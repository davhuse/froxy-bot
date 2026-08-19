#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi — BarlasMedya Tarzı Dinamik Shopier Bakiye Motoru (v3.0)
- Kullanıcının Telegram adı, soyadı ve ID'si ile anlık sıfır Shopier ilanı açar.
- Ödeme yapıldığında Shopier Orders API'den teyit edip bakiyeyi anında cüzdana yükler.
- Ödenen veya 1 saat içinde satın alınmayan sahipsiz ilanları Shopier'dan otomatik SİLER (mağaza temiz kalır).
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CREDITED_ORDERS_PATH = BASE_DIR / "credited_orders.json"
PENDING_TOPUPS_PATH = BASE_DIR / "pending_topups.json"

def get_shopier_token():
    return os.environ.get("SHOPIER_KEYVADI_ACCESS_TOKEN", "").strip()

def load_json_file(path, default_val):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

CACHED_CDN_URL = "https://cdn.shopier.app/pictures_large/keyvadi_a71b72ba-c88a-4be2-a240-08d0a7f22888.png"

def delete_shopier_product(product_id: str):
    """Shopier'dan ilanı siler (ödenen veya süresi geçen dinamik ilanları temizler)"""
    token = get_shopier_token()
    if not token or not product_id:
        return False
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.delete(f"https://api.shopier.com/v1/products/{product_id}", headers=headers, timeout=5)
        return res.status_code in [200, 204]
    except Exception:
        return False

