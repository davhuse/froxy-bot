#!/usr/bin/env python3
"""Froxy AI Telegram Mini App backend.

All inference, identity, billing and payment reconciliation happens server-side.
The browser receives only public model metadata and user-owned results.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import os
import random
import socket
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qsl

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

import firestore_helper

try:
    from license_delivery import allocate_license
except ImportError:  # pragma: no cover
    from ..license_delivery import allocate_license

try:
    from .froxy_gateway import FroxyGateway, GatewayError
    from .froxy_store import FroxyStore, InsufficientBalance, QuotaExceeded, StoreUnavailable
    from .shopier_dynamic import cancel_and_delete_topup, create_dynamic_shopier_listing
except (ImportError, ValueError):  # pragma: no cover
    from froxy_gateway import FroxyGateway, GatewayError
    from froxy_store import FroxyStore, InsufficientBalance, QuotaExceeded, StoreUnavailable
    from shopier_dynamic import cancel_and_delete_topup, create_dynamic_shopier_listing


BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_DB_PATH = BASE_DIR / "products_db.json"
MAX_INIT_DATA_AGE = int(os.environ.get("FROXY_INIT_DATA_MAX_AGE", "86400"))
SUPPORT_HANDLE = "@FroxyDestekBOT"
MANUAL_DELIVERY_LABEL = "1–3 iş günü içinde manuel teslimat"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.config.update(MAX_CONTENT_LENGTH=256 * 1024)
store = FroxyStore()
gateway = FroxyGateway()
image_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="froxy-image")
_image_jobs_lock = threading.Lock()
_running_image_jobs: set[str] = set()
_rate_lock = threading.Lock()
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_topup_worker_started = False
_topup_worker_lock = threading.Lock()


def _telegram_bot_token() -> str:
    return (os.environ.get("FROXY_BOT_TOKEN") or os.environ.get("FROXY_SUPPORT_BOT_TOKEN") or "").strip()


def verify_telegram_init_data(raw_init_data: str) -> dict | None:
    if not raw_init_data or not _telegram_bot_token():
        return None
    try:
        pairs = dict(parse_qsl(raw_init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", "")
        auth_date = int(pairs.get("auth_date", "0"))
        age = time.time() - auth_date
        if not received_hash or not auth_date or age < -60 or age > MAX_INIT_DATA_AGE:
            return None
        data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
        secret_key = hmac.new(b"WebAppData", _telegram_bot_token().encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            return None
        user = json.loads(pairs.get("user", "{}"))
        return user if user.get("id") else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def authenticated_user() -> dict | None:
    raw = request.headers.get("X-Telegram-Init-Data", "")
    user = verify_telegram_init_data(raw)
    if user:
        return user
    runtime_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production")).strip().lower()
    if os.environ.get("FROXY_ALLOW_DEV_AUTH", "0") == "1" and runtime_env in {"development", "test", "local"}:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id") or request.args.get("user_id") or request.headers.get("X-Dev-User-Id")
        if user_id:
            return {
                "id": int(user_id),
                "first_name": str(data.get("first_name") or "Froxy Test"),
                "last_name": str(data.get("last_name") or ""),
                "username": str(data.get("username") or ""),
            }
    return None


def auth_error():
    return jsonify({"success": False, "error": "Telegram doğrulaması gerekli"}), 401


def _require_user() -> tuple[dict | None, tuple | None]:
    user = authenticated_user()
    if not user:
        return None, auth_error()
    try:
        store.get_or_create_user(user)
    except StoreUnavailable:
        return None, (jsonify({"success": False, "error": "Kalıcı veri hizmetine ulaşılamıyor"}), 503)
    return user, None


def _rate_limit(scope: str, identity: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    key = f"{scope}:{identity}"
    with _rate_lock:
        bucket = _rate_buckets[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def _json_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _credit_try_value() -> float:
    try:
        return max(0.000001, float(os.environ.get("FROXY_CREDIT_TRY_VALUE", "0.001")))
    except ValueError:
        return 0.001


def _credit_amount_for_product(product: dict) -> int:
    return max(1, int(round(float(product.get("price_num", 0)) / _credit_try_value())))


def load_products() -> list[dict]:
    if not PRODUCTS_DB_PATH.exists():
        return []
    with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as handle:
        rows = json.load(handle)
    result = []
    for raw in rows:
        product = dict(raw)
        if product.get("category") == "credits":
            credits = _credit_amount_for_product(product)
            product.update({
                "ai_credits": credits,
                "badge": f"🪙 {credits:,} AI Kredi".replace(",", "."),
                "model_tag": "Gerçek kullanıma göre",
                "delivery_type": "ai_credit",
                "delivery_label": "⚡ Ödeme sonrası anında AI kredisi",
                "description": f"{credits:,} AI kredisi. Kullanım maliyeti seçilen model ve gerçek token tüketimine göre hesaplanır.".replace(",", "."),
            })
        else:
            if "sınırsız" in str(product.get("badge", "")).lower():
                product["badge"] = "💎 1 Aylık Erişim"
            product.update({
                "delivery_type": "stock_or_manual",
                "delivery_label": "Stoktan otomatik veya 1–3 iş günü manuel",
                "manual_delivery_sla": "1–3 iş günü",
                "support_handle": SUPPORT_HANDLE,
            })
        result.append(product)
    return result


@app.after_request
def add_froxy_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://telegram.org; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; "
        "connect-src 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org; "
        "base-uri 'none'; form-action 'self' https://www.shopier.com"
    )
    response.headers.pop("X-Frame-Options", None)
    return response


@app.errorhandler(StoreUnavailable)
def handle_store_unavailable(_error):
    return jsonify({"success": False, "error": "Kalıcı veri hizmetine ulaşılamıyor"}), 503


@app.route("/")
def serve_index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/api/health", methods=["GET"])
def froxy_health():
    firestore = (
        firestore_helper.health_check()
        if store.backend == "firestore"
        else {"configured": False, "reachable": True, "status": "local_memory"}
    )
    status = "ok" if firestore.get("reachable") else "degraded"
    return jsonify(
        {
            "status": status,
            "store": store.backend,
            "firestore": firestore,
            "configured_providers": sum(1 for provider in gateway.providers() if provider.key),
        }
    ), (200 if status == "ok" else 503)


@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category", "all")
    query = request.args.get("q", "").lower().strip()
    products = load_products()
    if category and category != "all":
        products = [p for p in products if p.get("category") == category]
    if query:
        products = [p for p in products if query in p.get("title", "").lower() or query in p.get("description", "").lower()]
    return jsonify({"success": True, "count": len(products), "products": products})


@app.route("/api/me", methods=["GET", "POST"])
def get_me():
    telegram_user, error = _require_user()
    if error:
        return error
    _sync_shopier_topups(user_id=int(telegram_user["id"]), quiet=True)
    user = store.get_or_create_user(telegram_user)
    return jsonify({"success": True, "user": user})


@app.route("/api/user/<int:user_id>", methods=["GET", "POST"])
def legacy_user_profile(user_id: int):
    telegram_user, error = _require_user()
    if error:
        return error
    if int(telegram_user["id"]) != int(user_id):
        return auth_error()
    user = store.get_or_create_user(telegram_user)
    user["balance"] = user["wallet_balance"]
    return jsonify({"success": True, "user": user})


@app.route("/api/models", methods=["GET"])
def get_models():
    # Model metadata has no user data or credentials. Let the picker load
    # while Telegram finishes injecting initData; AI requests stay HMAC-only.
    visitor = request.headers.get("X-Forwarded-For", request.remote_addr or "anonymous").split(",")[0].strip()
    if not _rate_limit("models", visitor, 30):
        return jsonify({"success": False, "error": "Çok fazla model yenileme isteği"}), 429
    try:
        catalog = gateway.public_catalog()
    except Exception:
        return jsonify({"success": False, "error": "Model kataloğu şu anda yenilenemiyor"}), 503
    return jsonify({"success": True, **catalog})


@app.route("/api/provider-status", methods=["GET"])
def provider_status():
    telegram_user, error = _require_user()
    if error:
        return error
    return jsonify({"success": True, "providers": gateway.provider_status()})


@app.route("/api/chat", methods=["POST"])
def chat():
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    if not _rate_limit("chat", str(user_id), 10):
        return jsonify({"success": False, "error": "Dakikalık sohbet sınırına ulaştınız"}), 429
    data = request.get_json(silent=True) or {}
    model_id = str(data.get("model") or "froxy-fast")[:220]
    request_id = str(data.get("request_id") or uuid.uuid4().hex)[:120]
    chat_id = str(data.get("chat_id") or uuid.uuid4().hex)[:80]
    raw_messages = data.get("messages") or []
    if not isinstance(raw_messages, list) or not raw_messages:
        return jsonify({"success": False, "error": "En az bir mesaj gerekli"}), 400
    messages = []
    for row in raw_messages[-30:]:
        if not isinstance(row, dict) or row.get("role") not in {"system", "user", "assistant"}:
            continue
        content = str(row.get("content") or "")[:12000]
        if content:
            messages.append({"role": row["role"], "content": content})
    if not messages or messages[-1]["role"] != "user":
        return jsonify({"success": False, "error": "Son mesaj kullanıcı mesajı olmalı"}), 400
    try:
        max_tokens = max(64, min(int(data.get("max_tokens", 800)), 1200))
        temperature = max(0.0, min(float(data.get("temperature", 0.7)), 1.5))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Üretim ayarları geçersiz"}), 400
    try:
        model = gateway.get_model(model_id)
        is_free = bool(model.get("is_froxy"))
        if is_free:
            store.consume_free_quota(user_id, "text", request_id)
            reservation = 0
        else:
            reservation = gateway.reservation_for_chat(model, messages, max_tokens)
            store.reserve_credits(user_id, request_id, reservation, f"chat:{model_id}")
    except (GatewayError, QuotaExceeded, InsufficientBalance) as exc:
        status = 402 if isinstance(exc, InsufficientBalance) else 429 if isinstance(exc, QuotaExceeded) else 400
        return jsonify({"success": False, "error": str(exc)}), status

    def generate():
        output_parts: list[str] = []
        usage: dict = {}
        provider_meta: dict = {}
        try:
            yield _json_sse("meta", {"request_id": request_id, "chat_id": chat_id, "model": model_id, "reserved_credits": reservation})
            for event in gateway.stream_chat(model, messages, max_tokens=max_tokens, temperature=temperature):
                if event["type"] == "delta":
                    output_parts.append(event["content"])
                    yield _json_sse("delta", {"content": event["content"]})
                elif event["type"] == "provider_done":
                    usage = event.get("usage") or {}
                    provider_meta = {"provider": event.get("provider"), "provider_model": event.get("provider_model")}
            output = "".join(output_parts).strip()
            if not output:
                raise GatewayError("Model boş yanıt verdi")
            if is_free:
                billing = {"charged": 0}
            else:
                input_text = "\n".join(row["content"] for row in messages)
                actual = gateway.actual_chat_credits(model, usage, input_text, output)
                billing = store.settle_credits(user_id, request_id, actual, provider_meta)
            store.append_chat(user_id, chat_id, model_id, messages[-1]["content"], output)
            yield _json_sse("done", {"usage": usage, "billing": billing, **provider_meta})
        except Exception as exc:
            if is_free:
                store.restore_free_quota(user_id, "text", request_id)
            else:
                store.refund_credits(user_id, request_id, "chat_failed")
            message = str(exc) if isinstance(exc, GatewayError) else "Sohbet isteği tamamlanamadı"
            yield _json_sse("error", {"error": message})

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-transform"})


def _image_dimensions(ratio: str, free: bool) -> tuple[int, int]:
    if free:
        return 512, 512
    return {"1:1": (768, 768), "16:9": (768, 432), "9:16": (432, 768), "4:3": (768, 576), "4:5": (614, 768)}.get(ratio, (768, 768))


def _submit_image_job(job: dict) -> None:
    job_id = str(job["job_id"])
    with _image_jobs_lock:
        if job_id in _running_image_jobs:
            return
        _running_image_jobs.add(job_id)

    def run():
        try:
            store.update_image_job(job_id, {"status": "running", "started_at": int(time.time())})
            result = gateway.generate_image(job["prompt"], int(job["width"]), int(job["height"]))
            if job.get("billing_kind") == "credits":
                store.settle_credits(int(job["user_id"]), job["request_id"], int(job["reserved_credits"]), {"provider": result.get("provider"), "provider_model": result.get("model")})
            store.update_image_job(job_id, {"status": "completed", "image_url": result["image_url"], "provider": result.get("provider"), "provider_model": result.get("model"), "completed_at": int(time.time())})
        except Exception as exc:
            if job.get("billing_kind") == "credits":
                store.refund_credits(int(job["user_id"]), job["request_id"], "image_failed")
            else:
                store.restore_free_quota(int(job["user_id"]), "image", job["request_id"])
            store.update_image_job(job_id, {"status": "failed", "error": str(exc) if isinstance(exc, GatewayError) else "Görsel üretimi tamamlanamadı", "failed_at": int(time.time())})
        finally:
            with _image_jobs_lock:
                _running_image_jobs.discard(job_id)

    image_executor.submit(run)


@app.route("/api/images", methods=["POST"])
def create_image():
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    if not _rate_limit("image", str(user_id), 4, 120):
        return jsonify({"success": False, "error": "Görsel istek sınırına ulaştınız"}), 429
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt") or "").strip()[:3000]
    if len(prompt) < 3:
        return jsonify({"success": False, "error": "Görsel açıklaması çok kısa"}), 400
    request_id = str(data.get("request_id") or uuid.uuid4().hex)[:120]
    job_id = str(data.get("job_id") or uuid.uuid4().hex)[:80]
    use_free = data.get("use_free", True) is not False
    billing_kind = "free"
    reserved = 0
    try:
        if use_free:
            store.consume_free_quota(user_id, "image", request_id)
        else:
            raise QuotaExceeded("Ücretli üretim seçildi")
    except QuotaExceeded:
        billing_kind = "credits"
        reserved = gateway.image_credit_cost()
        try:
            store.reserve_credits(user_id, request_id, reserved, "image")
        except InsufficientBalance as exc:
            return jsonify({"success": False, "error": str(exc)}), 402
    width, height = _image_dimensions(str(data.get("ratio") or "1:1"), billing_kind == "free")
    job = store.create_image_job(user_id, {"job_id": job_id, "request_id": request_id, "prompt": prompt, "style": str(data.get("style") or "auto")[:40], "ratio": str(data.get("ratio") or "1:1")[:10], "width": width, "height": height, "billing_kind": billing_kind, "reserved_credits": reserved})
    _submit_image_job(job)
    return jsonify({"success": True, "job": job}), 202


@app.route("/api/generation-jobs/<job_id>", methods=["GET"])
def get_image_job(job_id: str):
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    job = store.get_image_job(user_id, job_id)
    if not job:
        return jsonify({"success": False, "error": "Üretim işi bulunamadı"}), 404
    if job.get("status") in {"queued", "running"} and int(job.get("updated_at", 0)) < int(time.time()) - 25:
        _submit_image_job(job)
    return jsonify({"success": True, "job": job})


def _shopier_token() -> str:
    return (os.environ.get("SHOPIER_FROXY_ACCESS_TOKEN") or os.environ.get("SHOPIER_BEARER_TOKEN") or "").strip()


def _create_topup(telegram_user: dict, *, amount: float, kind: str, product: dict | None, idempotency_key: str) -> dict:
    user_id = int(telegram_user["id"])
    if kind == "credits" and not product:
        raise ValueError("Kredi paketi bulunamadı")
    existing = store.get_pending_topup_by_idempotency(user_id, idempotency_key)
    if existing:
        return {
            "success": True,
            "duplicate": True,
            "product_id": existing["product_id"],
            "payment_url": existing.get("payment_url"),
            "is_live_shopier": True,
        }
    result = create_dynamic_shopier_listing(amount=amount, user_id=user_id, user_name=str(telegram_user.get("first_name") or "Froxy Müşteri"), username=str(telegram_user.get("username") or ""), idempotency_key=idempotency_key, purpose="credits" if kind == "credits" else "wallet", purpose_title=(product or {}).get("title", ""), persist_local=False)
    if result.get("success"):
        store.save_topup({"product_id": str(result["product_id"]), "user_id": user_id, "amount_kurus": int(round(amount * 100)), "kind": kind, "ai_credits": _credit_amount_for_product(product) if product else 0, "credit_product_id": str((product or {}).get("id") or ""), "payment_url": result.get("payment_url"), "status": "pending", "idempotency_key": idempotency_key, "created_at": int(time.time())})
    return result


@app.route("/api/balance/create-dynamic-topup", methods=["POST"])
def create_dynamic_topup():
    telegram_user, error = _require_user()
    if error:
        return error
    if not _shopier_token():
        return jsonify({"success": False, "error": "Shopier ödeme altyapısı henüz yapılandırılmadı"}), 503
    data = request.get_json(silent=True) or {}
    try:
        amount = round(float(data.get("amount", 50)), 2)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Geçersiz tutar"}), 400
    if amount < 10 or amount > 50000:
        return jsonify({"success": False, "error": "Yükleme tutarı 10–50.000 TL arasında olmalı"}), 400
    idem = str(data.get("idempotency_key") or uuid.uuid4().hex)[:120]
    result = _create_topup(telegram_user, amount=amount, kind="wallet", product=None, idempotency_key=idem)
    return jsonify(result), 200 if result.get("success") else 502


@app.route("/api/credits/create-checkout", methods=["POST"])
def create_credit_checkout():
    telegram_user, error = _require_user()
    if error:
        return error
    if not _shopier_token():
        return jsonify({"success": False, "error": "Shopier ödeme altyapısı henüz yapılandırılmadı"}), 503
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("product_id") or "")
    product = next((row for row in load_products() if str(row.get("id")) == product_id and row.get("category") == "credits"), None)
    if not product:
        return jsonify({"success": False, "error": "Kredi paketi bulunamadı"}), 404
    idem = str(data.get("idempotency_key") or uuid.uuid4().hex)[:120]
    result = _create_topup(telegram_user, amount=float(product["price_num"]), kind="credits", product=product, idempotency_key=idem)
    if result.get("success"):
        result["ai_credits"] = int(product["ai_credits"])
    return jsonify(result), 200 if result.get("success") else 502


def _paid_shopier_orders() -> list[dict]:
    token = _shopier_token()
    if not token:
        return []
    try:
        response = requests.get("https://api.shopier.com/v1/orders?limit=50", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=12)
        if response.status_code != 200:
            return []
        payload = response.json()
        rows = payload if isinstance(payload, list) else payload.get("orders", payload.get("data", []))
        return rows if isinstance(rows, list) else []
    except (requests.RequestException, ValueError):
        return []


def _sync_shopier_topups(user_id: int | None = None, quiet: bool = False) -> list[dict]:
    try:
        topups = store.list_active_topups()
    except StoreUnavailable:
        return []
    if user_id is not None:
        topups = [row for row in topups if int(row.get("user_id", 0)) == int(user_id)]
    if not topups:
        return []
    by_product = {str(row["product_id"]): row for row in topups}
    credited = []
    for order in _paid_shopier_orders():
        status = str(order.get("paymentStatus") or order.get("status") or order.get("orderStatus") or "").lower()
        if status not in {"paid", "shipped", "delivered", "completed", "success"}:
            continue
        order_id = str(order.get("id") or order.get("orderId") or "")
        for item in order.get("lineItems") or order.get("line_items") or order.get("items") or []:
            pid = str(item.get("productId") or item.get("product_id") or item.get("id") or "")
            topup = by_product.get(pid)
            if not topup:
                continue
            paid_value = item.get("total") or item.get("price")
            if paid_value is not None:
                try:
                    paid_kurus = int(round(float(str(paid_value).replace(",", ".")) * 100))
                except (TypeError, ValueError):
                    continue
                if paid_kurus < int(topup.get("amount_kurus", 0)):
                    continue
            uid = int(topup["user_id"])
            result = store.credit_balance(uid, wallet_kurus=int(topup["amount_kurus"]) if topup.get("kind") == "wallet" else 0, ai_credits=int(topup.get("ai_credits", 0)) if topup.get("kind") == "credits" else 0, idempotency_key=f"shopier:{order_id}:{pid}", title="Froxy AI kredi paketi" if topup.get("kind") == "credits" else "Froxy mağaza cüzdanı yükleme")
            store.update_topup(pid, {"status": "completed", "shopier_order_id": order_id, "completed_at": int(time.time())})
            cancel_and_delete_topup(pid)
            credited.append({"user_id": uid, "product_id": pid, "order_id": order_id, **result})
    return credited


@app.route("/api/balance/sync-orders", methods=["GET"])
def sync_orders():
    telegram_user, error = _require_user()
    if error:
        return error
    credited = _sync_shopier_topups(user_id=int(telegram_user["id"]))
    return jsonify({"success": True, "credited_orders": credited, "count": len(credited)})


@app.route("/api/balance/cancel-topup", methods=["POST"])
def cancel_topup():
    telegram_user, error = _require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("product_id") or "")
    topup = store.get_topup(product_id)
    if not topup or int(topup.get("user_id", 0)) != int(telegram_user["id"]):
        return jsonify({"success": False, "error": "Bu ödeme ilanı size ait değil"}), 403
    if topup.get("status") == "pending":
        cancel_and_delete_topup(product_id)
        store.update_topup(product_id, {"status": "cancelled", "cancelled_at": int(time.time())})
    return jsonify({"success": True})


def _make_order(product: dict, qty: int = 1) -> dict:
    now = int(time.time())
    return {"order_id": f"FRX-{now}-{uuid.uuid4().hex[:8].upper()}", "product_id": str(product["id"]), "title": product["title"], "qty": qty, "price_kurus": int(round(float(product["price_num"]) * 100)), "subtotal_kurus": int(round(float(product["price_num"]) * 100)) * qty, "created_at": now}


def _finalize_delivery(order: dict) -> dict:
    alloc = allocate_license(order["title"], brand="froxy")
    delivered = bool(alloc.get("license_key")) and alloc.get("status") == "delivered"
    order.update({"status": "delivered" if delivered else "manual_pending", "license_key": alloc.get("license_key"), "delivery_note": alloc.get("delivery_note") if delivered else MANUAL_DELIVERY_LABEL, "support_handle": SUPPORT_HANDLE, "redeem_url": alloc.get("redeem_url"), "activation_guide": alloc.get("activation_guide"), "needs_email": alloc.get("needs_email", False), "manual_delivery_sla": None if delivered else "1–3 iş günü"})
    return order


@app.route("/api/user/purchase", methods=["POST"])
def purchase_product():
    telegram_user, error = _require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("product_id") or "")
    product = next((row for row in load_products() if str(row.get("id")) == product_id), None)
    if not product:
        return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
    if product.get("category") == "credits":
        return jsonify({"success": False, "error": "AI kredi paketleri ödeme ekranından alınır"}), 409
    idem = str(data.get("idempotency_key") or "")[:120]
    if not idem:
        return jsonify({"success": False, "error": "Güvenli sipariş anahtarı eksik"}), 400
    order = _make_order(product)
    try:
        reserved = store.reserve_wallet_purchase(int(telegram_user["id"]), idem, order["subtotal_kurus"], [order])
    except InsufficientBalance as exc:
        return jsonify({"success": False, "error": str(exc)}), 402
    if reserved.get("duplicate"):
        return jsonify({"success": True, **reserved})
    finalized = [_finalize_delivery(order)]
    store.finalize_orders(int(telegram_user["id"]), finalized)
    return jsonify({"success": True, "message": "Ürün teslim edildi." if finalized[0]["status"] == "delivered" else "Sipariş alındı; 1–3 iş günü içinde manuel teslim edilecek.", "new_balance": round(int(reserved["wallet_kurus"]) / 100, 2), "order": finalized[0]})


@app.route("/api/user/purchase-cart", methods=["POST"])
def purchase_cart():
    telegram_user, error = _require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    idem = str(data.get("idempotency_key") or "")[:120]
    if not isinstance(items, list) or not items or not idem:
        return jsonify({"success": False, "error": "Sepet veya güvenli sipariş anahtarı eksik"}), 400
    products = {str(row["id"]): row for row in load_products()}
    orders = []
    for item in items[:10]:
        product = products.get(str(item.get("id")))
        if not product or product.get("category") == "credits":
            return jsonify({"success": False, "error": "Sepette geçersiz veya kredi paketi ürün var"}), 400
        try:
            qty = max(1, min(int(item.get("qty", 1)), 3))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Ürün adedi geçersiz"}), 400
        for _ in range(qty):
            orders.append(_make_order(product))
    total = sum(int(row["subtotal_kurus"]) for row in orders)
    try:
        reserved = store.reserve_wallet_purchase(int(telegram_user["id"]), idem, total, orders)
    except InsufficientBalance as exc:
        return jsonify({"success": False, "error": str(exc)}), 402
    if reserved.get("duplicate"):
        return jsonify({"success": True, **reserved})
    finalized = [_finalize_delivery(order) for order in orders]
    store.finalize_orders(int(telegram_user["id"]), finalized)
    return jsonify({"success": True, "message": f"{len(finalized)} ürünlük sipariş alındı.", "new_balance": round(int(reserved["wallet_kurus"]) / 100, 2), "orders": finalized})


@app.route("/api/user/spin", methods=["POST"])
def spin_daily_wheel():
    telegram_user, error = _require_user()
    if error:
        return error
    day = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 3 * 3600))
    amount_kurus = random.choice([50, 100, 100, 150, 200, 300])
    result = store.credit_balance(int(telegram_user["id"]), wallet_kurus=amount_kurus, idempotency_key=f"spin:{day}", title="Günlük çark ödülü")
    return jsonify({"success": not result.get("duplicate"), "error": "Bugünkü çark hakkınızı kullandınız" if result.get("duplicate") else None, "segment": random.randint(0, 7), "reward_type": "balance", "reward_text": f"₺{amount_kurus / 100:.2f} mağaza bakiyesi", "reward_amount": amount_kurus / 100, "new_balance": round(int(result["wallet_kurus"]) / 100, 2)}), 429 if result.get("duplicate") else 200


@app.route("/api/referrals/<int:user_id>", methods=["GET"])
def referrals(user_id: int):
    telegram_user, error = _require_user()
    if error:
        return error
    if int(telegram_user["id"]) != user_id:
        return auth_error()
    return jsonify({"success": True, "user_id": user_id, "ref_link": f"https://t.me/FroxyDestekBOT?start=ref_{user_id}", "referrals_count": 0, "referral_earnings": 0, "commission_rate": 0.10})


def _start_topup_worker() -> None:
    global _topup_worker_started
    if not _shopier_token() or os.environ.get("APP_ENV", "").lower() == "test":
        return
    with _topup_worker_lock:
        if _topup_worker_started:
            return
        _topup_worker_started = True

    def worker():
        while True:
            try:
                _sync_shopier_topups(quiet=True)
            except Exception:
                pass
            time.sleep(30)

    threading.Thread(target=worker, daemon=True, name="froxy-shopier-sync").start()


@app.route("/<path:path>")
def serve_static(path: str):
    target = (BASE_DIR / path).resolve()
    try:
        target.relative_to(BASE_DIR.resolve())
    except ValueError:
        return jsonify({"success": False, "error": "Geçersiz dosya yolu"}), 400
    if target.exists() and target.is_file():
        return send_from_directory(str(BASE_DIR), path)
    return send_from_directory(str(BASE_DIR), "index.html")


_start_topup_worker()


def get_local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
        return address
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
