"""LisansArena Telegram storefront and support bot (Mini App First).

Shopier 3D Secure dynamic wallet top-ups, product purchases, order history,
referral tracking, and 7/24 automatic deliveries are seamlessly managed
via the LisansArena CyberVault Mini App.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import requests
from telethon import TelegramClient, events, Button
from telethon.errors import ButtonTypeInvalidError, FloodWaitError, MessageNotModifiedError
from telethon.sessions import StringSession
from telethon.tl.types import KeyboardButtonRow, KeyboardButtonWebView, ReplyInlineMarkup

from sales_metrics import conversation_key, record_dm_event, record_event
from customer_intent import INTENT_SALES_LEAD
import firestore_helper
from sales_conversion import load_sales_catalog, match_sales_products, purchase_url
from support_flow import (
    claim_first_greeting,
    claim_support_event,
    forward_customer_message,
    release_product_claim,
    release_support_event,
    respond_with_floodwait,
    save_ticket_record,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("LisansArenaBot")

BASE_DIR = Path(__file__).resolve().parent
MINIAPP_DIR = BASE_DIR / "miniapp_lisansarena"
LA_USER_DATA_PATH = MINIAPP_DIR / "users_data.json"
LA_PRODUCTS_DB_PATH = MINIAPP_DIR / "products_db.json"
DATA_LOCK = threading.RLock()

API_ID = int(os.environ.get("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "").strip()
def _load_config() -> dict[str, Any]:
    try:
        return json.loads(Path("bot_config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CONFIG = _load_config()
BOT_TOKEN = (
    os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
    or str(CONFIG.get("lisansarena_bot_token", "")).strip()
    or "8272543860:AAGESmDOiIXFoK7FYCh0UfP3IplBcvMhTEA"
)

# Canonical Mini App URL configuration
_configured_mini_app_url = os.environ.get("LISANSARENA_MINI_APP_URL", "").strip()
_canonical_mini_app_url = "https://froxy-bot-live.onrender.com/la/app/"
if _configured_mini_app_url:
    from urllib.parse import urlsplit, urlunsplit

    _parts = urlsplit(_configured_mini_app_url)
    _path = _parts.path.rstrip("/")
    _old_storefront = _path.endswith("/lisansarena") or _parts.netloc in {
        "froxy-bot-wjzr.onrender.com",
        "froxy-bot-qy0a.onrender.com",
    }
    if _old_storefront or _parts.netloc != "froxy-bot-live.onrender.com":
        _configured_mini_app_url = _canonical_mini_app_url
    elif _path == "/la/app":
        _configured_mini_app_url = urlunsplit((_parts.scheme, _parts.netloc, "/la/app/", "", ""))
MINI_APP_URL = (_configured_mini_app_url or _canonical_mini_app_url).rstrip("/") + "/"

ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", CONFIG.get("admin_id", 0)) or 0)
SUPPORT_CHAT_ID = int(CONFIG.get("support_chat_id") or ADMIN_ID or 0)
PENDING_INPUT: dict[int, str] = {}
USER_EVENT_LOCKS: dict[int, asyncio.Lock] = {}


# ==================== DATA HELPERS ====================

def load_la_users() -> dict[str, Any]:
    with DATA_LOCK:
        if LA_USER_DATA_PATH.exists():
            try:
                return json.loads(LA_USER_DATA_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def save_la_users(data: dict[str, Any]) -> None:
    with DATA_LOCK:
        LA_USER_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix="la_bot_users_", suffix=".json", dir=str(LA_USER_DATA_PATH.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, LA_USER_DATA_PATH)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass


def get_or_create_la_user(user_id: int, username: str = "", first_name: str = "", last_name: str = "") -> dict[str, Any]:
    users = load_la_users()
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
            "orders": [],
        }
        save_la_users(users)
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
            save_la_users(users)

    return users[uid]


def load_la_products() -> list[dict[str, Any]]:
    if LA_PRODUCTS_DB_PATH.exists():
        try:
            return json.loads(LA_PRODUCTS_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


# ==================== IDEMPOTENCY & LOCKS ====================

async def claim_command_event(event, command: str) -> bool:
    """Suppress a duplicate Telegram command update across all processes."""
    event_id = getattr(getattr(event, "message", None), "id", None)
    if event_id is None or event.sender_id is None:
        return False
    claimed = await claim_support_event(
        "LisansArena", event.sender_id, event_id, f"command_{command}"
    )
    if not claimed:
        record_event(
            "duplicate_suppressed", "LisansArena", source="telegram_private",
            reason=f"command_{command}_already_claimed",
        )
    return claimed


def once_per_command(command: str):
    """Decorate a command handler with durable per-update idempotency."""
    def decorator(handler):
        async def wrapped(event, *args, **kwargs):
            if not await claim_command_event(event, command):
                return
            try:
                return await handler(event, *args, **kwargs)
            except Exception:
                await release_support_event(
                    "LisansArena", event.sender_id,
                    getattr(getattr(event, "message", None), "id", 0),
                    f"command_{command}",
                )
                raise
        return wrapped
    return decorator


def serialize_user_events(handler):
    """Serialize one customer's updates so one Telegram event cannot race."""
    async def serialized(event, *args, **kwargs):
        user_id = getattr(event, "sender_id", None)
        if user_id is None:
            return await handler(event, *args, **kwargs)
        lock = USER_EVENT_LOCKS.setdefault(int(user_id), asyncio.Lock())
        async with lock:
            return await handler(event, *args, **kwargs)
    return serialized


