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
import uuid
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ACTIVE_TOPUPS_FILE = BASE_DIR / "active_topups.json"

LISANSARENA_TOKEN = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or "").strip()

def _durable_load_users(users_data_path: Path):
    try:
        from .blueprint import load_users
        return load_users()
    except Exception:
        try:
            from blueprint import load_users
            return load_users()
        except Exception:
            pass
    if users_data_path.exists():
        try:
            with open(users_data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _durable_save_users(users: dict, users_data_path: Path):
    try:
        from .blueprint import save_users
        save_users(users)
        return
    except Exception:
        try:
            from blueprint import save_users
            save_users(users)
            return
        except Exception:
            pass
    try:
        import firestore_helper
        firestore_helper.set_document("lisansarena_legacy_users_data", {"users": users})
    except Exception:
        pass
    try:
        with open(users_data_path, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_topup_media_url():
    base = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("PUBLIC_BASE_URL")
        or "https://bot-service-production-9d74.up.railway.app"
    ).rstrip("/")
    return (os.environ.get("LISANSARENA_TOPUP_MEDIA_URL") or f"{base}/la/app/assets/lisansarena_logo.png").strip()

try:
    from license_delivery import allocate_license
except ImportError:
    try:
        from ..license_delivery import allocate_license
    except Exception:
        def allocate_license(t, brand=None): return {"status": "pending_delivery", "license_key": None}

def _notify_admin_of_shopier_order(user_id, display_name, title, amount, license_key=None):
    token = os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
    admin_id = os.environ.get("TELEGRAM_ADMIN_ID", "8791896048")
    if not token or not admin_id:
        return
    try:
        key_info = f"\n🔑 **Lisans Kodu:** `{license_key}`" if license_key else "\n⚡ **Teslimat:** Otomatik / Destek Temsilcisi"
        text = (
            f"🛒 **[LisansArena] Shopier Üzerinden Yeni İşlem!**\n\n"
            f"👤 **Müşteri:** {display_name}\n"
            f"🆔 **Kullanıcı ID:** `{user_id}`\n"
            f"📦 **İşlem / Ürün:** {title}\n"
            f"💰 **Tutar:** `₺{float(amount):.2f}` (Shopier 3D ile ödendi)\n"
            f"{key_info}\n\n"
            f"*(Sipariş Mini App üzerinden otomatik işlendi.)*"
        )
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": int(admin_id),
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as exc:
        print(f"[LisansArena Notify Admin] {exc}")

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

def create_dynamic_shopier_listing(amount: float, user_id: int, user_name: str = "", username: str = "", idempotency_key: str = "", product_title: str = "", target_product_id: str = "") -> dict:
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
    
    if product_title:
        title_str = f"LisansArena — {product_title} ({clean_amount:.2f} TL) - {display_name}"
        desc_str = f"LisansArena siparişi: {product_title} | Müşteri: {display_name}"
    else:
        title_str = f"LisansArena Cüzdan Bakiye Yükleme ({clean_amount:.2f} TL) - {display_name}"
        desc_str = f"LisansArena özel bakiye yükleme | Müşteri: {display_name}"

    payload = {
        "title": title_str,
        "type": "digital",
        "description": desc_str,
        "stockQuantity": 1,
        "shippingPayer": "sellerPays",
        "priceData": {
            "currency": "TRY",
            "price": clean_amount,
            "discount": False,
            "shippingPrice": 0.0
        },
        "media": [{"type": "image", "url": get_topup_media_url(), "placement": 1}]
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
                "idempotency_key": idempotency_key,
                "product_title": product_title or "",
                "target_product_id": target_product_id or ""
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
    ttl_seconds = int(os.environ.get("LISANSARENA_TOPUP_TTL_SECONDS", "900"))
    now = time.time()

    # 1. Yerel veritabanındaki süresi dolan pending ilanları derhal sil
    topups = load_active_topups()
    expired_pids = []
    for pid, info in list(topups.items()):
        if info.get("status") == "pending" and (now - info.get("created_at", now)) > ttl_seconds:
            expired_pids.append(pid)
    for pid in expired_pids:
        print(f"[LisansArena Auto-Cleaner] Süresi dolan ilan siliniyor: {pid}")
        cancel_and_delete_topup(pid)

    # 2. Shopier API üzerinden de açık bakiye ilanlarını tara (erişim varsa)
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
    """Gelen Shopier siparişlerini kontrol edip bakiyeyi veya siparişi anında tanımlar ve ilanı siler."""
    token = (os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN") or os.environ.get("LISANSARENA_SHOPIER_BEARER_TOKEN") or LISANSARENA_TOKEN).strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }

    topups = load_active_topups()
    credited_orders = []
    if topups:
        try:
            res = requests.get("https://api.shopier.com/v1/orders?limit=20", headers=headers, timeout=25)
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
                                p_title = t_info.get("product_title", "").strip()
                                target_p_id = t_info.get("target_product_id", "").strip()
                                idem = t_info.get("idempotency_key", "")
                                shopier_order_id = str(ord_item.get("id") or ord_item.get("orderId") or pid)

                                users = _durable_load_users(users_data_path)
                                if uid not in users:
                                    users[uid] = {
                                        "id": int(uid),
                                        "username": "",
                                        "first_name": "Müşteri",
                                        "last_name": "",
                                        "full_name": f"Müşteri #{uid}",
                                        "balance": 0.0,
                                        "referrals_count": 0,
                                        "referral_earnings": 0.0,
                                        "referred_by": None,
                                        "orders": []
                                    }
                                user_obj = users[uid]

                                if p_title:
                                    # Kartla Direkt Satın Alındı: Lisans ata ve siparişi tamamla
                                    alloc = allocate_license(p_title, brand="lisansarena")
                                    order_rec = {
                                        "order_id": f"LA-SHP-{uuid.uuid4().hex[:8].upper()}",
                                        "shopier_order_id": shopier_order_id,
                                        "product_id": target_p_id or pid,
                                        "title": p_title,
                                        "price": amt,
                                        "amount": amt,
                                        "status": alloc.get("status", "pending_delivery"),
                                        "license_key": alloc.get("license_key"),
                                        "delivery_note": alloc.get("delivery_note", "7/24 Teslimat"),
                                        "support_handle": alloc.get("support_handle", "@LisansArenaOnline"),
                                        "redeem_url": alloc.get("redeem_url"),
                                        "activation_guide": alloc.get("activation_guide"),
                                        "needs_email": alloc.get("needs_email", False),
                                        "idempotency_key": idem,
                                        "created_at": int(time.time())
                                    }
                                    user_obj.setdefault("orders", []).append(order_rec)
                                    _notify_admin_of_shopier_order(
                                        uid, user_obj.get("full_name", f"Müşteri #{uid}"),
                                        p_title, amt, license_key=alloc.get("license_key")
                                    )
                                    credited_orders.append({
                                        "user_id": uid, "amount": amt, "product_id": pid,
                                        "type": "direct_purchase", "title": p_title, "order": order_rec
                                    })
                                else:
                                    # Cüzdan Bakiye Yükleme
                                    user_obj["balance"] = round(user_obj.get("balance", 0.0) + amt, 2)
                                    order_rec = {
                                        "type": "bakiye_yukleme",
                                        "order_id": f"TOPUP-{shopier_order_id}",
                                        "product_id": pid,
                                        "title": f"Cüzdan Bakiye Yükleme (₺{amt:.2f})",
                                        "price": amt,
                                        "amount": amt,
                                        "status": "completed",
                                        "idempotency_key": idem,
                                        "created_at": int(time.time())
                                    }
                                    user_obj.setdefault("orders", []).append(order_rec)
                                    _notify_admin_of_shopier_order(
                                        uid, user_obj.get("full_name", f"Müşteri #{uid}"),
                                        f"Cüzdan Bakiye Yükleme (₺{amt:.2f})", amt, license_key=None
                                    )
                                    credited_orders.append({
                                        "user_id": uid, "amount": amt, "product_id": pid,
                                        "type": "topup", "title": f"Cüzdan Bakiye Yükleme (₺{amt:.2f})"
                                    })

                                users[uid] = user_obj
                                _durable_save_users(users, users_data_path)

                                t_info["status"] = "completed"
                                topups[pid] = t_info
                                save_active_topups(topups)

                                # Satın alındı, ilanı Shopier'dan derhal sil
                                try:
                                    requests.delete(f"https://api.shopier.com/v1/products/{pid}", headers=headers, timeout=8)
                                    print(f"[LisansArena] Sipariş tamamlandı, ilan silindi: {pid}")
                                except Exception:
                                    pass
        except requests.exceptions.Timeout:
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
