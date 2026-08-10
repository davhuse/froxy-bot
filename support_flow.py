"""Single-owner customer support helpers.

Support bots own the customer DM flow.  The helper deliberately stores only a
one-time greeting claim and never message text or contact details in metrics.
"""

from __future__ import annotations

import asyncio
import os

import firestore_helper


def one_time_mode_enabled() -> bool:
    return os.environ.get("SUPPORT_ONE_TIME_GREETING", "1").strip().lower() not in {"0", "false", "no", "off"}


async def claim_first_greeting(brand: str, user_id: int) -> bool:
    """Return True for exactly one durable first greeting.

    If the durable store is unavailable, fail closed: forwarding still works,
    but no automatic reply is sent that could be duplicated after a restart.
    """
    if not one_time_mode_enabled():
        return False
    doc_id = f"support_greeting_{brand.lower()}_{int(user_id)}"
    loop = asyncio.get_running_loop()
    try:
        claimed = await loop.run_in_executor(
            None, firestore_helper.claim_document, doc_id,
            {"brand": brand, "created_at": __import__("time").time()},
        )
    except Exception:
        return False
    return claimed is True


async def forward_customer_message(bot, event, support_chat_id, brand: str, buttons=None) -> bool:
    """Forward every customer message to the support chat for a manual reply."""
    if not support_chat_id:
        return False
    try:
        user = await event.get_sender()
        username = f"@{user.username}" if getattr(user, "username", None) else "Yok"
        first_name = getattr(user, "first_name", "") or ""
        last_name = getattr(user, "last_name", "") or ""
        language = "TR"
        message = (
            f"📩 **[{brand}] Yeni Destek Talebi**\n"
            f"👤 **Kullanıcı ID:** `{event.sender_id}`\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\n"
            f"💬 **Kullanıcı Adı:** {username}\n"
            f"🌐 **Dil/Lang:** {language}\n"
            "--------------------------------------\n\n"
            f"{event.text}\n\n"
            "*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )
        await bot.send_message(support_chat_id, message, buttons=buttons)
        return True
    except Exception:
        return False


def greeting_for(brand: str) -> str:
    packages = (
        "• Öğrenci Paketi: Canva Pro + Duolingo Super\n"
        "• Eğlence Paketi: Netflix 4K + Spotify Premium\n"
        "• AI/Üretkenlik Paketi: Gemini Pro 18 Ay Davet + Canva Pro"
    )
    if brand.lower() == "froxy ai":
        return (
            "Merhaba, yardımcı olayım. Froxy AI kredi paketi veya teknik destek "
            "talebinizi yazın; ekibimiz size dönüş yapacak."
        )
    return (
        "Merhaba, yardımcı olayım. Paket fırsatlarımız:\n"
        f"{packages}\n\n"
        "İstediğiniz paket ya da ürünü yazın; ekibimiz size dönüş yapacak."
    )
