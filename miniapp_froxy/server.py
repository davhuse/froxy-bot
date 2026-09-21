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
    from .web_search import perform_web_search, web_context
except (ImportError, ValueError):  # pragma: no cover
    from froxy_gateway import FroxyGateway, GatewayError
    from froxy_store import FroxyStore, InsufficientBalance, QuotaExceeded, StoreUnavailable
    from shopier_dynamic import cancel_and_delete_topup, create_dynamic_shopier_listing
    from web_search import perform_web_search, web_context


BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
PRODUCTS_DB_PATH = BASE_DIR / "products_db.json"
MAX_INIT_DATA_AGE = int(os.environ.get("FROXY_INIT_DATA_MAX_AGE", "86400"))
SUPPORT_HANDLE = "@FroxyDestekBOT"
MANUAL_DELIVERY_LABEL = "1–3 iş günü içinde manuel teslimat"

app = Flask(__name__, static_folder=str(DIST_DIR if DIST_DIR.exists() else BASE_DIR), static_url_path="")
app.config.update(MAX_CONTENT_LENGTH=12 * 1024 * 1024)
store = FroxyStore()
gateway = FroxyGateway()
image_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="froxy-image")
_image_jobs_lock = threading.Lock()
_running_image_jobs: set[str] = set()
_image_recovery_started = False
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


def _store_category(product: dict) -> str:
    title = str(product.get("title") or "").lower()
    if str(product.get("id") or "").startswith("474081"):
        return "credits"
    if "chatgpt" in title or "codex" in title:
        return "chatgpt"
    if "gemini" in title or "antigravity" in title:
        return "gemini"
    if "perplexity" in title:
        return "perplexity"
    return "other"


def load_products() -> list[dict]:
    if not PRODUCTS_DB_PATH.exists():
        return []
    with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as handle:
        rows = json.load(handle)
    result = []
    for raw in rows:
        product = dict(raw)
        product["store_category"] = _store_category(product)
        if product["store_category"] == "credits":
            product["category"] = "credits"
            credits = _credit_amount_for_product(product)
            formatted_credits = f"{credits:,}".replace(",", ".")
            product.update({
                "ai_credits": credits,
                "badge": f"🪙 {formatted_credits} AI Kredi",
                "model_tag": "Gerçek kullanıma göre",
                "image": raw.get("image") or "assets/froxy_logo.png",
                "delivery_type": "ai_credit",
                "delivery_label": "⚡ Ödeme sonrası anında AI kredisi",
                "description": f"{product.get('title', 'Froxy AI kredi paketi')} — ödeme onayından sonra hesabınıza {formatted_credits} AI kredisi yüklenir. Kullanım, seçilen model ve gerçek token tüketimine göre hesaplanır.",
            })
        else:
            product["category"] = "ai"
            category_labels = {
                "chatgpt": ("OPENAI ÜRÜNÜ", "assets/provider_openai.svg"),
                "gemini": ("GOOGLE GEMINI", "assets/provider_google.svg"),
                "perplexity": ("PERPLEXITY", "assets/provider_perplexity.svg"),
                "other": ("FROXY ÜRÜNÜ", "assets/froxy_logo.png"),
            }
            badge, fallback_image = category_labels.get(product["store_category"], category_labels["other"])
            product.update({
                "badge": badge,
                "model_tag": "Shopier ürünü",
                "image": raw.get("image") or fallback_image,
                "delivery_type": "stock_or_manual",
                "delivery_label": "Stoktan otomatik veya 1–3 iş günü manuel",
                "manual_delivery_sla": "1–3 iş günü",
                "support_handle": SUPPORT_HANDLE,
                "description": f"{product.get('title', 'Froxy AI ürünü')} — Shopier 3D Secure ödeme. Stok varsa otomatik, stok yoksa @FroxyDestekBOT üzerinden 1–3 iş günü içinde teslim edilir.",
            })
        result.append(product)
    return result


@app.after_request
def add_froxy_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://telegram.org https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; "
        "connect-src 'self' https://cdn.jsdelivr.net; media-src 'self' data: blob: https:; worker-src 'self' blob:; "
        "frame-ancestors https://web.telegram.org https://*.telegram.org; "
        "base-uri 'none'; form-action 'self' https://www.shopier.com"
    )
    response.headers.pop("X-Frame-Options", None)
    return response