_LA_MEMORY_CLAIMS = set()

async def claim_product_reply(user_id: int, product: dict[str, Any]) -> bool:
    """Keep one automatic product card per product and private chat."""
    product_id = str(product.get("id") or product.get("url") or product.get("title") or "product")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_id)[:100]
    doc_id = f"support_product_once_lisansarena_{int(user_id)}_{safe_id}"
    
    if doc_id in _LA_MEMORY_CLAIMS:
        return False
    _LA_MEMORY_CLAIMS.add(doc_id)
    if len(_LA_MEMORY_CLAIMS) > 10000:
        _LA_MEMORY_CLAIMS.clear()
        _LA_MEMORY_CLAIMS.add(doc_id)
        
    claimed = await asyncio.to_thread(
        firestore_helper.claim_remote_document,
        doc_id,
        {"brand": "lisansarena", "user_id": int(user_id), "product_id": product_id},
        True,
    )
    return claimed is True


async def send_product_card(event, matched_products: list[dict[str, Any]]) -> bool:
    event_id = getattr(event.message, "id", None)
    if event_id is None or not await claim_support_event("LisansArena", event.sender_id, event_id, "product_card"):
        record_event("duplicate_suppressed", "LisansArena", source="telegram_private", reason="product_event_already_claimed")
        return False
    claimed_products = []
    for product in matched_products[:3]:
        if await claim_product_reply(event.sender_id, product):
            claimed_products.append(product)
    if not claimed_products:
        return False
    for product in claimed_products:
        product["_cta_id"] = os.urandom(8).hex()
    lines = [
        "⚡ **LisansArena Ürün Seçenekleri**\n",
    ]
    buttons = []
    for product in claimed_products:
        price_txt = product.get("price") or "Fiyat için mağaza"
        lines.append(f"• **{product['title']}** — `{price_txt}`")
        pid = product.get("id", "")
        bot_app_url = f"https://t.me/LisansArenaOnline/app?startapp=p_{pid}"
        direct_url = purchase_url(product, "lisansarena", "support_bot_dm")
        buttons.append([
            Button.url("🛍️ Mağazada Aç", bot_app_url),
            Button.url("💳 Direkt Al", direct_url)
        ])
    buttons.append([Button.inline("💬 Canlı Destek", b"ticket_support")])
    lines.extend([
        "",
        "⚡ *7/24 Anında Otomatik Teslimat · Shopier 3D Secure Güvencesi*",
    ])
    try:
        await respond_with_floodwait(event, "\n".join(lines), buttons=buttons)
    except Exception:
        await release_support_event("LisansArena", event.sender_id, event_id, "product_card")
        for product in claimed_products:
            await release_product_claim(
                "lisansarena", event.sender_id,
                str(product.get("id") or product.get("url") or product.get("title") or "product"),
            )
        raise
    first = claimed_products[0]
    safe_conversation = conversation_key("LisansArena", event.sender_id)
    record_event("product_matched", "LisansArena", source="telegram_private", product=first.get("title", ""), product_count=len(claimed_products), conversation_key=safe_conversation)
    for product in claimed_products:
        record_event(
            "purchase_cta_sent", "LisansArena", source="telegram_private",
            product=product.get("title", ""), product_id=product.get("id", ""),
            cta_key=product.get("_cta_id", ""), conversation_key=safe_conversation,
        )
    record_event("dm_reply_sent", "LisansArena", source="telegram_private", product=first.get("title", ""))
    return True


