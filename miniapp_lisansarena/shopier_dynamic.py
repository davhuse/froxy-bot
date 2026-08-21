# -*- coding: utf-8 -*-
"""
LisansArena — Dinamik Shopier Bakiye Motoru ve Otomatik İlan Kapatıcı (v8.0)
Özellikler:
- Anlık bakiye ilanı açma (Shopier REST API v1)
- Ödeme yapılınca anında bakiyeyi tanımlayıp ilanı silme
- Kullanıcı satın almazsa, iptal ederse veya çıkarsa ilanı ANINDA Shopier'dan silme
- Arka planda 5 dakikayı (300sn) aşan tüm satın alınmamış ilanları otomatik temizleme
"""

import os
import sys
import json
import time
import threading
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ACTIVE_TOPUPS_FILE = BASE_DIR / "active_topups.json"

LISANSARENA_TOKEN = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or "").strip()
LISANSARENA_TOPUP_MEDIA_URL = os.environ.get(
    "LISANSARENA_TOPUP_MEDIA_URL",
    "https://froxy-bot-live.onrender.com/la/app/assets/lisansarena_logo.png",
).strip()

_cleaner_started = False
_lock = threading.Lock()

def load_active_topups():
    with _lock:
        if ACTIVE_TOPUPS_FILE.exists():
            try:
                with open(ACTIVE_TOPUPS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

def save_active_topups(data):
    with _lock:
        with open(ACTIVE_TOPUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def cancel_and_delete_topup(product_id: str) -> bool:
    """Belirtilen ilanı hem Shopier'dan hem de yerel tablodan anında siler."""
    pid = str(product_id).strip()
    if not pid:
        return False

    token = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or LISANSARENA_TOKEN).strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }

    # Shopier API delete
    try:
        res = requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=headers, timeout=8)
        print(f"[LisansArena Cancel] Product {pid} silindi (HTTP {res.status_code})")
    except Exception as e:
        print(f"[LisansArena Cancel Error] {e}")

    topups = load_active_topups()
    if pid in topups:
        del topups[pid]
        save_active_topups(topups)
    return True

def cleanup_user_previous_topups(user_id: int):
    """Kullanıcının daha önce açılmış olup satın alınmamış ilanlarını siler."""
    topups = load_active_topups()
    pids_to_del = []
    for pid, info in topups.items():
        if str(info.get("user_id")) == str(user_id) and info.get("status") == "pending":
            pids_to_del.append(pid)
    
    for pid in pids_to_del:
        cancel_and_delete_topup(pid)

