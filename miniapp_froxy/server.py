#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Froxy Telegram Mini App — Backend Server (v3.0)
Serves static SPA files & provides API endpoints for products, balance, and referrals.
Includes Telegram User Binding, BarlasMedya-style Dynamic Shopier Listing & Real-Time Sync.
"""

import os
import sys
import json
import socket
import hashlib
import hmac
import tempfile
import time
import threading
from urllib.parse import parse_qsl
from pathlib import Path

try:
    from license_delivery import allocate_license
except ImportError:
    try:
        from ..license_delivery import allocate_license
    except Exception:
        def allocate_license(t): return {"status": "pending_delivery", "license_key": None}

# Ensure UTF-8 output on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, jsonify, request, send_from_directory
try:
    from .shopier_dynamic import create_dynamic_shopier_listing, check_and_sync_shopier_orders, cancel_and_delete_topup, load_active_topups, start_background_shopier_cleaner
except (ImportError, ValueError):
    from shopier_dynamic import create_dynamic_shopier_listing, check_and_sync_shopier_orders, cancel_and_delete_topup, load_active_topups, start_background_shopier_cleaner

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_DB_PATH = BASE_DIR / "products_db.json"
USER_DATA_PATH = BASE_DIR / "users_data.json"
DATA_LOCK = threading.RLock()
MAX_INIT_DATA_AGE = int(os.environ.get("FROXY_INIT_DATA_MAX_AGE", "86400"))

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

# Ensure users database file exists
if not USER_DATA_PATH.exists():
    with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_products():
    if PRODUCTS_DB_PATH.exists():
        with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_users():
    with DATA_LOCK:
        if USER_DATA_PATH.exists():
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def save_users(data):
    with DATA_LOCK:
        fd, tmp_name = tempfile.mkstemp(prefix="users_", suffix=".json", dir=str(BASE_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, USER_DATA_PATH)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

def _telegram_bot_token():
    return (os.environ.get("FROXY_BOT_TOKEN") or
            os.environ.get("FROXY_SUPPORT_BOT_TOKEN") or "").strip()

def verify_telegram_init_data(raw_init_data):
    """Validate Telegram Web App initData and return its user object."""
    if not raw_init_data or not _telegram_bot_token():
        return None
    try:
        pairs = dict(parse_qsl(raw_init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", "")
        auth_date = int(pairs.get("auth_date", "0"))
        if not received_hash or not auth_date or time.time() - auth_date > MAX_INIT_DATA_AGE:
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

def authenticated_user():
    raw = request.headers.get("X-Telegram-Init-Data", "")
    if not raw and request.is_json:
        raw = (request.get_json(silent=True) or {}).get("init_data", "")
    user = verify_telegram_init_data(raw)
    if user:
        return user
    runtime_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production")).strip().lower()
    if os.environ.get("FROXY_ALLOW_DEV_AUTH", "0") == "1" and runtime_env in {"development", "test", "local"}:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id") or request.args.get("user_id")
        if user_id:
            return {"id": int(user_id), "first_name": data.get("first_name", "Müşteri"),
                    "last_name": data.get("last_name", ""), "username": data.get("username", "")}
    return None

def auth_error():
    return jsonify({"success": False, "error": "Telegram doğrulaması gerekli"}), 401

def get_or_create_user(user_id, username="", first_name="", last_name=""):
    users = load_users()
    uid = str(user_id)
    full_name = f"{first_name} {last_name}".strip() or "Müşteri"
    
    if uid not in users:
        users[uid] = {
            "id": int(user_id),
            "username": username or "",
            "first_name": first_name or "Müşteri",
            "last_name": last_name or "",
            "full_name": full_name,
            "balance": 0.0,
            "referrals_count": 0,
            "referral_earnings": 0.0,
            "referred_by": None,
            "orders": []
        }
        save_users(users)
    else:
        # Update user profile info if provided
        updated = False
        if username and users[uid].get("username") != username:
            users[uid]["username"] = username
            updated = True
        if first_name and users[uid].get("first_name") != first_name:
            users[uid]["first_name"] = first_name
            users[uid]["last_name"] = last_name
            users[uid]["full_name"] = full_name
            updated = True
        if updated:
            save_users(users)

    return users[uid]

@app.route("/")
def serve_index():
    return send_from_directory(str(BASE_DIR), "index.html")

@app.route("/<path:path>")
def serve_static(path):
    target = BASE_DIR / path
    if target.exists() and target.is_file():
        return send_from_directory(str(BASE_DIR), path)
    return send_from_directory(str(BASE_DIR), "index.html")

# ==================== API ENDPOINTS ====================

@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category", "all")
    q = request.args.get("q", "").lower().strip()
    products = load_products()

    if category and category != "all":
        products = [p for p in products if p.get("category") == category]

    if q:
        products = [p for p in products if q in p.get("title", "").lower() or q in p.get("description", "").lower()]

    return jsonify({
        "success": True,
        "count": len(products),
        "products": products
    })

@app.route("/api/user/<int:user_id>", methods=["GET", "POST"])
def get_or_update_user_profile(user_id):
    try:
        check_and_sync_shopier_orders(USER_DATA_PATH)
    except Exception:
        pass

    telegram_user = authenticated_user()
    if not telegram_user or int(telegram_user.get("id", 0)) != int(user_id):
        return auth_error()
    data = request.get_json(silent=True) or {}

    if telegram_user:
        username = telegram_user.get("username", "") or data.get("username", "")
        first_name = telegram_user.get("first_name", "") or data.get("first_name", "")
        last_name = telegram_user.get("last_name", "") or data.get("last_name", "")
    else:
        username = data.get("username", "")
        first_name = data.get("first_name", "Froxy Müşteri")
        last_name = data.get("last_name", "")

    user = get_or_create_user(user_id, username=username, first_name=first_name, last_name=last_name)
    
    now = int(time.time())
    last_spin = int(user.get("last_spin_at", 0))
    cooldown = 86400
    elapsed = now - last_spin
    remaining = max(0, cooldown - elapsed) if last_spin > 0 else 0
    user["can_spin"] = remaining == 0
    user["spin_cooldown_remaining"] = remaining

    return jsonify({
        "success": True,
        "user": user
    })

# ==================== DINAMIK BAKİYE YÜKLEME (BARLASMEDYA TARZI) ====================

@app.route("/api/balance/create-dynamic-topup", methods=["POST"])
def create_dynamic_topup():
    """
    Kullanıcının girdiği tutarda ve Telegram profiline özel Shopier API üzerinden anlık sıfır ilan oluşturur.
    """
    data = request.get_json(silent=True) or {}
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    user_id = int(telegram_user["id"])
    user_name = telegram_user.get("first_name", "Froxy Müşteri")
    username = telegram_user.get("username", "")
    
    try:
        amount = float(data.get("amount", 50.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Geçersiz tutar"}), 400

    if amount < 5 or amount > 50000:
        return jsonify({"success": False, "error": "Minimum yükleme tutarı 5 TL'dir"}), 400

    result = create_dynamic_shopier_listing(
        amount=amount,
        user_id=user_id,
        user_name=user_name,
        username=username,
        idempotency_key=str(data.get("idempotency_key", "")).strip()
    )
    return jsonify(result)

@app.route("/api/balance/cancel-topup", methods=["POST"])
def cancel_topup():
    """Kullanıcı vazgeçtiğinde veya sayfadan ayrıldığında ilanı anında siler."""
    data = request.get_json(silent=True) or {}
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    product_id = str(data.get("product_id", "")).strip()
    if product_id:
        owner = (load_active_topups().get(product_id) or {}).get("user_id")
        if str(owner) != str(telegram_user["id"]):
            return jsonify({"success": False, "error": "Bu ilan size ait değil"}), 403
        cancel_and_delete_topup(product_id)
        return jsonify({"success": True, "message": "İlan silindi"})
    return jsonify({"success": False, "error": "Geçersiz product_id"}), 400

@app.route("/api/balance/sync-orders", methods=["GET"])
def sync_orders():
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    credited = check_and_sync_shopier_orders(USER_DATA_PATH)
    credited = [row for row in credited if str(row.get("user_id")) == str(telegram_user["id"])]
    return jsonify({
        "success": True,
        "credited_orders": credited,
        "count": len(credited)
    })

# Arka plan otomatik ilan temizleyicisini baslat
start_background_shopier_cleaner(USER_DATA_PATH)

@app.route("/api/balance/simulate-payment", methods=["POST"])
def simulate_payment():
    """
    Önizleme ve test amaçlı anında bakiye yükleme simülasyonu.
    """
    runtime_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production")).strip().lower()
    if os.environ.get("FROXY_ALLOW_SIMULATE_PAYMENT", "0") != "1" or runtime_env not in {"development", "test", "local"}:
        return jsonify({"success": False, "error": "Test ödeme endpointi kapalı"}), 404
    data = request.get_json() or {}
    user_id = str(data.get("user_id", 8797763469))
    amount = float(data.get("amount", 100.0))

    users = load_users()
    if user_id not in users:
        get_or_create_user(int(user_id))
        users = load_users()

    users[user_id]["balance"] += amount
    save_users(users)

    return jsonify({
        "success": True,
        "message": f"₺{amount:.2f} bakiye başarıyla yüklendi",
        "new_balance": users[user_id]["balance"]
    })

@app.route("/api/user/purchase", methods=["POST"])
def purchase_product():
    data = request.get_json(silent=True) or {}
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    user_id = int(telegram_user["id"])
    product_id = str(data.get("product_id"))

    if not user_id or not product_id:
        return jsonify({"success": False, "error": "Eksik parametreler"}), 400

    products = load_products()
    product = next((p for p in products if str(p.get("id")) == product_id), None)
    if not product:
        return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404

    with DATA_LOCK:
        users = load_users()
        uid = str(user_id)
        user = users.get(uid) or get_or_create_user(
            user_id,
            username=telegram_user.get("username", ""),
            first_name=telegram_user.get("first_name", "Müşteri"),
            last_name=telegram_user.get("last_name", "")
        )
        idem = str(data.get("idempotency_key", "")).strip()
        if idem:
            for existing in user.get("orders", []):
                if existing.get("idempotency_key") == idem:
                    return jsonify({"success": True, "duplicate": True,
                                    "new_balance": user["balance"], "order": existing})
        price = float(product.get("price_num", 0.0))
        if user["balance"] < price:
            return jsonify({"success": False, "error": "Yetersiz bakiye"}), 400
        user["balance"] -= price
        alloc = allocate_license(product.get("title", ""), brand="froxy")
        order = {
            "order_id": f"KV-{int(time.time())}",
            "product_id": product_id,
            "title": product.get("title"),
            "price": price,
            "status": alloc.get("status", "pending_delivery"),
            "license_key": alloc.get("license_key"),
            "delivery_note": alloc.get("delivery_note", "7/24 Teslimat"),
            "support_handle": alloc.get("support_handle", "@FroxyDestek"),
            "redeem_url": alloc.get("redeem_url"),
            "activation_guide": alloc.get("activation_guide"),
            "needs_email": alloc.get("needs_email", False),
            "idempotency_key": idem or None,
            "created_at": int(time.time())
        }
        user.setdefault("orders", []).append(order)
        users[uid] = user
        save_users(users)

    return jsonify({
        "success": True,
        "message": "🎉 Siparişiniz başarıyla alındı!" if order.get("status") == "delivered" else "Sipariş kaydınız alındı; teslimat doğrulanıyor.",
        "new_balance": user["balance"],
        "order": order
    })

@app.route("/api/user/purchase-cart", methods=["POST"])
def purchase_cart():
    data = request.get_json(silent=True) or {}
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    user_id = int(telegram_user["id"])
    
    items = data.get("items", [])
    if not items:
        return jsonify({"success": False, "error": "Sepet boş"}), 400
    idempotency_key = str(data.get("idempotency_key") or "").strip()[:160]
    if not idempotency_key:
        return jsonify({"success": False, "error": "Güvenli sepet anahtarı eksik"}), 400

    products = {str(p.get("id")): p for p in load_products()}
    total_cost = 0.0
    valid_orders = []

    for it in items:
        pid = str(it.get("id"))
        try:
            qty = int(it.get("qty", 1))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Ürün adedi geçersiz"}), 400
        if pid in products:
            p = products[pid]
            max_qty = max(1, min(int(p.get("max_qty") or 1), 10))
            if qty < 1 or qty > max_qty:
                return jsonify({"success": False, "error": f"{p.get('title')}: en fazla {max_qty} adet alınabilir"}), 400
            stock = p.get("stock")
            if isinstance(stock, (int, float)) and stock >= 0 and qty > int(stock):
                return jsonify({"success": False, "error": f"Stok yetersiz: {p.get('title')}"}), 409
            p_price = float(p.get("price_num", 0.0))
            subtotal = p_price * qty
            total_cost += subtotal
            alloc = allocate_license(p.get("title", ""), brand="froxy")
            valid_orders.append({
                "order_id": f"KV-{int(time.time())}",
                "product_id": pid,
                "title": p.get("title"),
                "qty": qty,
                "price": p_price,
                "subtotal": subtotal,
                "status": alloc.get("status", "pending_delivery"),
                "license_key": alloc.get("license_key"),
                "delivery_note": alloc.get("delivery_note", "7/24 Teslimat"),
                "support_handle": alloc.get("support_handle", "@FroxyDestek"),
                "redeem_url": alloc.get("redeem_url"),
                "activation_guide": alloc.get("activation_guide"),
                "needs_email": alloc.get("needs_email", False),
                "cart_idempotency_key": idempotency_key,
                "created_at": int(time.time())
            })

    if not valid_orders:
        return jsonify({"success": False, "error": "Geçerli ürün bulunamadı"}), 400

    total_cost = round(total_cost, 2)

    with DATA_LOCK:
        users = load_users()
        uid = str(user_id)
        user = users.get(uid) or get_or_create_user(int(user_id))
        duplicates = [
            order for order in user.get("orders", [])
            if order.get("cart_idempotency_key") == idempotency_key
        ]
        if duplicates:
            return jsonify({
                "success": True, "duplicate": True,
                "message": "Bu sepet daha önce işlendi.",
                "new_balance": user["balance"], "orders": duplicates,
            })
        if user["balance"] < total_cost:
            shortfall = round(total_cost - float(user["balance"]), 2)
            return jsonify({
                "success": False,
                "error": f"Yetersiz bakiye! Gerekli: ₺{total_cost:.2f}, Mevcut: ₺{user['balance']:.2f}",
                "required_amount": total_cost,
                "balance": float(user["balance"]),
                "balance_shortfall": shortfall,
            }), 400
        
        user["balance"] = round(user["balance"] - total_cost, 2)
        user.setdefault("orders", []).extend(valid_orders)
        users[uid] = user
        save_users(users)

    return jsonify({
        "success": True,
        "message": f"🎉 Toplam ₺{total_cost:.2f} tutarındaki {len(valid_orders)} ürünlük sepetiniz başarıyla satın alındı!",
        "new_balance": user["balance"],
        "orders": valid_orders
    })

@app.route("/api/user/spin", methods=["POST"])
def spin_daily_wheel():
    import random
    telegram_user = authenticated_user()
    if not telegram_user:
        return auth_error()
    user_id = int(telegram_user["id"])
    
    with DATA_LOCK:
        users = load_users()
        uid = str(user_id)
        user = users.get(uid) or get_or_create_user(
            user_id,
            username=telegram_user.get("username", ""),
            first_name=telegram_user.get("first_name", "Müşteri"),
            last_name=telegram_user.get("last_name", "")
        )
        
        now = int(time.time())
        last_spin = int(user.get("last_spin_at", 0))
        cooldown = 86400  # 24 hours
        
        if (now - last_spin) < cooldown:
            remaining_secs = cooldown - (now - last_spin)
            hours = remaining_secs // 3600
            mins = (remaining_secs % 3600) // 60
            return jsonify({
                "success": False,
                "error": f"Günde 1 kez çark çevirebilirsiniz. Kalan süre: {hours} sa {mins} dk.",
                "next_spin_in": remaining_secs
            }), 429
            
        prizes = [
            {"segment": 0, "type": "balance", "amount": 1.0, "text": "₺1.00 Bakiye"},
            {"segment": 1, "type": "coupon", "code": "FROXY10", "text": "%10 İndirim Kuponu (FROXY10)"},
            {"segment": 2, "type": "balance", "amount": 2.0, "text": "₺2.00 Bakiye"},
            {"segment": 3, "type": "coupon", "code": "FROXY15", "text": "%15 VIP İndirim Kuponu (FROXY15)"},
            {"segment": 4, "type": "balance", "amount": 3.0, "text": "₺3.00 Süper Bakiye"},
            {"segment": 5, "type": "balance", "amount": 5.0, "text": "🌟 ₺5.00 Büyük Ödül!"},
            {"segment": 6, "type": "none", "text": "Pas / Şansını Yarın Tekrar Dene"},
            {"segment": 7, "type": "balance", "amount": 0.5, "text": "₺0.50 Bakiye"}
        ]
        weights = [30, 20, 20, 10, 10, 5, 3, 2]
        chosen = random.choices(prizes, weights=weights, k=1)[0]
        
        user["last_spin_at"] = now
        if chosen["type"] == "balance":
            user["balance"] = round(user["balance"] + chosen["amount"], 2)
            user.setdefault("orders", []).append({
                "type": "spin_reward",
                "order_id": f"SPIN-{now}",
                "title": f"🎁 Günlük Çark Ödülü: {chosen['text']}",
                "amount": chosen["amount"],
                "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "created_at": now,
                "status": "completed"
            })
            
        users[uid] = user
        save_users(users)
        
        return jsonify({
            "success": True,
            "segment": chosen["segment"],
            "reward_type": chosen["type"],
            "reward_text": chosen["text"],
            "reward_amount": chosen.get("amount", 0.0),
            "coupon_code": chosen.get("code"),
            "new_balance": user["balance"],
            "message": f"Tebrikler! {chosen['text']} kazandınız!"
        })

@app.route("/api/referrals/<int:user_id>", methods=["GET"])
def get_referral_info(user_id):
    telegram_user = authenticated_user()
    if not telegram_user or int(telegram_user.get("id", 0)) != int(user_id):
        return auth_error()
    user = get_or_create_user(user_id)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "ref_link": f"https://t.me/FroxyDestekBOT?start=ref_{user_id}",
        "referrals_count": user.get("referrals_count", 0),
        "referral_earnings": user.get("referral_earnings", 0.0),
        "commission_rate": 0.10
    })

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    local_ip = get_local_ip()
    print("=" * 60)
    print("  [+] FROXY TELEGRAM MINI APP SUNUCUSU BASLATILDI")
    print(f"  [+] Yerel Baglanti:   http://localhost:{port}")
    print(f"  [+] Yerel Ag (Wi-Fi): http://{local_ip}:{port}")
    print(f"  [+] Shopier Magazasi: https://www.shopier.com/froxy")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