@app.errorhandler(StoreUnavailable)
def handle_store_unavailable(_error):
    return jsonify({"success": False, "error": "Kalıcı veri hizmetine ulaşılamıyor"}), 503


@app.route("/")
def serve_index():
    root = DIST_DIR if DIST_DIR.exists() else BASE_DIR
    return send_from_directory(str(root), "index.html")


@app.route("/assets/<path:path>")
def serve_froxy_asset(path: str):
    built = DIST_DIR / "assets" / path
    if built.exists():
        return send_from_directory(str(DIST_DIR / "assets"), path)
    return send_from_directory(str(BASE_DIR / "assets"), path)


@app.route("/api/health", methods=["GET"])
def froxy_health():
    firestore = (
        firestore_helper.health_check()
        if store.backend == "firestore"
        else {"configured": False, "reachable": True, "status": "local_memory"}
    )
    status = "ok" if firestore.get("reachable") else "degraded"
    catalog = gateway.public_catalog()
    providers = catalog.get("providers") or gateway.provider_status()
    image_catalog = gateway.image_models()
    fallback = store.fallback_state()
    return jsonify(
        {
            "status": status,
            "store": store.backend,
            "firestore": firestore,
            "gateway_revision": getattr(gateway, "REVISION", "test"),
            "configured_providers": sum(1 for row in providers.values() if row.get("configured")),
            "provider_count": len(providers),
            "active_providers": sum(1 for row in providers.values() if row.get("healthy")),
            "image_model_count": len(image_catalog),
            "active_image_models": sum(1 for row in image_catalog if row.get("active")),
            "active_model_count": int(catalog.get("active_model_count", 0) or 0),
            "catalog_model_count": int(catalog.get("catalog_model_count", 0) or 0),
            "unavailable_model_count": int(catalog.get("unavailable_model_count", 0) or 0),
            "catalog_cache_age": catalog.get("catalog_cache_age"),
            "local_fallback": fallback,
            "providers": providers,
        }
    ), (200 if status == "ok" else 503)


@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category", "all")
    query = request.args.get("q", "").lower().strip()
    products = load_products()
    if category and category != "all":
        products = [p for p in products if p.get("store_category") == category]
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
    force_refresh = str(request.args.get("refresh") or "").lower() in {"1", "true", "yes"}
    try:
        catalog = gateway.public_catalog(force=force_refresh)
    except Exception:
        return jsonify({"success": False, "error": "Model kataloğu şu anda yenilenemiyor"}), 503
    rows = list(catalog.get("models") or [])
    scope = str(request.args.get("scope") or "all").lower()
    modality = str(request.args.get("modality") or "").lower().strip()
    provider = str(request.args.get("provider") or "").lower().strip()
    availability = str(request.args.get("availability") or "").lower().strip()
    capability = str(request.args.get("capability") or "").lower().strip()
    query = " ".join(str(request.args.get("q") or "").lower().split())[:120]
    if provider:
        rows = [row for row in rows if str(row.get("provider") or "").lower() == provider]
    if modality:
        rows = [row for row in rows if str(row.get("kind") or "chat").lower() == modality]
    if availability:
        rows = [row for row in rows if str(row.get("availability") or "").lower() == availability]
    if capability:
        rows = [row for row in rows if capability in [str(value).lower() for value in row.get("capabilities") or []]]
    if query:
        rows = [row for row in rows if query in " ".join(str(row.get(key) or "") for key in ("name", "provider", "provider_label", "developer", "family", "description")).lower()]

    def matches_scope(row: dict, requested: str) -> bool:
        haystack = " ".join(str(row.get(key) or "") for key in ("id", "name", "family", "developer", "description")).lower()
        capabilities = {str(value).lower() for value in row.get("capabilities") or []}
        if requested in {"all", "recommended"}:
            return True
        if requested == "best":
            return any(token in haystack for token in ("gpt-5", "gpt-4.1", "claude opus", "claude sonnet", "gemini 2.5 pro", "gemini 3", "deepseek", "qwen3", "llama 4", "mistral large"))
        if requested == "coding":
            return "code" in capabilities or any(token in haystack for token in ("code", "coder", "codestral", "devstral", "gpt", "claude", "deepseek", "qwen"))
        if requested == "research":
            return "reasoning" in capabilities or any(token in haystack for token in ("reason", "search", "perplexity", "sonar", "deepseek", "gemini", "claude"))
        if requested == "vision":
            return "vision" in capabilities or bool(row.get("supports_vision"))
        if requested == "fast":
            return any(token in haystack for token in ("fast", "flash", "mini", "nano", "instant", "8b", "haiku", "lite"))
        if requested == "free":
            return bool(row.get("is_free") or row.get("is_froxy")) and row.get("availability") == "active"
        return True

    if scope not in {"all", "recommended"}:
        rows = [row for row in rows if matches_scope(row, scope)]

    def score(row: dict) -> tuple:
        model_id = str(row.get("id") or "").lower()
        preferred = any(token in model_id for token in ("froxy-", "gpt", "claude", "gemini", "llama", "qwen", "deepseek", "mistral"))
        return (
            0 if row.get("availability") == "active" else 1,
            0 if row.get("is_froxy") else 1,
            0 if preferred else 1,
            int(row.get("estimated_1k_credits") or 0),
            str(row.get("name") or "").lower(),
        )

    rows.sort(key=score)
    if scope != "all":
        unique_rows = []
        seen_names = set()
        for row in rows:
            display_name = " ".join(str(row.get("name") or row.get("id") or "").lower().split())
            if display_name in seen_names:
                continue
            seen_names.add(display_name)
            unique_rows.append(row)
        rows = unique_rows
    if scope == "recommended":
        active = [row for row in rows if row.get("availability") == "active"]
        rows = active[:18]
    try:
        offset = max(0, int(request.args.get("cursor") or 0))
        limit = max(1, min(int(request.args.get("limit") or (40 if scope == "recommended" else len(rows) or 1)), 100))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Geçersiz sayfalama"}), 400
    total_filtered = len(rows)
    page = rows[offset:offset + limit]
    next_cursor = str(offset + limit) if offset + limit < total_filtered else None
    facets = {
        "providers": sorted({str(row.get("provider") or "") for row in rows if row.get("provider")}),
        "capabilities": sorted({str(value) for row in rows for value in (row.get("capabilities") or [])}),
        "families": sorted({str(row.get("family") or "AI") for row in rows}),
    }
    summary = {key: value for key, value in catalog.items() if key != "models"}
    return jsonify({"success": True, **summary, "models": page, "count": len(page), "total_filtered": total_filtered, "next_cursor": next_cursor, "facets": facets})


