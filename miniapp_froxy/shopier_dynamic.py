# -*- coding: utf-8 -*-
"""
Froxy â€” Dinamik Shopier Bakiye Motoru ve Otomatik Ä°lan KapatÄ±cÄ± (v8.0)
Ã–zellikler:
- AnlÄ±k bakiye ilanÄ± aÃ§ma (Shopier REST API v1)
- Ã–deme yapÄ±lÄ±nca anÄ±nda bakiyeyi tanÄ±mlayÄ±p ilanÄ± silme
- KullanÄ±cÄ± satÄ±n almazsa, iptal ederse veya Ã§Ä±karsa ilanÄ± ANINDA Shopier'dan silme
- Arka planda bir saati aÅŸan tÃ¼m satÄ±n alÄ±nmamÄ±ÅŸ ilanlarÄ± otomatik kapatma
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

# Froxy Shopier Bearer Token
FROXY_TOKEN = (
    os.environ.get("SHOPIER_FROXY_ACCESS_TOKEN")
    or os.environ.get("SHOPIER_KEYVADI_ACCESS_TOKEN")
    or os.environ.get("SHOPIER_BEARER_TOKEN")
    or ""
).strip()
FROXY_TOPUP_MEDIA_URL = os.environ.get(
    "FROXY_TOPUP_MEDIA_URL",
    "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp_froxy/assets/froxy_logo.png",
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
    """Belirtilen ilanÄ± hem Shopier'dan hem de yerel tablodan anÄ±nda siler."""
    pid = str(product_id).strip()
    if not pid:
        return False

    headers = {
        "Authorization": f"Bearer {FROXY_TOKEN}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=headers, timeout=8)
    except Exception as e:
        print(f"[Froxy Cancel Error] {e}")

    topups = load_active_topups()
    if pid in topups:
        del topups[pid]
        save_active_topups(topups)
    return True

def cleanup_user_previous_topups(user_id: int):
    """KullanÄ±cÄ±nÄ±n daha Ã¶nce aÃ§Ä±lmÄ±ÅŸ olup satÄ±n alÄ±nmamÄ±ÅŸ ilanlarÄ±nÄ± siler."""
    topups = load_active_topups()
    pids_to_del = []
    for pid, info in topups.items():
        if str(info.get("user_id")) == str(user_id) and info.get("status") == "pending":
            pids_to_del.append(pid)
    
    for pid in pids_to_del:
        cancel_and_delete_topup(pid)

def create_dynamic_shopier_listing(
    amount: float,
    user_id: int,
    user_name: str = "",
    username: str = "",
    idempotency_key: str = "",
    purpose: str = "wallet",
    purpose_title: str = "",
    persist_local: bool = True,
) -> dict:
    """Shopier REST API v1 ile Froxy iÃ§in anlÄ±k ilan aÃ§ar."""
    if not FROXY_TOKEN:
        return {"success": False, "error": "Shopier eriÅŸim anahtarÄ± yapÄ±landÄ±rÄ±lmamÄ±ÅŸ"}
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
    # Ã–nceki aÃ§Ä±k kalanlarÄ± temizle
    cleanup_user_previous_topups(user_id)

    token = FROXY_TOKEN
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    display_name = user_name or (f"@{username}" if username else f"MÃ¼ÅŸteri #{user_id}")
    clean_amount = round(float(amount), 2)
    
    is_credit = str(purpose).lower() == "credits"
    listing_title = (
        f"{purpose_title or 'Froxy AI Kredi Paketi'} - {display_name}"
        if is_credit
        else f"Froxy Mağaza Cüzdanı ({clean_amount:.2f} TL) - {display_name}"
    )
    payload = {
        "title": listing_title,
        "type": "digital",
        "description": (
            f"Froxy AI kullanım kredisi | Müşteri: {display_name}"
            if is_credit
            else f"Froxy mağaza cüzdanı yükleme | Müşteri: {display_name}"
        ),
        "stockQuantity": 1,
        "shippingPayer": "sellerPays",
        "priceData": {
            "currency": "TRY",
            "price": clean_amount,
            "discount": False,
            "shippingPrice": 0.0
        },
        "media": [{"type": "image", "url": FROXY_TOPUP_MEDIA_URL, "placement": 1}]
    }

    try:
        res = requests.post("https://api.shopier.com/v1/products", headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            data = res.json()
            pid = str(data.get("id"))
            pay_url = f"https://www.shopier.com/froxy/{pid}"

            if persist_local:
                topups = load_active_topups()
                topups[pid] = {
                    "user_id": user_id,
                    "amount": clean_amount,
                    "created_at": time.time(),
                    "payment_url": pay_url,
                    "status": "pending",
                    "idempotency_key": idempotency_key,
                    "purpose": "credits" if is_credit else "wallet",
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
            print(f"[Froxy Shopier Error] {res.status_code}: {res.text}")
            return {
                "success": False,
                "error": f"Shopier API HatasÄ± ({res.status_code}): {res.text}"
            }
    except Exception as e:
        print(f"[Froxy Shopier Exception] {e}")
        return {
            "success": False,
            "error": str(e)
        }

def check_and_sync_shopier_orders(users_data_path: Path):
    """Gelen Shopier sipariÅŸlerini kontrol edip bakiyeyi anÄ±nda tanÄ±mlar ve ilanÄ± siler."""
    token = FROXY_TOKEN
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }

    topups = load_active_topups()
    if not topups:
        return []

    credited_orders = []
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
                            order_id = str(ord_item.get("id") or ord_item.get("orderId") or pid)

                            if users_data_path.exists():
                                try:
                                    with open(users_data_path, "r", encoding="utf-8") as f:
                                        users = json.load(f)
                                    if uid in users:
                                        already_credited = any(
                                            str(row.get("order_id")) == order_id
                                            and row.get("type") == "bakiye_yukleme"
                                            for row in users[uid].get("orders", [])
                                        )
                                        if not already_credited:
                                            users[uid]["balance"] = round(users[uid].get("balance", 0.0) + amt, 2)
                                            users[uid].setdefault("orders", []).append({
                                                "type": "bakiye_yukleme",
                                                "order_id": order_id,
                                                "product_id": pid,
                                                "title": "Froxy bakiye yÃ¼kleme",
                                                "amount": amt,
                                                "status": "completed",
                                                "created_at": int(time.time())
                                            })
                                        with open(users_data_path, "w", encoding="utf-8") as f:
                                            json.dump(users, f, ensure_ascii=False, indent=2)
                                except Exception as ue:
                                    print(f"[Froxy User Save Error] {ue}")

                            t_info["status"] = "completed"
                            topups[pid] = t_info
                            save_active_topups(topups)
                            credited_orders.append({"user_id": uid, "amount": amt, "product_id": pid})

                            try:
                                requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=headers, timeout=8)
                            except Exception:
                                pass
    except Exception as e:
        print(f"[Froxy Shopier Sync Error] {e}")

    now = time.time()
    expired_pids = []
    for pid, info in list(topups.items()):
        if info.get("status") == "pending" and (now - info.get("created_at", now)) > 3600:
            expired_pids.append(pid)
    
    for pid in expired_pids:
        print(f"[Froxy Auto-Cleaner] SÃ¼resi dolan ilan siliniyor: {pid}")
        cancel_and_delete_topup(pid)

    return credited_orders

def start_background_shopier_cleaner(users_data_path: Path):
    """Her 20 saniyede bir sipariÅŸleri kontrol eder ve satÄ±n alÄ±nmayan ilanlarÄ± siler."""
    global _cleaner_started
    if _cleaner_started:
        return
    _cleaner_started = True

    def _worker():
        while True:
            try:
                check_and_sync_shopier_orders(users_data_path)
            except Exception as e:
                print(f"[Froxy Cleaner Worker Error] {e}")
            time.sleep(20)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    print("[Froxy] Otomatik Ä°lan Temizleme Arka Plan Servisi BaÅŸlatÄ±ldÄ± (20s dÃ¶ngÃ¼, 5dk TTL).")

