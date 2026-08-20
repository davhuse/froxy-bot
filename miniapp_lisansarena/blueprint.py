# -*- coding: utf-8 -*-
"""
LisansArena — Telegram Mini App Flask Blueprint (v6.0)
Serves static SPA files & provides API endpoints for products, balance, and referrals.
Connects with LisansArena Shopier REST API.
"""

import os
import sys
import json
import time
import tempfile
import threading
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

try:
    from .shopier_dynamic import create_dynamic_shopier_listing, check_and_sync_shopier_orders, cancel_and_delete_topup, start_background_shopier_cleaner
except ImportError:
    from shopier_dynamic import create_dynamic_shopier_listing, check_and_sync_shopier_orders, cancel_and_delete_topup, start_background_shopier_cleaner

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_DB_PATH = BASE_DIR / "products_db.json"
USER_DATA_PATH = BASE_DIR / "users_data.json"
DATA_LOCK = threading.RLock()

la_bp = Blueprint("lisansarena_miniapp", __name__, static_folder=str(BASE_DIR), static_url_path="")

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
        fd, tmp_name = tempfile.mkstemp(prefix="la_users_", suffix=".json", dir=str(BASE_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, USER_DATA_PATH)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

def get_or_create_user(user_id, username="", first_name="", last_name=""):
    users = load_users()
    uid = str(user_id)
    full_name = f"{first_name} {last_name}".strip() or "LisansArena Müşterisi"
    
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

@la_bp.route("/")
def serve_index():
    return send_from_directory(str(BASE_DIR), "index.html")

@la_bp.route("/<path:path>")
def serve_static(path):
    target = BASE_DIR / path
    if target.exists() and target.is_file():
        return send_from_directory(str(BASE_DIR), path)
    return send_from_directory(str(BASE_DIR), "index.html")

# ==================== API ENDPOINTS ====================

@la_bp.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category", "all")
    q = request.args.get("q", "").lower().strip()
    products = load_products()

    if category and category != "all":
        if category == "vitrin":
            products = [p for p in products if p.get("showcase") is True or p.get("is_vitrin") is True]
        else:
            products = [p for p in products if p.get("category") == category]

    if q:
        products = [p for p in products if q in p.get("title", "").lower() or q in p.get("description", "").lower()]

    return jsonify({
        "success": True,
        "count": len(products),
        "products": products
    })

@la_bp.route("/api/user/<int:user_id>", methods=["GET", "POST"])
def get_or_update_user_profile(user_id):
    try:
        check_and_sync_shopier_orders(USER_DATA_PATH)
    except Exception:
        pass

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        username = data.get("username", "")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        user = get_or_create_user(user_id, username=username, first_name=first_name, last_name=last_name)
    else:
        user = get_or_create_user(user_id)

    return jsonify({
        "success": True,
        "user": user
    })

@la_bp.route("/api/user/profile", methods=["GET", "POST"])
def user_profile_endpoint():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 8797763469))
    return get_or_update_user_profile(user_id)

@la_bp.route("/api/balance/create-dynamic-topup", methods=["POST"])
def create_dynamic_topup():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 8797763469))
    user_name = data.get("user_name", "LisansArena Müşteri")
    username = data.get("username", "")
    
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

@la_bp.route("/api/balance/cancel-topup", methods=["POST"])
def cancel_topup():
    """Kullanıcı ödeme yapmaktan vazgeçtiğinde veya sayfadan çıktığında ilanı anında siler."""
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("product_id", "")).strip()
    if product_id:
        cancel_and_delete_topup(product_id)
        return jsonify({"success": True, "message": "İlan başarıyla silindi"})
    return jsonify({"success": False, "error": "Geçersiz product_id"}), 400

@la_bp.route("/api/balance/sync-orders", methods=["GET"])
def sync_orders():
    credited = check_and_sync_shopier_orders(USER_DATA_PATH)
    return jsonify({
        "success": True,
        "credited_orders": credited,
        "count": len(credited)
    })

# Arka plan otomatik ilan temizleyicisini baslat
start_background_shopier_cleaner(USER_DATA_PATH)

@la_bp.route("/api/user/purchase", methods=["POST"])
def purchase_product():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
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
        user = users.get(uid) or get_or_create_user(int(user_id))
        price = float(product.get("price_num", 0.0))
        if user["balance"] < price:
            return jsonify({"success": False, "error": "Yetersiz bakiye"}), 400
        user["balance"] -= price
        order = {
            "product_id": product_id,
            "title": product.get("title"),
            "price": price,
            "status": "pending_delivery",
            "created_at": int(time.time())
        }
        user.setdefault("orders", []).append(order)
        users[uid] = user
        save_users(users)

    return jsonify({
        "success": True,
        "message": "Sipariş kaydınız alındı; teslimat sağlanıyor.",
        "new_balance": user["balance"],
        "order": order
    })

@la_bp.route("/api/user/purchase-cart", methods=["POST"])
def purchase_cart():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    items = data.get("items", [])

    if not user_id or not items:
        return jsonify({"success": False, "error": "Sepet boş veya kullanıcı geçersiz"}), 400

    products = {str(p.get("id")): p for p in load_products()}
    total_cost = 0.0
    valid_orders = []

    for it in items:
        pid = str(it.get("id"))
        qty = int(it.get("qty", 1))
        if pid in products:
            p = products[pid]
            p_price = float(p.get("price_num", 0.0))
            subtotal = p_price * qty
            total_cost += subtotal
            valid_orders.append({
                "product_id": pid,
                "title": p.get("title"),
                "qty": qty,
                "price": p_price,
                "subtotal": subtotal,
                "status": "pending_delivery",
                "created_at": int(time.time())
            })

    if not valid_orders:
        return jsonify({"success": False, "error": "Geçerli ürün bulunamadı"}), 400

    total_cost = round(total_cost, 2)

    with DATA_LOCK:
        users = load_users()
        uid = str(user_id)
        user = users.get(uid) or get_or_create_user(int(user_id))
        if user["balance"] < total_cost:
            return jsonify({"success": False, "error": f"Yetersiz bakiye! Gerekli: ₺{total_cost:.2f}, Mevcut: ₺{user['balance']:.2f}"}), 400
        
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

@la_bp.route("/api/referrals/<int:user_id>", methods=["GET"])
def get_referral_info(user_id):
    user = get_or_create_user(user_id)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "ref_link": f"https://t.me/LisansArenaBot?start=ref_{user_id}",
        "referrals_count": user.get("referrals_count", 0),
        "referral_earnings": user.get("referral_earnings", 0.0),
        "commission_rate": 0.10
    })