@app.route("/api/models/<path:model_id>", methods=["GET"])
def get_model_detail(model_id: str):
    catalog = gateway.public_catalog()
    model = next((row for row in catalog.get("models") or [] if str(row.get("id")) == str(model_id)), None)
    if not model:
        return jsonify({"success": False, "error": "Model bulunamadı"}), 404
    return jsonify({"success": True, "model": model, "input_schema": {
        "text": True,
        "attachments": "vision" in (model.get("capabilities") or []),
        "reasoning_levels": model.get("reasoning_levels") or ["adaptive"],
    }, "health": {
        "availability": model.get("availability"),
        "status_reason": model.get("status_reason"),
        "last_checked_at": model.get("last_checked_at"),
    }, "pricing": {
        "state": model.get("pricing_state"),
        "estimated_1k_credits": model.get("estimated_1k_credits"),
    }})


@app.route("/api/chats", methods=["GET"])
def chat_history():
    telegram_user, error = _require_user()
    if error:
        return error
    return jsonify({"success": True, "chats": store.list_chats(int(telegram_user["id"]))})


@app.route("/api/chats/<chat_id>", methods=["GET", "DELETE"])
def chat_history_item(chat_id: str):
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    if request.method == "DELETE":
        return jsonify({"success": True, "deleted": store.delete_chat(user_id, chat_id[:80])})
    row = store.get_chat(user_id, chat_id[:80])
    if not row:
        return jsonify({"success": False, "error": "Sohbet bulunamadı"}), 404
    return jsonify({"success": True, "chat": row})


@app.route("/api/research/watchlists", methods=["GET", "POST"])
def research_watchlists():
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    if request.method == "GET":
        return jsonify({"success": True, "watchlists": store.list_watchlists(user_id)})
    data = request.get_json(silent=True) or {}
    try:
        row = store.save_watchlist(user_id, str(data.get("topic") or ""), str(data.get("query") or ""))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "watchlist": row}), 201