if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("LisansArena Telegram credentials are not configured")

bot = TelegramClient(StringSession(), API_ID, API_HASH)


BOT_COMMANDS = [
    ("start", "LisansArena ana menüsünü aç"),
    ("magaza", "LisansArena mağazasını aç"),
    ("urunler", "Ürün kataloğunu görüntüle"),
    ("bakiye", "Bakiye yükle ve sorgula"),
    ("siparisler", "Siparişlerini görüntüle"),
    ("hesaplar", "Hesap ve profil bilgilerin"),
    ("gecmis", "Bakiye hareketlerin"),
    ("kullanim", "Teslimat ve kullanım bilgileri"),
    ("talep", "Yeni ürün talebi oluştur"),
    ("destek", "Destek talebi oluştur"),
    ("iade", "İade talebi oluştur"),
    ("referans", "Referans profilini ve davet linkini görüntüle"),
    ("cekilis", "Aktif çekilişleri görüntüle"),
    ("ayarlar", "Hesap ayarları"),
    ("dil", "Dil seçimini değiştir"),
    ("yardim", "Komutları ve yardımı görüntüle"),
]


def mini_app_markup(label="Mağazayı Aç"):
    return ReplyInlineMarkup(rows=[KeyboardButtonRow(buttons=[
        KeyboardButtonWebView(text=f"🛍️ {label}", url=MINI_APP_URL)
    ])])


def inline_menu():
    return [
        [Button.inline("🛍️ Ürünler", b"menu_products"), Button.inline("💳 Bakiye", b"menu_balance")],
        [Button.inline("📦 Siparişler", b"menu_orders"), Button.inline("👤 Profil & Referans", b"menu_profile")],
        [Button.inline("💬 Destek Talebi", b"ticket_support"), Button.inline("➕ Ürün Talebi", b"ticket_request")],
    ]


async def safe_edit(event, text, **kwargs):
    try:
        return await event.edit(text, **kwargs)
    except MessageNotModifiedError:
        return None


# ==================== MAIN MENUS & SCREENS ====================

async def show_main_menu(event, *, edit=False):
    welcome = (
        "🛡️ **LİSANSARENA — Kurumsal & Bireysel Dijital Lisans Arenası** 🏆\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **LisansArena Resmi İşlem Paneline Hoş Geldiniz!**\n\n"
        "Adobe Creative Cloud, Canva Pro, Microsoft Office 365, Windows 10/11 Pro, CapCut Pro, Envato Elements, Freepik, Netflix 4K ve yapay zeka araçları orijinal lisans güvencesiyle tek platformda!\n\n"
        "🌟 **LisansArena Güvenceleri:**\n"
        "• 🛡️ Tüm Lisans ve Hesaplarda Süresi Boyunca Değişim & Telafi Garantisi\n"
        "• ⚡ 7/24 Anında Otomatik Lisans Anahtarı Teslimatı\n"
        "• 🔒 Shopier 3D Secure / Kredi Kartı / Cüzdan ile Güvenli Ödeme\n\n"
        "👇 **Lisansları incelemek ve sipariş vermek için mağazayı açın:**"
    )
    buttons = mini_app_markup("Mağazayı Aç (Mini App)")
    if edit:
        await safe_edit(event, welcome, buttons=buttons)
    else:
        try:
            await event.respond(welcome, buttons=buttons)
        except ButtonTypeInvalidError:
            await event.respond(
                f"{welcome}\n\nMağazayı sohbet ekranının altındaki Menü düğmesinden açabilirsiniz."
            )