def create_dynamic_shopier_listing(amount: float, user_id: int, user_name: str = "", username: str = "", idempotency_key: str = "") -> dict:
    """
    Shopier REST API üzerinden anlık, tam istenen tutarda dinamik sıfır ürün ilanı açar.
    Kullanıcının Telegram Adı, Soyadı, @kullanıcıadı ve ID'sini başlığa ve açıklamaya işler.
    """
    token = get_shopier_token()
    if not token:
        return {"success": False, "error": "Shopier bağlantısı yapılandırılmamış", "is_live_shopier": False}
    amount_str = f"{amount:.2f}"
    
    display_user = f"{user_name}".strip()
    if not display_user:
        display_user = "Müşteri"

    pending = load_json_file(PENDING_TOPUPS_PATH, {})
    if idempotency_key:
        for existing in pending.values():
            if (existing.get("user_id") == user_id and
                    existing.get("idempotency_key") == idempotency_key and
                    existing.get("status") == "pending"):
                return {"success": True, "duplicate": True,
                        "product_id": existing.get("product_id"),
                        "payment_url": existing.get("payment_url"),
                        "amount": existing.get("amount"), "is_live_shopier": True}

    product_title = f"KeyVadi Bakiye (₺{amount_str}) - {display_user}"
    product_desc = (
        f"KeyVadi Telegram Mini App Otomatik Bakiye Yükleme.\n"
        f"Müşteri: {display_user}\n"
        f"Yüklenecek Tutar: {amount_str} TL\n"
        f"Ödeme doğrulamaya bağlı olarak en geç 10 dakika içinde bakiyeye yansır."
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "title": product_title,
        "type": "digital",
        "description": product_desc,
        "priceData": {
            "currency": "TRY",
            "price": amount_str,
            "discount": False,
            "discountedPrice": amount_str,
            "shippingPrice": "0.00"
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays",
        "media": [
            {
                "type": "image",
                "url": CACHED_CDN_URL,
                "placement": 1
            }
        ]
    }

    try:
        res = requests.post("https://api.shopier.com/v1/products", headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            product_id = str(data.get("id"))
            shopier_url = f"https://www.shopier.com/keyvadi/{product_id}"

            pending[product_id] = {
                "product_id": product_id,
                "user_id": user_id,
                "user_name": display_user,
                "amount": amount,
                "idempotency_key": idempotency_key,
                "created_at": time.time(),
                "status": "pending",
                "payment_url": shopier_url
            }
            save_json_file(PENDING_TOPUPS_PATH, pending)

            print(f"[+] Dinamik Shopier İlanı Açıldı: {product_id} -> {shopier_url} ({amount} TL | {display_user})")
            return {
                "success": True,
                "product_id": product_id,
                "payment_url": shopier_url,
                "amount": amount,
                "is_live_shopier": True
            }
        else:
            print(f"[!] Shopier API Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"[!] Shopier API Exception: {e}")

    return {
        "success": False,
        "error": "Shopier ilanı oluşturulamadı",
        "amount": amount,
        "is_live_shopier": False
    }

def cleanup_abandoned_shopier_listings():
    """
    1 saatten eski olan ve ödenmemiş sahipsiz dinamik ilanları Shopier'dan siler.
    Böylece Shopier mağazanızda gereksiz ilan birikmez.
    """
    pending = load_json_file(PENDING_TOPUPS_PATH, {})
    now = time.time()
    to_delete = []

    for pid, info in list(pending.items()):
        created = info.get("created_at", now)
        # 1 hour timeout (3600 seconds)
        if now - created > 3600 and info.get("status") == "pending":
            print(f"[*] Sahipsiz dinamik ilan siliniyor: {pid} ({info.get('amount')} TL)")
            delete_shopier_product(pid)
            to_delete.append(pid)

    if to_delete:
        for pid in to_delete:
            pending.pop(pid, None)
        save_json_file(PENDING_TOPUPS_PATH, pending)

def check_and_sync_shopier_orders(users_db_path) -> list:
    """
    Shopier son siparişleri tarar, paymentStatus == 'paid' olan ödemeleri
    kullanıcının cüzdan bakiyesine ekler ve tamamlanan ilanı Shopier'dan siler.
    """
    token = get_shopier_token()
    if not token:
        return []

    credited = load_json_file(CREDITED_ORDERS_PATH, [])
    pending = load_json_file(PENDING_TOPUPS_PATH, {})
    newly_credited = []

    try:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        res = requests.get("https://api.shopier.com/v1/orders?limit=20", headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            orders = data if isinstance(data, list) else data.get("orders", [])
            
            if users_db_path.exists():
                with open(users_db_path, "r", encoding="utf-8") as f:
                    users = json.load(f)
            else:
                users = {}

            for order in orders:
                order_id = str(order.get("id"))
                if order_id in credited:
                    continue

                # Check payment status
                payment_status = str(order.get("paymentStatus", "")).lower()
                order_status = str(order.get("status", "")).lower()

                if payment_status == "paid" or order_status in ["paid", "completed", "success"]:
                    items = order.get("lineItems", [])
                    for itm in items:
                        p_title = itm.get("productTitle", "") or itm.get("title", "")
                        p_id = str(itm.get("productId", ""))
                        
                        pending_info = pending.get(p_id)
                        target_user_id = None
                        amount = float(itm.get("price", 0.0))

                        if pending_info:
                            target_user_id = str(pending_info.get("user_id"))
                            amount = float(pending_info.get("amount", amount))
                        elif "ID:" in p_title:
                            try:
                                target_user_id = p_title.split("ID:")[1].strip().split("]")[0].split()[0]
                            except Exception:
                                pass

                        if target_user_id:
                            uid = str(target_user_id)
                            if uid not in users:
                                users[uid] = {
                                    "id": int(target_user_id),
                                    "username": "",
                                    "first_name": "Müşteri",
                                    "balance": 0.0,
                                    "referrals_count": 0,
                                    "referral_earnings": 0.0,
                                    "orders": []
                                }

                            users[uid]["balance"] += amount
                            users[uid]["orders"].append({
                                "type": "bakiye_yukleme",
                                "amount": amount,
                                "order_id": order_id,
                                "date": time.strftime("%Y-%m-%d %H:%M:%S")
                            })

                            credited.append(order_id)
                            newly_credited.append({
                                "order_id": order_id,
                                "user_id": target_user_id,
                                "amount": amount
                            })

                            # Otomatik temizleme: Tamamlanan dinamik ilanı Shopier'dan sil
                            if p_id in pending:
                                delete_shopier_product(p_id)
                                pending.pop(p_id, None)

            if newly_credited:
                with open(users_db_path, "w", encoding="utf-8") as f:
                    json.dump(users, f, ensure_ascii=False, indent=2)
                save_json_file(CREDITED_ORDERS_PATH, credited)
                save_json_file(PENDING_TOPUPS_PATH, pending)
                print(f"[+] {len(newly_credited)} yeni Shopier ödemesi kullanıcılara işlendi!")

    except Exception as e:
        print(f"[!] Shopier sync error: {e}")

    # Otomatik eski sahipsiz ilanları temizle
    try:
        cleanup_abandoned_shopier_listings()
    except Exception:
        pass

    return newly_credited
