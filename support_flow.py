"""Single-owner customer support helpers.

Support bots own the customer DM flow.  The helper deliberately stores only a
one-time greeting claim and never message text or contact details in metrics.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import tempfile
from contextlib import contextmanager

import firestore_helper


TICKETS_FILE = "tickets.json"
TICKETS_LOCK_FILE = "tickets.json.lock"


@contextmanager
def _ticket_file_lock():
    """Serialize ticket updates across the separate support-bot processes."""
    lock_handle = open(TICKETS_LOCK_FILE, "a+b")
    try:
        lock_handle.seek(0, os.SEEK_END)
        if lock_handle.tell() == 0:
            lock_handle.write(b"0")
            lock_handle.flush()
        lock_handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            lock_handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()


def save_ticket_record(
    brand: str,
    user_id: int,
    first_name: str,
    last_name: str,
    username: str,
    message: str,
) -> None:
    """Persist a customer DM atomically for the web panel."""
    ticket = {
        "bot_type": brand,
        "user_id": user_id,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "username": username or "Yok",
        "message": message or "",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with _ticket_file_lock():
        tickets = []
        if os.path.exists(TICKETS_FILE):
            try:
                with open(TICKETS_FILE, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, list):
                        tickets = loaded
            except (OSError, ValueError, TypeError):
                tickets = []
        tickets.insert(0, ticket)
        tickets = tickets[:200]
        target_dir = os.path.dirname(os.path.abspath(TICKETS_FILE))
        fd, temp_path = tempfile.mkstemp(prefix="tickets-", suffix=".json.tmp", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(tickets, handle, indent=2, ensure_ascii=False)
            os.replace(temp_path, TICKETS_FILE)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def save_incoming_ticket(brand: str, event, user) -> None:
    """Persist every incoming customer DM for the web panel."""
    save_ticket_record(
        brand,
        event.sender_id,
        getattr(user, "first_name", "") or "",
        getattr(user, "last_name", "") or "",
        f"@{user.username}" if getattr(user, "username", None) else "Yok",
        event.text or "",
    )


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
    try:
        user = await event.get_sender()
        save_incoming_ticket(brand, event, user)
        if not support_chat_id:
            return False
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