async def show_products(event, *, edit=False):
    text = (
        "🛍️ **LİSANSARENA ÜRÜN VE LİSANS KATALOĞU**\n\n"
        "Tüm profesyonel tasarım yazılımları, kurumsal Office lisansları ve yapay zeka abonelikleri:\n\n"
        "🌟 **Öne Çıkan Kategoriler:**\n"
        "• 🎨 **Tasarım & Edit:** CapCut Pro, Adobe Creative Cloud, Canva Pro, Envato, Freepik\n"
        "• 🔑 **Orijinal Lisans:** Windows 10/11 Pro, Office 365 Pro Plus, Antivirüs\n"
        "• 🎬 **Yayın & Eğlence:** Netflix 4K, Spotify Premium, YouTube Premium, Exxen, Prime Video\n"
        "• 🤖 **Yapay Zeka:** ChatGPT Plus, Gemini Pro, Perplexity Pro\n"
        "• 🎮 **Oyun & E-Pin:** Minecraft Capeleri, Steam Random Key\n\n"
        "⚡ **7/24 Anında Otomatik Teslimat · Shopier 3D Secure Güvencesi**\n\n"
        "👇 Kataloğu incelemek ve sepete eklemek için mağazayı açın:"
    )
    buttons = mini_app_markup("🛍️ Ürünleri İncele")
    if edit:
        await safe_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)


async def show_balance(event, *, edit=False):
    user_id = event.sender_id
    user = get_or_create_la_user(user_id)
    bal = user.get("balance", 0.0)
    text = (
        "💳 **LİSANSARENA CÜZDAN & BAKİYE**\n\n"
        f"💰 **Mevcut Bakiyeniz:** `₺{bal:.2f}`\n\n"
        "Shopier 3D Secure altyapısıyla komisyonsuz, güvenli ve 7/24 anında bakiye yükleyebilirsiniz.\n\n"
        "⚡ **Özellikler:**\n"
        "• Kredi Kartı / Banka Kartı ile Anında 3D Secure Ödeme\n"
        "• 0 Komisyon & Anında Bakiyeye Yansıma\n"
        "• Özel Tutar veya Hazır Paket Seçenekleri\n\n"
        "👇 Bakiye yüklemek için mağazayı açın:"
    )
    buttons = mini_app_markup("Bakiye Yükle")
    if edit:
        await safe_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)


async def show_orders(event, *, edit=False):
    user_id = event.sender_id
    user = get_or_create_la_user(user_id)
    orders = user.get("orders", [])
    lines = ["📦 **LİSANSARENA SİPARİŞLERİM**", ""]
    if not orders:
        lines.append("Henüz bir siparişiniz bulunmuyor.")
    else:
        lines.append(f"Toplam {len(orders)} adet siparişiniz kayıtlı:")
        for o in orders[-5:]:
            title = o.get("title", "Ürün")
            price = o.get("price") or o.get("subtotal") or 0.0
            status = "✅ Teslim Edildi" if o.get("status") == "delivered" else "⏳ Teslimat Bekleniyor"
            lines.append(f"• **{title}** — `₺{price:.2f}` ({status})")
    lines.extend(["", "Sipariş detaylarınızı, teslimat kodlarınızı ve hesap bilgilerinizi mağazadan 7/24 görüntüleyebilirsiniz."])
    text = "\n".join(lines)
    buttons = mini_app_markup("Siparişleri Aç")
    if edit:
        await safe_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)


