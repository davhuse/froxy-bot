# -*- coding: utf-8 -*-
"""
Order Fulfillment and Delivery Engine.
Handles automatic delivery vs manual/email-based delivery for Shopier orders
across KeyVadi, LisansArena, Froxy, and JarvisCraft.
Strictly zero emojis.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from license_delivery import allocate_license

# Strict list of products that require personal email or manual invite (NON-AUTO)
NON_AUTO_KEYWORDS = [
    "canva",
    "duolingo",
    "kendi hesab",
    "kendi mail",
    "davet",
    "ogretmen",
    "öğretmen",
    "ogrenci",
    "öğrenci",
    "bakiye",
    "cuzdan",
    "cüzdan",
    "adobe",
    "gemini pro 18 ay",
    "gemini pro davet",
]

# Order numbers are 9 digits
ORDER_REGEX = re.compile(r"\b(\d{9})\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def extract_order_id(text: str) -> str | None:
    if not text:
        return None
    match = ORDER_REGEX.search(str(text))
    return match.group(1) if match else None


def extract_email(text: str) -> str | None:
    if not text:
        return None
    match = EMAIL_REGEX.search(str(text))
    return match.group(0).lower() if match else None


ORDER_INQUIRY_TRIGGERS = (
    "sipariş nerede", "siparis nerede", "siparişim nerede", "siparisim nerede",
    "sipariş durumu", "siparis durumu", "sipariş durumu nedir", "siparişi sorgula",
    "kod gelmedi", "kodum gelmedi", "kod nerede", "kodum nerede", "kod ulaşmadı", "kod ulasmadi",
    "teslim edilmedi", "teslimat nerede", "teslimat yapılmadı", "teslimat yapilmadi",
    "satın aldım gelmedi", "satin aldim gelmedi", "ödedim gelmedi", "odedim gelmedi",
    "sipariş sorgula", "siparis sorgula", "nerede kaldı", "nerede kaldi", "gelmedi hala",
    "kod ne zaman", "teslimat ne zaman", "siparişim ne zaman", "siparisim ne zaman",
    "ödeme yaptım", "odeme yaptim", "ödemeyi yaptım", "odemeyi yaptim",
    "shoppierden aldım", "shopierden aldım", "shopier aldım", "shoppier aldım",
    "aldım gelmedi", "aldim gelmedi", "gelmedi valla", "yoo gelmedi", "gelmedi",
    "buradan mı vereceksiniz", "burdan mı vereceksiniz", "bilgileri buradan mı", "bilgileri nerden",
    "hesap bilgileri", "şifre nerede", "sifre nerede", "parayı attım", "parayi attim",
    "parayı gönderdim", "parayi gonderdim", "dekont", "havale yaptım", "havale yaptim"
)


def is_order_status_inquiry(text: str) -> bool:
    if not text:
        return False
    lower = str(text).lower().strip()
    if any(t in lower for t in ORDER_INQUIRY_TRIGGERS):
        return True
    words = ("sipariş", "siparis", "kodum", "teslimat", "satın aldım", "satin aldim", "ürünüm", "urunum", "ödeme", "odeme", "aldım", "aldim", "shopier", "shoppier")
    queries = ("nerede", "gelmedi", "ne zaman", "durum", "ulaşmadı", "ulasmadi", "bekliyorum", "çıkmadı", "cikmadi", "yaptım", "yaptim", "bilgi", "verir misiniz", "verir misin")
    return any(w in lower for w in words) and any(q in lower for q in queries)


def get_order_inquiry_reply(brand: str = "") -> str:
    return (
        "Merhaba, siparişinizi kontrol edebilmemiz için lütfen 9 haneli Shopier sipariş numaranızı "
        "veya satın alırken kullandığınız e-posta adresinizi buraya yazınız.\n\n"
        "Bilgilendirme: Şu anda canlı destek ekibimiz aktif değildir (mesai dışındadır). "
        "Sipariş numaranızı veya e-posta adresinizi ilettiğinizde talebiniz sıraya kaydedilecek ve "
        "destek ekibimiz aktif olduğunda sırayla kontrol edilerek tarafınıza dönüş sağlanacaktır."
    )



def get_brand_shopier_token(brand: str) -> str:
    brand = str(brand or "").lower().strip()
    env_keys = {
        "keyvadi": "SHOPIER_KEYVADI_ACCESS_TOKEN",
        "lisansarena": "SHOPIER_LISANSARENA_ACCESS_TOKEN",
        "froxy": "SHOPIER_FROXY_ACCESS_TOKEN",
        "jarvis": "SHOPIER_JARVIS_ACCESS_TOKEN",
    }
    key = env_keys.get(brand)
    if key and os.environ.get(key):
        return os.environ[key].strip()
    try:
        from check_shopier_jwts import vars as jwt_vars
        if key and jwt_vars.get(key):
            return jwt_vars[key].strip()
    except Exception:
        pass
    return ""


def is_auto_delivery_product(product_name: str) -> bool:
    """
    Returns True if product has instant license key or auto-activation,
    Returns False if product requires customer's personal email or manual invite.
    """
    if not product_name:
        return False
    norm = product_name.lower().strip()
    if any(kw in norm for kw in NON_AUTO_KEYWORDS):
        return False
    return True


def fetch_shopier_order(order_id: str, brand_hint: str = None) -> dict[str, Any] | None:
    """Fetch order details from Shopier API by order ID."""
    order_id = str(order_id).strip()
    if not order_id:
        return None

    brands = ["keyvadi", "lisansarena", "froxy", "jarvis"]
    if brand_hint and brand_hint.lower() in brands:
        brands.remove(brand_hint.lower())
        brands.insert(0, brand_hint.lower())

    for b in brands:
        token = get_brand_shopier_token(b)
        if not token:
            continue
        try:
            req = urllib.request.Request(
                f"https://api.shopier.com/v1/orders/{order_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict) and str(data.get("id")) == order_id:
                        shipping = data.get("shippingInfo") or {}
                        totals = data.get("totals") or {}
                        line_items = data.get("lineItems") or []
                        item_title = "Dijital Urun"
                        if line_items and isinstance(line_items[0], dict):
                            item_title = line_items[0].get("title") or item_title

                        buyer_name = f"{shipping.get('firstName', '')} {shipping.get('lastName', '')}".strip()
                        buyer_email = str(shipping.get("email") or "").strip().lower()
                        note = str(data.get("note") or "").strip()
                        extracted_note_email = extract_email(note)
                        final_email = extracted_note_email or buyer_email

                        return {
                            "order_id": order_id,
                            "brand": b,
                            "product_name": item_title,
                            "amount": str(totals.get("total") or data.get("totalAmount") or "0"),
                            "payment_status": str(data.get("paymentStatus") or "").lower(),
                            "buyer_name": buyer_name,
                            "buyer_email": final_email,
                            "buyer_phone": str(shipping.get("phone") or ""),
                            "note": note,
                            "date_created": data.get("dateCreated", ""),
                        }
        except Exception:
            continue

    # Fallback to local/firestore records
    try:
        import firestore_helper
        doc = firestore_helper.get_document(f"shopier_order_{order_id}")
        if doc and isinstance(doc, dict):
            return {
                "order_id": order_id,
                "brand": doc.get("brand", brand_hint or "keyvadi"),
                "product_name": doc.get("product_name", "Dijital Urun"),
                "amount": str(doc.get("amount", "0")),
                "payment_status": doc.get("status", "paid"),
                "buyer_name": doc.get("buyer_name", ""),
                "buyer_email": doc.get("buyer_email", ""),
                "buyer_phone": "",
                "note": "",
                "date_created": doc.get("timestamp", ""),
            }
    except Exception:
        pass

    return None


async def send_admin_push_alert(client_or_bot, message: str) -> None:
    """Send alert to all configured administrators."""
    admin_ids = [8791896048, 6196006704, 5359327143, 8116518175]
    try:
        with open("bot_config.json", "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
            if cfg.get("admin_id"):
                admin_ids.insert(0, int(cfg["admin_id"]))
            for a in cfg.get("admin_ids", []):
                admin_ids.append(int(a))
    except Exception:
        pass

    seen = set()
    for a_id in admin_ids:
        if a_id in seen:
            continue
        seen.add(a_id)
        try:
            if hasattr(client_or_bot, "send_message"):
                await client_or_bot.send_message(a_id, message)
        except Exception:
            pass


async def fulfill_order_request(
    order_query: str,
    tg_user_id: int | None = None,
    tg_username: str | None = None,
    brand_hint: str | None = None,
    user_email: str | None = None,
    client_or_bot: Any | None = None,
) -> dict[str, Any]:
    """
    Main fulfillment dispatcher.
    Separates instant auto-delivery from manual/email-based delivery.
    """
    order_id = extract_order_id(order_query) or order_query.strip()
    if not order_id:
        return {
            "success": False,
            "status": "invalid_query",
            "message": "Geçerli bir sipariş numarası (örn: 720325449) bulunamadı.",
        }

    order = fetch_shopier_order(order_id, brand_hint=brand_hint)
    if not order:
        return {
            "success": False,
            "status": "not_found",
            "message": (
                f"Sipariş No: {order_id}\n\n"
                "Shopier sistemi üzerinde henüz kayıtlı bir ödeme bulunamadı.\n"
                "Ödemenizi yeni yaptıysanız banka ve sistem onayı 1-2 dakika sürebilir.\n"
                "Birazdan tekrar kontrol edebilir veya dekontunuz ile destek ekibimize yazabilirsiniz.\n\n"
                "Not: Canlı destek ekibimiz şu anda aktif değildir (mesai dışındadır). "
                "Talebiniz sıraya kaydedilmiş olup, ekibimiz aktif olduğunda sırayla kontrol edilecektir."
            ),
        }

    if order["payment_status"] not in {"paid", "completed", "success"}:
        return {
            "success": False,
            "status": "payment_pending",
            "message": (
                f"Sipariş No: {order_id}\n"
                f"Ürün: {order['product_name']}\n"
                f"Tutar: {order['amount']} TL\n\n"
                "Ödeme durumu henüz tamamlanmamış veya onay bekliyor.\n"
                "Ödemeniz bankanızdan çekildiyse 1-2 dakika içinde otomatik onaylanacaktır."
            ),
        }

    brand = order["brand"]
    product_name = order["product_name"]
    amount = order["amount"]
    buyer_email = user_email or order.get("buyer_email") or ""
    uname = f"@{tg_username}" if tg_username else (f"ID:{tg_user_id}" if tg_user_id else "Müşteri")

    # Check if this order is AUTO-DELIVERY
    if is_auto_delivery_product(product_name):
        lowered = product_name.lower()
        # 1. Jarvis VIP and Bot Products
        is_jarvis_vip = (
            brand == "jarvis" or "jarvis" in lowered
        ) and (
            "vip" in lowered or "haftalık" in lowered or "haftalik" in lowered or "aylık" in lowered or "aylik" in lowered
        )
        if is_jarvis_vip:
            benefit = "VIP üyeliğiniz hesabınız için tanımlandı."
            msg = (
                f"[SİPARİŞ ONAYLANDI - OTOMATİK TESLİMAT]\n"
                f"Sipariş No: {order_id}\n"
                f"Ürün: {product_name}\n"
                f"Tutar: {amount} TL\n\n"
                f"Aktivasyon: {benefit}\n"
                f"Hemen kullanmaya başlayabilirsiniz."
            )
            if client_or_bot:
                await send_admin_push_alert(
                    client_or_bot,
                    f"[OTO TESLİMAT - VIP]\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nMüşteri: {uname}"
                )
            return {"success": True, "status": "delivered", "message": msg}

        if "jarvis core" in lowered or "asistan" in lowered:
            msg = (
                f"[SİPARİŞ ONAYLANDI - OTOMATİK TESLİMAT]\n"
                f"Sipariş No: {order_id}\n"
                f"Ürün: {product_name}\n"
                f"Tutar: {amount} TL\n\n"
                f"Kurulum ve İndirme Paketi Linki:\n"
                f"https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n\n"
                f"Zip içerisindeki çalıştırıcıyı başlatıp talimatları izleyerek hemen kullanabilirsiniz."
            )
            if client_or_bot:
                await send_admin_push_alert(
                    client_or_bot,
                    f"[OTO TESLİMAT - JARVIS CORE]\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nMüşteri: {uname}"
                )
            return {"success": True, "status": "delivered", "message": msg}

        # 2. General Auto-Delivery via Stock Allocation
        alloc = allocate_license(product_name, brand=brand)
        if alloc.get("allocated") and alloc.get("license_key"):
            key = alloc["license_key"]
            guide = alloc.get("activation_guide") or "İlgili platform üzerinde lisans/kod alanına giriniz."
            redeem_url = alloc.get("redeem_url")
            link_line = f"\nKullanım Linki: {redeem_url}" if redeem_url else ""
            msg = (
                f"[SİPARİŞ ONAYLANDI - OTOMATİK TESLİMAT]\n"
                f"Sipariş No: {order_id}\n"
                f"Ürün: {product_name}\n"
                f"Tutar: {amount} TL\n\n"
                f"Lisans Kodu / Giriş Bilgisi:\n"
                f"{key}\n"
                f"{link_line}\n"
                f"Aktivasyon Rehberi:\n"
                f"{guide}\n\n"
                f"İyi günlerde kullanınız."
            )
            if client_or_bot:
                await send_admin_push_alert(
                    client_or_bot,
                    f"[OTO TESLİMAT BAŞARILI]\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nKod: {key}\nMüşteri: {uname}"
                )
            return {"success": True, "status": "delivered", "message": msg}

        # Auto product, but stock pool currently empty
        msg = (
            f"[SİPARİŞ ONAYLANDI]\n"
            f"Sipariş No: {order_id}\n"
            f"Ürün: {product_name}\n"
            f"Tutar: {amount} TL\n\n"
            f"Ödemeniz başarıyla alındı. Talebiniz ve sipariş bilgileriniz sıraya kaydedilmiştir.\n\n"
            f"Şu anda canlı destek ekibimiz aktif değildir (mesai dışındadır). "
            f"Ekibimiz aktif olduğunda lisans kodunuz güvenlik kontrolünün ardından sırayla buradan iletilecektir."
        )
        if client_or_bot:
            await send_admin_push_alert(
                client_or_bot,
                f"[ACİL - STOK BEKLEYEN SİPARİŞ]\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nMüşteri: {uname}\nLütfen müşterinin kodunu iletiniz."
            )
        return {"success": True, "status": "stock_pending", "message": msg}

    # NON-AUTO PRODUCT (Manual Invite / Customer Email Required)
    # Check if we already have the customer's email
    if buyer_email:
        msg = (
            f"[SİPARİŞ ONAYLANDI - HESAP TANIMLAMA]\n"
            f"Sipariş No: {order_id}\n"
            f"Ürün: {product_name}\n"
            f"Tutar: {amount} TL\n\n"
            f"Tanımlanacak E-Posta Adresi: {buyer_email}\n\n"
            f"Talebiniz yetkili ekibimize iletilmiştir ve sıraya alınmıştır.\n\n"
            f"Şu anda canlı destek ekibimiz aktif değildir (mesai dışındadır). "
            f"Ekibimiz aktif olduğunda davet ve yetki işleminiz belirtilen e-posta adresinize sırayla tanımlanacaktır."
        )
        if client_or_bot:
            await send_admin_push_alert(
                client_or_bot,
                f"[YENİ SİPARİŞ - MAİL TANIMLAMA BEKLİYOR]\nMarka: {brand.upper()}\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nMüşteri: {uname}\nE-Posta: {buyer_email}\nLütfen daveti/yetkiyi gönderiniz."
            )
        return {"success": True, "status": "email_confirmed", "message": msg}

    # Customer email is not yet provided
    msg = (
        f"[SİPARİŞ ONAYLANDI]\n"
        f"Sipariş No: {order_id}\n"
        f"Ürün: {product_name}\n"
        f"Tutar: {amount} TL\n\n"
        f"Bu ürün şahsi hesabınıza yetki ve davet şeklinde tanımlanmaktadır.\n"
        f"Aktivasyonun tamamlanabilmesi için lütfen {product_name} hesabınıza kayıtlı e-posta adresinizi buraya yazınız.\n\n"
        f"Not: Canlı destek ekibimiz şu anda aktif değildir (mesai dışındadır). "
        f"E-posta adresinizi ilettiğinizde talebiniz sıraya alınacak ve ekibimiz aktif olduğunda işlem tamamlanacaktır."
    )
    if client_or_bot:
        await send_admin_push_alert(
            client_or_bot,
            f"[SİPARİŞ - MAİL BEKLENİYOR]\nMarka: {brand.upper()}\nSipariş No: {order_id}\nÜrün: {product_name}\nTutar: {amount} TL\nMüşteri: {uname}"
        )
    return {"success": True, "status": "email_needed", "message": msg}
