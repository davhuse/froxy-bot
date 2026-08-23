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
from telethon.errors import FloodWaitError


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


async def respond_with_floodwait(event, *args, **kwargs):
    """Deliver one claimed support reply after at most one Telegram FloodWait."""
    try:
        return await event.respond(*args, **kwargs)
    except FloodWaitError as exc:
        await asyncio.sleep(max(1, int(exc.seconds or 1)) + 1)
        return await event.respond(*args, **kwargs)


_GREETING_MEMORY_CLAIMS = set()

async def claim_first_greeting(brand: str, user_id: int) -> bool:
    """Return True for exactly one first greeting."""
    if not one_time_mode_enabled():
        return False
    doc_id = f"support_greeting_{brand.lower()}_{int(user_id)}"
    if doc_id in _GREETING_MEMORY_CLAIMS:
        return False
    _GREETING_MEMORY_CLAIMS.add(doc_id)
    if len(_GREETING_MEMORY_CLAIMS) > 10000:
        _GREETING_MEMORY_CLAIMS.clear()
        _GREETING_MEMORY_CLAIMS.add(doc_id)

    loop = asyncio.get_running_loop()
    try:
        claimed = await loop.run_in_executor(
            None, firestore_helper.claim_remote_document, doc_id,
            {"brand": brand, "created_at": __import__("time").time()},
        )
        if claimed is False:
            return False
    except Exception:
        pass
    return True


_MEMORY_CLAIMS = set()

async def claim_support_event(brand: str, user_id: int, event_id: int, kind: str) -> bool:
    """Claim one customer-facing reply for one incoming Telegram event."""
    safe_brand = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(brand).lower())
    safe_kind = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(kind).lower())
    doc_id = f"support_reply_{safe_brand}_{int(user_id)}_{int(event_id)}_{safe_kind}"
    
    if doc_id in _MEMORY_CLAIMS:
        return False
    _MEMORY_CLAIMS.add(doc_id)
    if len(_MEMORY_CLAIMS) > 10000:
        _MEMORY_CLAIMS.clear()
        _MEMORY_CLAIMS.add(doc_id)
        
    loop = asyncio.get_running_loop()
    try:
        claimed = await loop.run_in_executor(
            None,
            firestore_helper.claim_remote_document,
            doc_id,
            {
                "brand": brand,
                "user_id": int(user_id),
                "event_id": int(event_id),
                "kind": safe_kind,
                "created_at": __import__("time").time(),
            },
        )
        if claimed is False:
            return False
    except Exception:
        pass
    return True


def support_event_claim_id(brand: str, user_id: int, event_id: int, kind: str) -> str:
    safe_brand = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(brand).lower())
    safe_kind = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(kind).lower())
    return f"support_reply_{safe_brand}_{int(user_id)}_{int(event_id)}_{safe_kind}"


async def release_support_event(brand: str, user_id: int, event_id: int, kind: str) -> bool:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None,
            firestore_helper.delete_remote_document,
            support_event_claim_id(brand, user_id, event_id, kind),
        )
    except Exception:
        return False


async def release_product_claim(brand: str, user_id: int, product_id: str) -> bool:
    safe_brand = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(brand).lower())
    safe_id = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(product_id))[:100]
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None,
            firestore_helper.delete_remote_document,
            f"support_product_once_{safe_brand}_{int(user_id)}_{safe_id}",
        )
    except Exception:
        return False


_AUTO_REPLY_MEMORY_CLAIMS = set()

async def claim_auto_reply_once(brand: str, user_id: int, kind: str = "generic", chat_id=None) -> bool:
    """Claim one non-product reply for a support conversation across restarts."""
    safe_brand = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(brand).lower())
    safe_kind = "".join(char if char.isalnum() or char in "_-" else "_" for char in str(kind).lower())
    doc_id = f"support_auto_reply_once_{safe_brand}_{int(user_id)}_{safe_kind}"
    
    if doc_id in _AUTO_REPLY_MEMORY_CLAIMS:
        return False
    _AUTO_REPLY_MEMORY_CLAIMS.add(doc_id)
    if len(_AUTO_REPLY_MEMORY_CLAIMS) > 10000:
        _AUTO_REPLY_MEMORY_CLAIMS.clear()
        _AUTO_REPLY_MEMORY_CLAIMS.add(doc_id)
        
    loop = asyncio.get_running_loop()
    try:
        claimed = await loop.run_in_executor(
            None,
            firestore_helper.claim_remote_document,
            doc_id,
            {
                "brand": brand,
                "user_id": int(user_id),
                "chat_id": int(chat_id) if chat_id is not None else int(user_id),
                "kind": safe_kind,
                "created_at": __import__("time").time(),
            },
        )
        if claimed is False:
            return False
    except Exception:
        pass
    return True


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
    brand_lower = brand.lower()
    if brand_lower == "keyvadi":
        return (
            "👋 **KeyVadi Destek Hattına Hoş Geldiniz!**\n\n"
            "Steam Random Keyler, FC26, Xbox Game Pass, Minecraft Koleksiyon Pelerinleri, "
            "Netflix 4K ve dijital e-pinler hakkında sormak istediğiniz her şeyi yazabilirsiniz.\n\n"
            "Mesajınız ekibimize iletildi, en kısa sürede dönüş yapılacaktır."
        )
    if brand_lower in ("lisansarena", "lisans arena"):
        return (
            "👋 **LisansArena Müşteri Hizmetlerine Hoş Geldiniz!**\n\n"
            "Adobe CC, Canva Pro, Microsoft Office 365, Windows 10/11 Pro, CapCut Pro ve yapay "
            "zeka araçlarımız 7/24 otomatik teslimat ve değişim garantimiz altındadır.\n\n"
            "Talebiniz müşteri temsilcimize başarıyla aktarıldı, en kısa sürede size dönülecektir."
        )
    if brand_lower == "froxy ai":
        return (
            "👋 **Froxy AI Destek Merkezine Hoş Geldiniz!**\n\n"
            "Froxy AI paketleri, kredi yüklemeleri veya teknik destek talebinizi "
            "yazın; ekibimiz en kısa sürede size dönüş yapacaktır."
        )
    return (
        "👋 **Merhaba, Destek Hattımıza Hoş Geldiniz!**\n\n"
        "İstediğiniz paket ya da ürünü yazın; ekibimiz en kısa sürede size dönüş yapacaktır."
    )