@app.route("/api/research/watchlists/<watch_id>", methods=["DELETE"])
def delete_research_watchlist(watch_id: str):
    telegram_user, error = _require_user()
    if error:
        return error
    deleted = store.delete_watchlist(int(telegram_user["id"]), watch_id[:40])
    return jsonify({"success": True, "deleted": deleted})


@app.route("/api/research/watchlists/<watch_id>/refresh", methods=["POST"])
def refresh_research_watchlist(watch_id: str):
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    row = next((item for item in store.list_watchlists(user_id) if item.get("watch_id") == watch_id), None)
    if not row:
        return jsonify({"success": False, "error": "Takip konusu bulunamadı"}), 404
    result = perform_web_search(str(row.get("query") or row.get("topic") or ""), max_results=8)
    updated = store.update_watchlist(user_id, watch_id, {
        "status": "ready" if result.get("results") else "unavailable",
        "results": result.get("results") or [],
        "provider": result.get("provider"),
        "refreshed_at": int(time.time()),
    })
    return jsonify({"success": True, "watchlist": updated})


@app.route("/api/provider-status", methods=["GET"])
def provider_status():
    telegram_user, error = _require_user()
    if error:
        return error
    return jsonify({"success": True, "providers": gateway.provider_status()})


@app.route("/api/image-models", methods=["GET"])
def image_models():
    visitor = request.headers.get("X-Forwarded-For", request.remote_addr or "anonymous").split(",")[0].strip()
    if not _rate_limit("image-models", visitor, 30):
        return jsonify({"success": False, "error": "Çok fazla görsel model isteği"}), 429
    force_refresh = str(request.args.get("refresh") or "").lower() in {"1", "true", "yes"}
    if force_refresh:
        gateway.refresh_catalog(force=True)
    models = gateway.image_models()
    active = [row for row in models if row.get("active")]
    return jsonify({
        "success": True,
        "count": len(active),
        "active_count": len(active),
        "total_count": len(models),
        "catalog_only_count": sum(1 for row in models if row.get("availability") == "catalog_only"),
        "unavailable_count": sum(1 for row in models if row.get("availability") == "unavailable"),
        "models": models,
    })


@app.route("/api/media/models", methods=["GET"])
def media_models():
    modality = str(request.args.get("modality") or "image").lower()
    if modality not in {"image", "edit", "variation", "upscale", "background", "video", "audio", "music", "3d", "embedding", "realtime"}:
        return jsonify({"success": False, "error": "Geçersiz medya türü"}), 400
    force_refresh = str(request.args.get("refresh") or "").lower() in {"1", "true", "yes"}
    rows = gateway.media_models(modality, force=force_refresh)
    normalized = []
    for row in rows:
        item = dict(row)
        item.update({
            "modality": str(item.get("kind") or modality),
            "operations": ["generate", "edit", "variation", "upscale", "background"] if modality in {"image", "edit", "variation", "upscale", "background"} else ["generate"],
            "input_schema": {
                "prompt": True,
                "reference_image": modality in {"image", "edit", "variation", "upscale", "background", "video"},
                "ratios": ["1:1", "4:5", "9:16", "16:9"] if modality in {"image", "edit", "variation", "upscale", "background", "video"} else [],
            },
        })
        normalized.append(item)
    return jsonify({"success": True, "modality": modality, "models": normalized, "count": len(normalized), "active_count": sum(1 for row in normalized if row.get("active"))})


@app.route("/api/media/jobs", methods=["GET", "POST"])
def media_jobs():
    telegram_user, error = _require_user()
    if error:
        return error
    if request.method == "GET":
        return jsonify({"success": True, "jobs": store.list_image_jobs(int(telegram_user["id"]))})
    operation = str((request.get_json(silent=True) or {}).get("operation") or "generate")
    if operation != "generate":
        return jsonify({"success": False, "error": "Bu işlem için etkin sağlayıcı şeması henüz bulunmuyor", "operation": operation}), 409
    return create_image()


def _audio_key() -> str:
    for name in ("OPENAI_AUDIO_KEY", "OPENAI_API_KEY", "POLLINATIONS_API_KEY", "POLLINATIONS_API_KEYS"):
        raw = os.environ.get(name, "").replace(",", "\n")
        value = next((part.strip() for part in raw.splitlines() if part.strip()), "")
        if value:
            return value
    return ""