async def show_profile(event, *, edit=False):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, "username", "") or ""
    first_name = getattr(sender, "first_name", "") or ""
    last_name = getattr(sender, "last_name", "") or ""
    user = get_or_create_la_user(user_id, username, first_name, last_name)

    bal = user.get("balance", 0.0)
    ref_count = user.get("referrals_count", 0)
    ref_earnings = user.get("referral_earnings", 0.0)

    try:
        me = await bot.get_me()
        bot_uname = me.username or "LisansArenaBot"
    except Exception:
        bot_uname = "LisansArenaBot"

    ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"

    text = (
        "👤 **LİSANSARENA KULLANICI PROFİLİ**\n\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"👤 **Kullanıcı:** @{username or user_id}\n"
        f"💰 **Bakiye:** `₺{bal:.2f}`\n\n"
        "👥 **Davet & Kazan (%10 Nakit):**\n"
        f"• Davet Ettiğiniz Kişi Sayısı: `{ref_count}`\n"
        f"• Toplam Referans Kazancınız: `₺{ref_earnings:.2f}`\n\n"
        "🔗 **Sizin Özel Referans Linkiniz:**\n"
        f"`{ref_link}`\n\n"
        "*(Linke dokunarak kopyalayabilir, arkadaşlarınıza göndererek her alışverişlerinden %10 anında nakit kazanabilirsiniz!)*"
    )
    buttons = mini_app_markup("Mağazayı Aç")
    if edit:
        await safe_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)


async def begin_ticket(event, ticket_type: str):
    labels = {
        "support": "yaşadığınız sorunu veya sormak istediğiniz konuyu",
        "request": "aradığınız veya eklenmesini istediğiniz ürünü",
        "refund": "sipariş numaranızı ve iade nedeninizi",
    }
    PENDING_INPUT[event.sender_id] = ticket_type
    await event.respond(
        f"💬 Lütfen {labels.get(ticket_type, 'mesajınızı')} bu sohbete tek mesaj olarak ayrıntılı yazın.\n\n"
        "Mesajınız doğrudan canlı destek ekibimize iletilecektir.\n"
        "*(Vazgeçmek için /start yazabilirsiniz)*"
    )


async def save_ticket_from_message(event, ticket_type: str):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = f"@{sender.username}" if getattr(sender, "username", None) else "yok"

    record_event("human_handoff", "LisansArena", source="telegram_private")
    if SUPPORT_CHAT_ID:
        await bot.send_message(
            SUPPORT_CHAT_ID,
            f"📩 [LisansArena] {ticket_type.upper()}\n"
            f"Kullanıcı ID: {user_id}\nKullanıcı: {username}\n\n{event.raw_text}",
            parse_mode=None,
        )
    await event.respond(
        "✅ Mesajınız LisansArena destek ekibimize iletildi. En kısa sürede yanıt alacaksınız.",
        buttons=mini_app_markup("Mağazayı Aç"),
    )


def _bot_api(method: str, *, payload: dict | None = None, files: dict | None = None) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        json=payload if files is None else None,
        data=payload if files is not None else None,
        files=files,
        timeout=25,
    )
    data = response.json() if response.content else {}
    if response.status_code >= 400 or not data.get("ok"):
        raise RuntimeError(data.get("description") or f"HTTP {response.status_code}")
    return data


def configure_bot_profile():
    """Configure commands, descriptions, menu button and square logo."""
    calls = (
        ("setMyCommands", {"commands": [{"command": command, "description": description} for command, description in BOT_COMMANDS]}),
        ("setChatMenuButton", {"menu_button": {"type": "web_app", "text": "🛍️ Mağazayı Aç", "web_app": {"url": MINI_APP_URL}}}),
        ("setMyName", {"name": "LisansArena"}),
        ("setMyDescription", {"description": "Dijital ürünler, bakiye, otomatik teslimat ile sipariş takibi için LisansArena mağazası."}),
        ("setMyShortDescription", {"short_description": "Dijital ürün mağazası · Stok · Bakiye · Sipariş"}),
    )
    for method, payload in calls:
        try:
            _bot_api(method, payload=payload)
        except Exception as exc:
            logger.warning("Bot API %s error: %s", method, exc)

    logo = Path("static/lisansarena_logo_v2.jpg")
    if logo.exists():
        try:
            with logo.open("rb") as handle:
                _bot_api(
                    "setMyProfilePhoto",
                    payload={
                        "photo": json.dumps({
                            "type": "static",
                            "photo": "attach://profile_photo",
                        })
                    },
                    files={
                        "profile_photo": (logo.name, handle, "image/jpeg")
                    },
                )
        except Exception as exc:
            logger.warning("Profile photo configuration skipped: %s", exc)


# ==================== BOT HANDLERS ====================