def create_dynamic_shopier_listing(amount: float, user_id: int, user_name: str = "", username: str = "", idempotency_key: str = "") -> dict:
    """Shopier REST API v1 ile LisansArena için anlık ilan açar."""
    token = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or LISANSARENA_TOKEN).strip()
    if not token:
        return {"success": False, "error": "Shopier erişim anahtarı yapılandırılmamış"}
    if idempotency_key:
        existing = next((
            (pid, info) for pid, info in load_active_topups().items()
            if str(info.get("user_id")) == str(user_id)
            and info.get("idempotency_key") == idempotency_key
            and info.get("status") == "pending"
        ), None)
        if existing:
            pid, info = existing
            return {
                "success": True, "duplicate": True, "product_id": pid,
                "payment_url": info["payment_url"], "amount": info["amount"],
                "is_live_shopier": True,
            }
    # Önceki açık kalanları temizle
    cleanup_user_previous_topups(user_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    display_name = user_name or (f"@{username}" if username else f"Müşteri #{user_id}")
    clean_amount = round(float(amount), 2)
    
    payload = {
        "title": f"LisansArena Cüzdan Bakiye Yükleme ({clean_amount:.2f} TL) - {display_name}",
        "type": "digital",
        "description": f"LisansArena özel bakiye yükleme | Müşteri: {display_name}",
        "stockQuantity": 1,
        "shippingPayer": "sellerPays",
        "priceData": {
            "currency": "TRY",
            "price": clean_amount,
            "discount": False,
            "shippingPrice": 0.0
        },
        "media": [{"type": "image", "url": LISANSARENA_TOPUP_MEDIA_URL, "placement": 1}]
    }

    try:
        res = requests.post("https://api.shopier.com/v1/products", headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            data = res.json()
            pid = str(data.get("id"))
            pay_url = f"https://www.shopier.com/lisansarena/{pid}"

            topups = load_active_topups()
            topups[pid] = {
                "user_id": user_id,
                "amount": clean_amount,
                "created_at": time.time(),
                "payment_url": pay_url,
                "status": "pending",
                "idempotency_key": idempotency_key
            }
            save_active_topups(topups)

            return {
                "success": True,
                "product_id": pid,
                "payment_url": pay_url,
                "amount": clean_amount,
                "is_live_shopier": True
            }
        else:
            print(f"[LisansArena Shopier Error] {res.status_code}: {res.text}")
            return {
                "success": False,
                "error": f"Shopier API Hatası ({res.status_code}): {res.text}"
            }
    except Exception as e:
        print(f"[LisansArena Shopier Exception] {e}")
        return {
            "success": False,
            "error": str(e)
        }

def sweep_orphan_shopier_products():
    """Shopier üzerindeki tüm açık kalmış dinamik bakiye ilanlarını tarar ve süresi dolan veya yetim kalanları siler."""
    token = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or LISANSARENA_TOKEN).strip()
    if not token:
        return
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        res = requests.get("https://api.shopier.com/v1/products?limit=50", headers=headers, timeout=12)
        if res.status_code == 200:
            payload = res.json()
            products_list = payload if isinstance(payload, list) else (payload.get("products") or payload.get("data") or [])
            now = time.time()
            ttl_seconds = int(os.environ.get("LISANSARENA_TOPUP_TTL_SECONDS", "900"))
            topups = load_active_topups()
            for prod in products_list:
                title = str(prod.get("title") or "")
                desc = str(prod.get("description") or "")
                pid = str(prod.get("id") or "")
                title_lower = title.lower()
                desc_lower = desc.lower()
                is_topup = (
                    ("lisansarena" in title_lower and ("bakiye" in title_lower or "cüzdan" in title_lower or "cuzdan" in title_lower or "yükle" in title_lower or "yukle" in title_lower))
                    or ("özel bakiye" in desc_lower or "ozel bakiye" in desc_lower or "bakiye yükleme" in desc_lower)
                )
                if is_topup:
                    info = topups.get(pid)
                    if info:
                        created_at = info.get("created_at", now)
                        if (now - created_at) > ttl_seconds and info.get("status") == "pending":
                            print(f"[LisansArena Auto-Cleaner] Süresi dolan ilan siliniyor: {pid}")
                            cancel_and_delete_topup(pid)
                    else:
                        print(f"[LisansArena Auto-Cleaner] Açıkta kalan bakiye ilanı siliniyor: {pid} ({title})")
                        cancel_and_delete_topup(pid)
    except Exception as e:
        print(f"[LisansArena Sweep Error] {e}")

def check_and_sync_shopier_orders(users_data_path: Path):
    """Gelen Shopier siparişlerini kontrol edip bakiyeyi anında tanımlar ve ilanı siler."""
    token = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or LISANSARENA_TOKEN).strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }

    topups = load_active_topups()
    credited_orders = []
    if topups:
        try:
            res = requests.get("https://api.shopier.com/v1/orders?limit=20", headers=headers, timeout=12)
            if res.status_code == 200:
                payload = res.json()
                orders = payload if isinstance(payload, list) else (payload.get("orders") or payload.get("data") or [])
                if isinstance(orders, list):
                    for ord_item in orders:
                        items = ord_item.get("lineItems") or ord_item.get("line_items") or ord_item.get("items") or []
                        ord_status = str(ord_item.get("paymentStatus") or ord_item.get("status") or ord_item.get("orderStatus") or "").lower()
                        if ord_status not in ["paid", "shipped", "delivered", "completed", "processing", "success"]:
                            continue

                        for item in items:
                            pid = str(item.get("productId") or item.get("product_id") or item.get("id") or "")
                            if pid in topups and topups[pid]["status"] == "pending":
                                t_info = topups[pid]
                                uid = str(t_info["user_id"])
                                amt = float(t_info["amount"])

                                if users_data_path.exists():
                                    try:
                                        with open(users_data_path, "r", encoding="utf-8") as f:
                                            users = json.load(f)
                                        if uid in users:
                                            users[uid]["balance"] = round(users[uid].get("balance", 0.0) + amt, 2)
                                            users[uid].setdefault("orders", []).append({
                                                "type": "bakiye_yukleme",
                                                "order_id": str(ord_item.get("id") or ord_item.get("orderId") or pid),
                                                "product_id": pid,
                                                "title": "LisansArena bakiye yükleme",
                                                "amount": amt,
                                                "status": "completed",
                                                "created_at": int(time.time())
                                            })
                                            with open(users_data_path, "w", encoding="utf-8") as f:
                                                json.dump(users, f, ensure_ascii=False, indent=2)
                                    except Exception as ue:
                                        print(f"[User Save Error] {ue}")

                                t_info["status"] = "completed"
                                topups[pid] = t_info
                                save_active_topups(topups)
                                credited_orders.append({"user_id": uid, "amount": amt, "product_id": pid})

                                # Satın alındı, ilanı derhal sil
                                try:
                                    requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=headers, timeout=8)
                                except Exception:
                                    pass
        except Exception as e:
            print(f"[LisansArena Shopier Sync Error] {e}")

    # Shopier üzerindeki tüm yetim ve açık kalmış bakiye ilanlarını temizle
    sweep_orphan_shopier_products()

    return credited_orders

def start_background_shopier_cleaner(users_data_path: Path):
    """Her 20 saniyede bir siparişleri kontrol eder ve satın alınmayan ilanları siler."""
    global _cleaner_started
    if _cleaner_started:
        return
    _cleaner_started = True

    def _worker():
        while True:
            try:
                check_and_sync_shopier_orders(users_data_path)
            except Exception as e:
                print(f"[LisansArena Cleaner Worker Error] {e}")
            time.sleep(20)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    print("[LisansArena] Otomatik İlan Temizleme Arka Plan Servisi Başlatıldı (20s döngü, 15dk TTL).")