@app.route("/api/audio/transcriptions", methods=["POST"])
def audio_transcription():
    telegram_user, error = _require_user()
    if error:
        return error
    audio = request.files.get("file")
    if not audio:
        return jsonify({"success": False, "error": "Ses kaydı gerekli"}), 400
    key = _audio_key()
    if not key:
        return jsonify({"success": False, "error": "Ses sağlayıcısı yapılandırılmadı", "fallback": "browser"}), 503
    base = os.environ.get("FROXY_AUDIO_BASE_URL", "https://gen.pollinations.ai/v1").rstrip("/")
    try:
        response = requests.post(
            f"{base}/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (audio.filename or "voice.webm", audio.stream, audio.mimetype or "audio/webm")},
            data={"model": os.environ.get("FROXY_TRANSCRIBE_MODEL", "gpt-transcribe"), "language": request.form.get("language", "tr")},
            timeout=(8, 90),
        )
        payload = response.json() if "json" in response.headers.get("Content-Type", "") else {}
        if response.status_code >= 400:
            return jsonify({"success": False, "error": "Ses çözümlenemedi"}), 502
        text = str(payload.get("text") or ((payload.get("data") or {}).get("text") if isinstance(payload.get("data"), dict) else ""))
        return jsonify({"success": True, "text": text})
    except (requests.RequestException, ValueError):
        return jsonify({"success": False, "error": "Ses sağlayıcısına ulaşılamadı", "fallback": "browser"}), 503


@app.route("/api/audio/speech", methods=["POST"])
def audio_speech():
    telegram_user, error = _require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()[:4000]
    if not text:
        return jsonify({"success": False, "error": "Seslendirilecek metin gerekli"}), 400
    key = _audio_key()
    if not key:
        return jsonify({"success": False, "error": "Sunucu ses modeli yok", "fallback": "browser"}), 503
    base = os.environ.get("FROXY_AUDIO_BASE_URL", "https://gen.pollinations.ai/v1").rstrip("/")
    try:
        response = requests.post(
            f"{base}/audio/speech",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": os.environ.get("FROXY_TTS_MODEL", "openai-audio"), "voice": str(data.get("voice") or "alloy")[:30], "input": text},
            timeout=(8, 90),
        )
        if response.status_code >= 400:
            return jsonify({"success": False, "error": "Ses üretilemedi", "fallback": "browser"}), 502
        return Response(response.content, content_type=response.headers.get("Content-Type", "audio/mpeg"))
    except requests.RequestException:
        return jsonify({"success": False, "error": "Ses sağlayıcısına ulaşılamadı", "fallback": "browser"}), 503


@app.route("/api/realtime/session", methods=["POST"])
def realtime_session():
    telegram_user, error = _require_user()
    if error:
        return error
    # No long-lived credential is ever returned to the browser.  A provider
    # that supports ephemeral sessions can be connected through this URL.
    broker = os.environ.get("FROXY_REALTIME_SESSION_URL", "").strip()
    if not broker:
        return jsonify({"success": True, "supported": False, "mode": "push_to_talk", "reason": "Canlı sağlayıcı yok; bas-konuş hazır"})
    try:
        response = requests.post(broker, headers={"Authorization": f"Bearer {_audio_key()}"}, json={"language": "tr"}, timeout=(5, 20))
        payload = response.json()
        return jsonify({"success": response.ok, "supported": response.ok, "mode": "realtime", "session": payload if response.ok else None}), (200 if response.ok else 502)
    except (requests.RequestException, ValueError):
        return jsonify({"success": True, "supported": False, "mode": "push_to_talk", "reason": "Canlı bağlantı kurulamadı"})