@bot.on(events.NewMessage(pattern=r"(?i)^/start(?:\s+(.+))?$"))
@once_per_command("start")
async def start_handler(event):
    PENDING_INPUT.pop(event.sender_id, None)
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, "username", "") or ""
    first_name = getattr(sender, "first_name", "") or ""
    last_name = getattr(sender, "last_name", "") or ""

    user = get_or_create_la_user(user_id, username, first_name, last_name)

    start_param = (event.pattern_match.group(1) or "").strip()
    if start_param.startswith("ref_"):
        ref_id_str = start_param[4:].strip()
        if ref_id_str.isdigit() and int(ref_id_str) != user_id:
            ref_id = int(ref_id_str)
            if not user.get("referred_by"):
                users = load_la_users()
                uid = str(user_id)
                if uid in users:
                    users[uid]["referred_by"] = str(ref_id)
                    ref_uid = str(ref_id)
                    if ref_uid in users:
                        users[ref_uid]["referrals_count"] = users[ref_uid].get("referrals_count", 0) + 1
                    save_la_users(users)
                try:
                    await bot.send_message(
                        ref_id,
                        "🎉 **Tebrikler!** Bir arkadaşınız davetinizle LisansArena'ya katıldı. Her siparişinden %10 nakit bakiye kazanacaksınız!",
                    )
                except Exception:
                    pass

    await show_main_menu(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/magaza$"))
@once_per_command("magaza")
async def store_handler(event):
    await event.respond(
        "⚡ **LisansArena Mini App Mağazası**\n\nTüm ürünleri, güncel stokları ve anında teslimatı görüntülemek için mağazayı açabilirsiniz.",
        buttons=mini_app_markup("Mağazayı Aç"),
    )


@bot.on(events.NewMessage(pattern=r"(?i)^/urunler$"))
@once_per_command("urunler")
async def products_handler(event):
    await show_products(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/bakiye$"))
@once_per_command("bakiye")
async def balance_handler(event):
    await show_balance(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/(siparisler|orders)$"))
@once_per_command("siparisler")
async def orders_handler(event):
    await show_orders(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/hesaplar$"))
@once_per_command("hesaplar")
async def accounts_handler(event):
    await show_profile(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/gecmis$"))
@once_per_command("gecmis")
async def history_handler(event):
    user_id = event.sender_id
    user = get_or_create_la_user(user_id)
    bal = user.get("balance", 0.0)
    lines = [f"💳 **BAKİYE GEÇMİŞİ · Mevcut: ₺{bal:.2f}**", ""]
    orders = user.get("orders", [])
    if not orders:
        lines.append("Henüz bakiye hareketi veya sipariş bulunmuyor.")
    else:
        for o in orders[-6:]:
            title = o.get("title", "İşlem")
            price = o.get("price") or o.get("subtotal") or 0.0
            lines.append(f"• {title} — `₺{price:.2f}`")
    lines.extend(["", "Detaylı bakiye yüklemeleri ve cüzdan geçmişi mağaza Cüzdan sekmesinde."])
    await event.respond("\n".join(lines), buttons=mini_app_markup("Cüzdanı Aç"))


@bot.on(events.NewMessage(pattern=r"(?i)^/kullanim$"))
@once_per_command("kullanim")
async def guides_handler(event):
    user_id = event.sender_id
    user = get_or_create_la_user(user_id)
    orders = [o for o in user.get("orders", []) if o.get("status") == "delivered"]
    if not orders:
        await event.respond(
            "📖 **Teslimat & Kullanım Bilgileri**\n\nSatın aldığınız ürünlerin aktivasyon rehberi ve lisans kodları mağaza içi **Siparişlerim** ekranında gösterilir.",
            buttons=mini_app_markup("Mağazayı Aç"),
        )
        return
    blocks = ["📖 **TESLİMAT VE KULLANIM REHBERİ**"]
    for row in orders[-3:]:
        blocks.append(f"\n• **{row.get('title', 'Ürün')}**")
        blocks.append("Rehber: Lisans anahtarınız ve kullanım talimatınız mağaza içi Siparişlerim sekmesindedir.")
    await event.respond("\n".join(blocks), buttons=mini_app_markup("Siparişleri Aç"))


@bot.on(events.NewMessage(pattern=r"(?i)^/talep$"))
@once_per_command("talep")
async def request_handler(event):
    await begin_ticket(event, "request")


@bot.on(events.NewMessage(pattern=r"(?i)^/destek$"))
@once_per_command("destek")
async def support_handler(event):
    await begin_ticket(event, "support")


@bot.on(events.NewMessage(pattern=r"(?i)^/iade$"))
@once_per_command("iade")
async def refund_handler(event):
    await begin_ticket(event, "refund")


@bot.on(events.NewMessage(pattern=r"(?i)^/referans$"))
@once_per_command("referans")
async def referral_handler(event):
    await show_profile(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/cekilis$"))
@once_per_command("cekilis")
async def draws_handler(event):
    await event.respond(
        "🎁 **LİSANSARENA ÇEKİLİŞLERİ**\n\nAktif çekilişler, hediye lisanslar ve kupon etkinlikleri için mağazamızı takip edebilirsiniz.",
        buttons=mini_app_markup("Çekilişleri Aç"),
    )


@bot.on(events.NewMessage(pattern=r"(?i)^/(ayarlar|dil)$"))
@once_per_command("ayarlar_dil")
async def settings_handler(event):
    await event.respond(
        "🌐 **Dil Seçimi / Language Selection**\n\nLütfen tercih ettiğiniz dili seçin:",
        buttons=[[Button.inline("🇹🇷 Türkçe", b"lang_tr"), Button.inline("🇬🇧 English", b"lang_en")]],
    )


@bot.on(events.NewMessage(pattern=r"(?i)^/yardim$"))
@once_per_command("yardim")
async def help_handler(event):
    text = "⚡ **LİSANSARENA BOT KOMUTLARI**\n\n" + "\n".join(f"/{command} — {description}" for command, description in BOT_COMMANDS)
    await event.respond(text, buttons=mini_app_markup("Mağazayı Aç"))


# ==================== CALLBACKS ====================

@bot.on(events.CallbackQuery(pattern=rb"^menu_(products|balance|orders|profile)$"))
async def menu_callback(event):
    await event.answer()
    name = event.pattern_match.group(1).decode()
    if name == "products":
        await show_products(event, edit=True)
    elif name == "balance":
        await show_balance(event, edit=True)
    elif name == "orders":
        await show_orders(event, edit=True)
    else:
        await show_profile(event, edit=True)


@bot.on(events.CallbackQuery(pattern=rb"^ticket_(support|request|refund)$"))
async def ticket_callback(event):
    await event.answer()
    await begin_ticket(event, event.pattern_match.group(1).decode())


@bot.on(events.CallbackQuery(pattern=rb"^lang_(tr|en)$"))
async def language_callback(event):
    await event.answer()
    language = event.pattern_match.group(1).decode()
    msg = "Dil tercihiniz Türkçe olarak ayarlandı." if language == "tr" else "Language preference saved as English."
    await safe_edit(event, msg, buttons=mini_app_markup("Mağazayı Aç"))


@bot.on(events.NewMessage(pattern=r"(?i)^/toplumesaj(?:\s+(.+))?$"))
async def broadcast_handler(event):
    if event.sender_id != ADMIN_ID:
        return
    message_text = (event.pattern_match.group(1) or "").strip()
    if not message_text:
        await event.respond("⚠️ Kullanım: `/toplumesaj Duyuru mesajınız buraya...`")
        return
        
    await event.respond("⏳ **Toplu mesaj gönderimi başlatılıyor.**\n\nKullanıcı sayısına göre bu işlem vakit alabilir. İşlem bitene kadar lütfen yeni bir toplu mesaj başlatmayın.")
    
    users = load_la_users()
    user_ids = list(users.keys())
    
    success_count = 0
    fail_count = 0
    
    for uid in user_ids:
        try:
            await bot.send_message(int(uid), message_text, parse_mode='md')
            success_count += 1
        except Exception:
            fail_count += 1
        await asyncio.sleep(0.5)
        
    await event.respond(f"✅ **Toplu Mesaj Tamamlandı!**\n\nBaşarıyla Gönderilen: {success_count}\nBaşarısız (Botu silen/engelleyenler): {fail_count}")

# ==================== INCOMING MESSAGES & PRODUCT MATCHING ====================

@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def private_message_handler(event):
    if getattr(event, "out", False) or not event.is_private or (event.raw_text or "").startswith("/"):
        return

    # Admin reply forwarding
    if event.sender_id == ADMIN_ID and event.is_reply:
        original = await event.get_reply_message()
        match = re.search(r"Kullanıcı ID:\s*(\d+)", original.raw_text or "") if original else None
        if match:
            target_uid = int(match.group(1))
            await bot.send_message(
                target_uid,
                f"📨 **LisansArena Canlı Destek Yanıtı:**\n\n{event.raw_text}",
                parse_mode=None,
            )
            await event.respond("✅ Yanıt kullanıcıya iletildi.")
        return

    sender = await event.get_sender()
    sender_id = event.sender_id
    uname = getattr(sender, 'username', '') or ''
    fname = getattr(sender, 'first_name', '') or ''
    lname = getattr(sender, 'last_name', '') or ''
    msg_text = event.raw_text or ''

    logger.info(f"📥 [LisansArena] DM Alındı: GÖNDEREN={sender_id} (@{uname}) MESAJ='{msg_text}'")
    print(f"📥 [LisansArena] DM Alındı: GÖNDEREN={sender_id} (@{uname}) MESAJ='{msg_text}'", flush=True)

    try:
        save_ticket_record(
            "LisansArena",
            sender_id,
            fname,
            lname,
            f"@{uname}" if uname else "Yok",
            msg_text,
        )
    except Exception as exc:
        logger.warning("Ticket kaydı oluşturulamadı: %s", exc)

    incoming_event_id = getattr(event.message, "id", None)
    dm_intent = record_dm_event(
        "LisansArena", event.sender_id, event.raw_text or "",
        message_id=incoming_event_id,
    )

    # Product matching on sales questions
    if event.raw_text and dm_intent == INTENT_SALES_LEAD:
        matched_products = match_sales_products(
            event.raw_text, load_sales_catalog("lisansarena"), limit=3
        )
        if matched_products:
            await send_product_card(event, matched_products)
            return

    # Process pending ticket input if any
    pending = PENDING_INPUT.pop(event.sender_id, None)
    if pending:
        await save_ticket_from_message(event, pending)
        return

    # Forward customer question to Support Chat / Admin
    forwarded = await forward_customer_message(
        bot, event, SUPPORT_CHAT_ID, "LisansArena"
    )
    if forwarded:
        record_event(
            "human_handoff", "LisansArena", source="telegram_private",
            reason=dm_intent,
        )

    if await claim_first_greeting("lisansarena", event.sender_id):
        await event.respond(
            "👋 **LisansArena Müşteri Hizmetlerine Hoş Geldiniz!**\n\n"
            "Talebiniz canlı destek ekibimize iletildi, en kısa sürede buradan yanıt alacaksınız.\n\n"
            "Orijinal lisansları incelemek, bakiye yüklemek ve 7/24 anında teslimatla sipariş vermek için aşağıdaki butondan mağazamızı açabilirsiniz.",
            buttons=mini_app_markup("🛍️ LisansArena Mağazasını Aç"),
        )


# ==================== MAIN LOOP ====================

async def main():
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            if os.environ.get("LISANSARENA_CONFIGURE_PROFILE", "0").strip().lower() in {"1", "true", "yes"}:
                try:
                    await asyncio.to_thread(configure_bot_profile)
                    logger.info("Commands, profile and Mini App menu configured")
                except Exception as exc:
                    logger.warning("Bot profile configuration warning: %s", exc)
            else:
                logger.info("Bot profile configuration skipped; canonical Mini App URL is %s", MINI_APP_URL)
            me = await bot.get_me()
            logger.info("LisansArena bot running as @%s", me.username)
            await bot.run_until_disconnected()
        except FloodWaitError as exc:
            await asyncio.sleep(exc.seconds + 5)
        except Exception as exc:
            logger.error("Bot runtime error: %s", exc)
            await asyncio.sleep(30)


if __name__ == "__main__":
    bot.loop.run_until_complete(main())
