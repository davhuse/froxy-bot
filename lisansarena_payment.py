"""Pure helpers for LisansArena's manual IBAN payment flow."""

from __future__ import annotations

import secrets
import time


IBAN_DISPLAY = "TR57 0082 9000 0949 1531 1092 06"
IBAN_COMPACT = IBAN_DISPLAY.replace(" ", "")
IBAN_RECIPIENT = "Mahmut Rençber"
PAYMENT_REPLY_COOLDOWN_SECONDS = 10 * 60
PAYMENT_SESSION_TTL_SECONDS = 60 * 60


class PaymentSessionStore:
    """Keeps short, non-identifying order codes for pending manual payments."""

    def __init__(self):
        self._sessions = {}

    def get_or_create(self, user_id, product_id, *, now=None):
        now = time.monotonic() if now is None else float(now)
        key = (int(user_id), str(product_id))
        current = self._sessions.get(key)
        if current and current["expires_at"] > now:
            return dict(current)
        session = {
            "code": f"LA-{secrets.token_hex(3).upper()}",
            "created_at": now,
            "expires_at": now + PAYMENT_SESSION_TTL_SECONDS,
        }
        self._sessions[key] = session
        return dict(session)

    def get(self, user_id, product_id, *, now=None):
        now = time.monotonic() if now is None else float(now)
        current = self._sessions.get((int(user_id), str(product_id)))
        if not current or current["expires_at"] <= now:
            return None
        return dict(current)


def build_payment_message(product, order_code, *, language="tr"):
    """Build a Shopier-free payment message tied to one selected product."""
    title = str(product.get("title") or "Seçilen Ürün")
    price = str(product.get("price") or "Fiyat için destek ekibine yazın")
    if language == "en":
        return (
            "💳 **LisansArena Bank Transfer Details**\n\n"
            f"📦 **Product:** {title}\n"
            f"💰 **Price:** `{price}`\n"
            "📦 **Stock:** Please wait for staff confirmation before payment.\n\n"
            f"🏦 **IBAN:** `{IBAN_DISPLAY}`\n"
            f"👤 **Recipient:** `{IBAN_RECIPIENT}`\n"
            f"🧾 **Order code:** `{order_code}`\n\n"
            "Write only the order code in the transfer description. After paying, "
            "use the receipt button and send the receipt image. Delivery is manual "
            "after the bank transaction is verified."
        )
    return (
        "💳 **LisansArena IBAN Ödeme Bilgileri**\n\n"
        f"📦 **Ürün:** {title}\n"
        f"💰 **Fiyat:** `{price}`\n"
        "📦 **Stok:** Ödeme yapmadan önce yetkili stok teyidini bekleyin.\n\n"
        f"🏦 **IBAN:** `{IBAN_DISPLAY}`\n"
        f"👤 **Alıcı:** `{IBAN_RECIPIENT}`\n"
        f"🧾 **Sipariş kodu:** `{order_code}`\n\n"
        "Havale/EFT açıklamasına yalnızca sipariş kodunu yazın. Ödemeden sonra "
        "dekont gönderme butonunu kullanarak dekont görselini iletin. Teslimat, "
        "banka hareketi manuel doğrulandıktan sonra yapılır."
    )