@app.route("/api/chat", methods=["POST"])
def chat():
    telegram_user, error = _require_user()
    if error:
        return error
    user_id = int(telegram_user["id"])
    if not _rate_limit("chat", str(user_id), 10):
        return jsonify({"success": False, "error": "Dakikalık sohbet sınırına ulaştınız"}), 429
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode") or "general").lower()
    if mode not in {"general", "research", "code", "plan"}:
        mode = "general"
    reasoning_level = str(data.get("reasoning_level") or "adaptive").lower()
    if reasoning_level not in {"adaptive", "fast", "balanced", "high", "max"}:
        reasoning_level = "adaptive"
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
        max_tokens = max(64, min(int(data.get("max_tokens", 1400)), 4000))
        temperature = max(0.0, min(float(data.get("temperature", 0.7)), 1.5))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Üretim ayarları geçersiz"}), 400
    search = {"query": "", "provider": "none", "results": []}
    gateway_messages = list(messages)
    mode_prompts = {
        "research": "Kaynak odaklı araştırma asistanısın. Güncellik, tarih ve kaynak güvenilirliğini açıkça belirt.",
        "code": "Kıdemli yazılım mühendisisin. Çalışan, güvenli ve test edilebilir çözümler üret; belirsizlikleri belirt.",
        "plan": "Uygulanabilir planlar hazırlayan ürün ve mühendislik danışmanısın. Kararları, bağımlılıkları ve kabul ölçütlerini netleştir.",
        "general": "Yararlı, doğru ve açık bir Türkçe yapay zeka asistanısın.",
    }
    gateway_messages = [{"role": "system", "content": mode_prompts[mode]}, *gateway_messages]
    if data.get("web_search") is True or mode == "research":
        search = perform_web_search(messages[-1]["content"], max_results=5)
        if not search.get("results"):
            return jsonify({"success": False, "error": "Web araması şu anda güvenilir kaynak döndüremedi"}), 503
        gateway_messages = [{"role": "system", "content": mode_prompts[mode]}, web_context(search), *messages]
    try:
        model = gateway.get_model(model_id)
        is_free = bool(model.get("is_froxy"))
        if is_free:
            store.consume_free_quota(user_id, "text", request_id)
            reservation = 0
        else:
            reservation = gateway.reservation_for_chat(model, gateway_messages, max_tokens)
            store.reserve_credits(user_id, request_id, reservation, f"chat:{model_id}")
    except (GatewayError, QuotaExceeded, InsufficientBalance) as exc:
        status = 402 if isinstance(exc, InsufficientBalance) else 429 if isinstance(exc, QuotaExceeded) else 400
        return jsonify({"success": False, "error": str(exc)}), status

    def generate():
        output_parts: list[str] = []
        usage: dict = {}
        provider_meta: dict = {}
        try:
            yield _json_sse("meta", {"request_id": request_id, "chat_id": chat_id, "model": model_id, "reserved_credits": reservation, "web_search": bool(search["results"]), "mode": mode, "reasoning_level": reasoning_level})
            yield _json_sse("reasoning_status", {"state": "thinking", "level": reasoning_level})
            if search["results"]:
                yield _json_sse("tool_start", {"tool": "web_search", "query": search.get("query")})
                yield _json_sse("tool_result", {"tool": "web_search", "count": len(search["results"]), "provider": search.get("provider")})
            for event in gateway.stream_chat(model, gateway_messages, max_tokens=max_tokens, temperature=temperature, reasoning_level=reasoning_level, mode=mode):
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
                input_text = "\n".join(row["content"] for row in gateway_messages)
                actual = gateway.actual_chat_credits(model, usage, input_text, output)
                billing = store.settle_credits(user_id, request_id, actual, provider_meta)
            stored_output = output
            if search["results"]:
                source_lines = "\n".join(
                    f"[{index}] {row['title']} — {row['url']}"
                    for index, row in enumerate(search["results"], 1)
                )
                stored_output = f"{output}\n\nKaynaklar:\n{source_lines}"
            store.append_chat(user_id, chat_id, model_id, messages[-1]["content"], stored_output)
            yield _json_sse("reasoning_status", {"state": "complete", "level": reasoning_level})
            yield _json_sse("done", {"usage": usage, "billing": billing, "stored_content": stored_output, "web_sources": search["results"], "search_provider": search["provider"], **provider_meta})
        except Exception as exc:
            if is_free:
                store.restore_free_quota(user_id, "text", request_id)
            else:
                store.refund_credits(user_id, request_id, "chat_failed")
            message = str(exc) if isinstance(exc, GatewayError) else "Sohbet isteği tamamlanamadı"
            yield _json_sse("error", {"error": message})

    return Response(stream_with_context(generate()), content_type="text/event-stream; charset=utf-8", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-transform"})


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
            result = gateway.generate_image(job["prompt"], int(job["width"]), int(job["height"]), str(job.get("model") or ""))
            if job.get("billing_kind") == "credits":
                actual = min(int(job["reserved_credits"]), max(1, int(result.get("estimated_credits") or job["reserved_credits"])))
                store.settle_credits(int(job["user_id"]), job["request_id"], actual, {"provider": result.get("provider"), "provider_model": result.get("model")})
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


def _start_image_recovery() -> None:
    global _image_recovery_started
    if os.environ.get("APP_ENV", "").lower() == "test" or _image_recovery_started:
        return
    _image_recovery_started = True

    def recover():
        try:
            for pending_job in store.list_recoverable_image_jobs():
                _submit_image_job(pending_job)
        except Exception:
            # Health endpoints stay available even when Firestore is briefly
            # unavailable during boot; client polling can also resume a job.
            return

    threading.Thread(target=recover, daemon=True, name="froxy-image-recovery").start()


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
    model_id = str(data.get("model") or "")[:80]
    try:
        image_model = gateway.get_image_model(model_id)
    except GatewayError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
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
        reserved = max(1, int(image_model.get("estimated_credits") or gateway.image_credit_cost()))
        try:
            store.reserve_credits(user_id, request_id, reserved, "image")
        except InsufficientBalance as exc:
            return jsonify({"success": False, "error": str(exc)}), 402
    width, height = _image_dimensions(str(data.get("ratio") or "1:1"), billing_kind == "free")
    job = store.create_image_job(user_id, {"job_id": job_id, "request_id": request_id, "model": image_model["id"], "prompt": prompt, "style": str(data.get("style") or "auto")[:40], "ratio": str(data.get("ratio") or "1:1")[:10], "width": width, "height": height, "billing_kind": billing_kind, "reserved_credits": reserved})
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
    return os.environ.get("SHOPIER_FROXY_ACCESS_TOKEN", "").strip()


def _create_topup(telegram_user: dict, *, amount: float, kind: str, product: dict | None, idempotency_key: str, metadata: dict | None = None) -> dict:
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
        store.save_topup({"product_id": str(result["product_id"]), "user_id": user_id, "amount_kurus": int(round(amount * 100)), "kind": kind, "ai_credits": _credit_amount_for_product(product) if product else 0, "credit_product_id": str((product or {}).get("id") or ""), "payment_url": result.get("payment_url"), "status": "pending", "idempotency_key": idempotency_key, "metadata": metadata or {}, "created_at": int(time.time())})
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
    product = next((row for row in load_products() if str(row.get("id")) == product_id and row.get("store_category") == "credits"), None)
    if not product:
        return jsonify({"success": False, "error": "Kredi paketi bulunamadı"}), 404
    idem = str(data.get("idempotency_key") or uuid.uuid4().hex)[:120]
    result = _create_topup(telegram_user, amount=float(product["price_num"]), kind="credits", product=product, idempotency_key=idem)
    if result.get("success"):
        result["ai_credits"] = int(product["ai_credits"])
    return jsonify(result), 200 if result.get("success") else 502


def _cart_orders(items: list[dict]) -> tuple[list[dict], int]:
    products = {str(row["id"]): row for row in load_products()}
    orders: list[dict] = []
    for item in items[:20]:
        product = products.get(str(item.get("id")))
        if not product:
            raise ValueError("Sepette geçersiz ürün var")
        try:
            qty = max(1, min(int(item.get("qty", 1)), int(product.get("max_qty", 3) or 3), 5))
        except (TypeError, ValueError):
            raise ValueError("Ürün adedi geçersiz") from None
        for _ in range(qty):
            order = _make_order(product)
            if product.get("store_category") == "credits":
                order.update({"is_credit": True, "ai_credits": _credit_amount_for_product(product)})
            orders.append(order)
    if not orders:
        raise ValueError("Sepet boş")
    return orders, sum(int(row["subtotal_kurus"]) for row in orders)


def _settle_cart_orders(user_id: int, orders: list[dict], purchase_id: str) -> list[dict]:
    finalized = []
    for order in orders:
        if order.get("is_credit"):
            store.credit_balance(
                user_id,
                ai_credits=int(order.get("ai_credits", 0)),
                idempotency_key=f"cart-credit:{purchase_id}:{order['order_id']}",
                title=str(order.get("title") or "Froxy AI kredi paketi"),
            )
            finalized.append({**order, "status": "delivered", "delivery_note": "AI kredileri anında hesabına tanımlandı", "support_handle": SUPPORT_HANDLE})
        else:
            finalized.append(_finalize_delivery(order))
    store.finalize_orders(user_id, finalized)
    return finalized


@app.route("/api/checkout", methods=["POST"])
def create_checkout():
    telegram_user, error = _require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode") or "wallet")
    idem = str(data.get("idempotency_key") or uuid.uuid4().hex)[:120]
    try:
        orders, total = _cart_orders(data.get("items") or [])
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    user_id = int(telegram_user["id"])
    if mode == "wallet":
        try:
            reserved = store.reserve_wallet_purchase(user_id, idem, total, orders)
        except InsufficientBalance as exc:
            return jsonify({"success": False, "error": str(exc), "required_kurus": total}), 402
        if reserved.get("duplicate"):
            return jsonify({"success": True, "completed": True, **reserved})
        finalized = _settle_cart_orders(user_id, orders, idem)
        return jsonify({"success": True, "completed": True, "orders": finalized, "new_balance": round(int(reserved["wallet_kurus"]) / 100, 2)})
    if mode not in {"card", "hybrid_shortfall"}:
        return jsonify({"success": False, "error": "Geçersiz ödeme yöntemi"}), 400
    if not _shopier_token():
        return jsonify({"success": False, "error": "Shopier ödeme altyapısı yapılandırılmadı"}), 503
    user = store.get_user(user_id) or {}
    wallet = int(user.get("wallet_kurus", 0)) if mode == "hybrid_shortfall" else 0
    shortfall = max(0, total - wallet)
    if shortfall == 0:
        try:
            reserved = store.reserve_wallet_purchase(user_id, idem, total, orders)
        except InsufficientBalance as exc:
            return jsonify({"success": False, "error": str(exc)}), 402
        finalized = _settle_cart_orders(user_id, orders, idem)
        return jsonify({"success": True, "completed": True, "orders": finalized, "new_balance": round(int(reserved["wallet_kurus"]) / 100, 2)})
    charge_kurus = max(1000, shortfall if mode == "hybrid_shortfall" else total)
    result = _create_topup(
        telegram_user,
        amount=round(charge_kurus / 100, 2),
        kind="cart_shortfall" if mode == "hybrid_shortfall" else "cart_card",
        product=None,
        idempotency_key=idem,
        metadata={"items": data.get("items") or [], "cart_total_kurus": total, "checkout_mode": mode},
    )
    if result.get("success"):
        result.update({"completed": False, "required_kurus": charge_kurus, "cart_total_kurus": total, "checkout_mode": mode})
    return jsonify(result), (200 if result.get("success") else 502)


def _paid_shopier_orders() -> list[dict]:
    token = _shopier_token()
    if not token:
        return []
    try:
        response = requests.get("https://api.shopier.com/v1/orders?limit=50", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=25)
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
            is_cart = topup.get("kind") in {"cart_shortfall", "cart_card"}
            result = store.credit_balance(uid, wallet_kurus=int(topup["amount_kurus"]) if topup.get("kind") == "wallet" or is_cart else 0, ai_credits=int(topup.get("ai_credits", 0)) if topup.get("kind") == "credits" else 0, idempotency_key=f"shopier:{order_id}:{pid}", title="Froxy AI kredi paketi" if topup.get("kind") == "credits" else "Froxy mağaza ödeme bakiyesi")
            completed_orders = []
            checkout_error = ""
            if is_cart:
                try:
                    cart_orders, cart_total = _cart_orders((topup.get("metadata") or {}).get("items") or [])
                    purchase = store.reserve_wallet_purchase(uid, str(topup.get("idempotency_key") or pid), cart_total, cart_orders)
                    if purchase.get("duplicate"):
                        completed_orders = purchase.get("orders") or []
                    else:
                        completed_orders = _settle_cart_orders(uid, cart_orders, str(topup.get("idempotency_key") or pid))
                except (ValueError, InsufficientBalance) as exc:
                    checkout_error = str(exc)
            final_status = "completed" if not checkout_error else "payment_completed_purchase_pending"
            store.update_topup(pid, {"status": final_status, "shopier_order_id": order_id, "completed_at": int(time.time()), "checkout_error": checkout_error, "order_ids": [row.get("order_id") for row in completed_orders]})
            cancel_and_delete_topup(pid)
            credited.append({"user_id": uid, "product_id": pid, "order_id": order_id, "checkout_status": final_status, "orders": completed_orders, **result})
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
    return jsonify({"success": False, "error": "Hediye çarkı kaldırıldı; günlük 3 sohbet ve 1 görsel hakkı kullanabilirsiniz"}), 410


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
_start_image_recovery()


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
