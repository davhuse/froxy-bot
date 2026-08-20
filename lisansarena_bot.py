"""LisansArena Telegram storefront and support bot.

Shopier is used only for Mini App wallet top-ups. Product purchase, order
history, requests, refunds and support are handled by the PostgreSQL-backed
LisansArena store.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

import requests
from telethon import TelegramClient, events, Button
from telethon.errors import ButtonTypeInvalidError, FloodWaitError, MessageNotModifiedError
from telethon.sessions import StringSession
from telethon.tl.types import KeyboardButtonRow, KeyboardButtonWebView, ReplyInlineMarkup

from lisansarena_store import StoreUnavailable, get_store
from sales_metrics import conversation_key, record_dm_event, record_event
from customer_intent import INTENT_SALES_LEAD
import firestore_helper
from sales_conversion import load_sales_catalog, match_sales_products, purchase_url
from support_flow import claim_first_greeting, claim_support_event, forward_customer_message, release_product_claim, release_support_event, respond_with_floodwait


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("LisansArenaBot")

API_ID = int(os.environ.get("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "").strip()
BOT_TOKEN = os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
# The old JSON storefront and the PostgreSQL storefront used to live at
# different Render paths.  Keep the bot on the canonical PostgreSQL route even
# if an old deployment left LISANSARENA_MINI_APP_URL behind in the environment.
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


def _load_config():
    try:
        return json.loads(Path("bot_config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CONFIG = _load_config()
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", CONFIG.get("admin_id", 0)) or 0)
SUPPORT_CHAT_ID = int(CONFIG.get("support_chat_id") or ADMIN_ID or 0)
PENDING_INPUT = {}
USER_EVENT_LOCKS = {}


async def claim_command_event(event, command):
    """Suppress a duplicate Telegram command update across all processes.

    Telegram may redeliver an update while a bot reconnects, and an old
    deployment can briefly overlap a new one.  The durable claim is keyed by
    the Telegram message id, so only one process is allowed to answer it.
    """
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


def once_per_command(command):
    """Decorate a command handler with durable per-update idempotency."""
    def decorator(handler):
        async def wrapped(event, *args, **kwargs):
            if not await claim_command_event(event, command):
                return
            try:
                return await handler(event, *args, **kwargs)
            except Exception:
                # A failed handler must be retryable after the transient error.
                await release_support_event(
                    "LisansArena", event.sender_id,
                    getattr(getattr(event, "message", None), "id", 0),
                    f"command_{command}",
                )
                raise
        return wrapped
    return decorator


def serialize_user_events(handler):
    """Serialize one customer's updates so one Telegram event cannot race.

    Firestore is still the cross-process idempotency authority; this lock
    closes the smaller same-process race between product matching, greeting
    and support forwarding.
    """
    async def serialized(event, *args, **kwargs):
        user_id = getattr(event, "sender_id", None)
        if user_id is None:
            return await handler(event, *args, **kwargs)
        lock = USER_EVENT_LOCKS.setdefault(int(user_id), asyncio.Lock())
        async with lock:
            return await handler(event, *args, **kwargs)
    return serialized


async def claim_product_reply(user_id, product):
    """Keep one automatic product card per product and private chat."""
    product_id = str(product.get("id") or product.get("url") or product.get("title") or "product")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_id)[:100]
    claimed = await asyncio.to_thread(
        firestore_helper.claim_remote_document,
        f"support_product_once_lisansarena_{int(user_id)}_{safe_id}",
        {"brand": "lisansarena", "user_id": int(user_id), "product_id": product_id},
        True,
    )
    return claimed is True


async def send_product_card(event, matched_products):
    event_id = getattr(event.message, "id", None)
    if event_id is None or not await claim_support_event("LisansArena", event.sender_id, event_id, "product_card"):
        record_event("duplicate_suppressed", "LisansArena", source="telegram_private", reason="product_event_already_claimed")
        return False
    claimed_products = []
    for product in matched_products[:3]:
        if await claim_product_reply(event.sender_id, product):
            claimed_products.append(product)
    if not claimed_products:
        # The original product card is already in the conversation. Keep the
        # new message in the support queue without another automatic reply.
        return False
    for product in claimed_products:
        product["_cta_id"] = os.urandom(8).hex()
    lines = ["LisansArena ürün seçenekleri", ""]
    buttons = []
    for product in claimed_products:
        lines.append(f"• {product['title']} — {product.get('price') or 'Fiyat bilgisi için destek'}")
        buttons.append([Button.url("🛒 Mağazada İncele", purchase_url(product, "lisansarena", "support_bot_dm"))])
    buttons.append([Button.inline("💬 Destek", b"ticket_support")])
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
    ("magaza", "Telegram mağazasını aç"),
    ("urunler", "Ürün kataloğunu görüntüle"),
    ("bakiye", "Bakiye ve yükleme ekranı"),
    ("siparisler", "Siparişlerini görüntüle"),
    ("hesaplar", "Hesap ve referans profilin"),
    ("gecmis", "Bakiye hareketlerin"),
    ("kullanim", "Teslimat ve kullanım bilgileri"),
    ("talep", "Yeni ürün talebi oluştur"),
    ("destek", "Destek talebi oluştur"),
    ("iade", "İade talebi oluştur"),
    ("referans", "Referans profilini görüntüle"),
    ("cekilis", "Aktif çekilişleri görüntüle"),
    ("ayarlar", "Hesap ayarları"),
    ("dil", "Dil seçimini değiştir"),
    ("yardim", "Komutları ve yardımı görüntüle"),
]


def mini_app_markup(label="Mağazayı Aç"):
    return ReplyInlineMarkup(rows=[KeyboardButtonRow(buttons=[
        KeyboardButtonWebView(text=f"🛍 {label}", url=MINI_APP_URL)
    ])])


def inline_menu():
    return [
        [Button.inline("🛍 Ürünler", b"menu_products"), Button.inline("💳 Bakiye", b"menu_balance")],
        [Button.inline("📦 Siparişler", b"menu_orders"), Button.inline("👤 Profil", b"menu_profile")],
        [Button.inline("💬 Destek", b"ticket_support"), Button.inline("➕ Ürün Talebi", b"ticket_request")],
    ]


def _telegram_user(sender):
    return {
        "id": sender.id,
        "username": getattr(sender, "username", "") or "",
        "first_name": getattr(sender, "first_name", "") or "",
        "last_name": getattr(sender, "last_name", "") or "",
    }


async def _store_user(event):
    sender = await event.get_sender()
    store = get_store()
    user_id = await asyncio.to_thread(store.get_or_create_user, _telegram_user(sender))
    return store, user_id, sender


async def safe_edit(event, text, **kwargs):
    try:
        return await event.edit(text, **kwargs)
    except MessageNotModifiedError:
        return None


async def respond_store_error(event, exc):
    logger.warning("Store request failed: %s", type(exc).__name__)
    await event.respond(
        "Mağaza verisine şu anda ulaşılamıyor. Mesajın destek kuyruğuna alınabilir; birkaç dakika sonra tekrar dene.",
        buttons=[[Button.inline("💬 Destek", b"ticket_support")]],
    )


async def show_main_menu(event, *, edit=False):
    text = (
        "LİSANSARENA\n\n"
        "Dijital ürünler, gerçek stok, bakiye ve sipariş takibi tek mağazada.\n\n"
        "• Otomatik teslim ürünleri stoktan verilir\n"
        "• Manuel ürünler en geç 24 saat içinde tamamlanır\n"
        "• Bakiye ödemeleri doğrulama sonrası en geç 10 dakikada yansır"
    )
    if edit:
        await safe_edit(event, text, buttons=inline_menu())
    else:
        try:
            await event.respond(text, buttons=mini_app_markup())
            await event.respond("Hızlı işlemler", buttons=inline_menu())
        except ButtonTypeInvalidError:
            await event.respond(
                f"{text}\n\nMağazayı sohbet ekranının altındaki Menü düğmesinden açabilirsin."
            )


async def show_products(event, *, edit=False):
    try:
        store, _, _ = await _store_user(event)
        catalog = await asyncio.to_thread(store.storefront_catalog)
        featured = [item for item in catalog if item.get("featured")][:6]
        active = sum(1 for item in catalog if item.get("available"))
        lines = [
            "ÜRÜN KATALOĞU",
            "",
            f"{len(catalog)} ürün katalogda · {active} ürün doğrudan satışta",
        ]
        if featured:
            lines.extend(["", "Vitrin:"])
            lines.extend(f"• {item['name']} — {item['price']}" for item in featured)
        lines.extend(["", "Tüm ürünler, kapaklar, stok ve teslim türleri mağazada gösterilir."])
        if edit:
            await safe_edit(event, "\n".join(lines), buttons=mini_app_markup("Kataloğu Aç"))
        else:
            await event.respond("\n".join(lines), buttons=mini_app_markup("Kataloğu Aç"))
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


async def show_balance(event, *, edit=False):
    try:
        store, user_id, _ = await _store_user(event)
        wallet = await asyncio.to_thread(store.wallet_history, user_id, 5)
        text = (
            f"BAKİYEM\n\nMevcut bakiye: {wallet['balance']}\n\n"
            "Bakiye paketini mağazada seçip ödeme bağlantısını oluşturabilirsin. "
            "Ödemeler doğrulamaya bağlı olarak en geç 10 dakika içinde yansır."
        )
        if edit:
            await safe_edit(event, text, buttons=mini_app_markup("Bakiye Yükle"))
        else:
            await event.respond(text, buttons=mini_app_markup("Bakiye Yükle"))
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


async def show_orders(event, *, edit=False):
    try:
        store, user_id, _ = await _store_user(event)
        rows = await asyncio.to_thread(store.order_history, user_id, 8)
        lines = ["SİPARİŞLERİM", ""]
        if not rows:
            lines.append("Henüz siparişin yok.")
        for order in rows:
            lines.append(f"#{order['id']} · {order['product_name']} · {order['total']} · {order['status']}")
        buttons = mini_app_markup("Siparişleri Aç")
        if edit:
            await safe_edit(event, "\n".join(lines), buttons=buttons)
        else:
            await event.respond("\n".join(lines), buttons=buttons)
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


async def show_profile(event, *, edit=False):
    try:
        store, user_id, sender = await _store_user(event)
        summary = await asyncio.to_thread(store.user_summary, user_id)
        referral = await asyncio.to_thread(store.referral_profile, user_id)
        text = (
            f"HESABIM\n\n"
            f"Telegram: @{getattr(sender, 'username', '') or sender.id}\n"
            f"Bakiye: {summary['balance']}\n"
            f"Referans kodu: {referral['code']}\n"
            f"Kayıtlı referans: {referral['count']}\n\n"
            "Referans ödülü gerçek kârlılık ölçümü tamamlanana kadar kapalıdır."
        )
        if edit:
            await safe_edit(event, text, buttons=inline_menu())
        else:
            await event.respond(text, buttons=inline_menu())
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


async def begin_ticket(event, ticket_type):
    labels = {"support": "destek sorununu", "request": "aradığın ürünü", "refund": "sipariş numarası ve iade nedenini"}
    PENDING_INPUT[event.sender_id] = ticket_type
    await event.respond(
        f"Lütfen {labels[ticket_type]} tek mesajda ayrıntılı yaz. İptal etmek için /start gönderebilirsin."
    )


async def save_ticket_from_message(event, ticket_type):
    store, user_id, sender = await _store_user(event)
    order_id = None
    if ticket_type == "refund":
        match = re.search(r"(?:#|sipariş\s*)?(\d+)", event.raw_text or "", re.I)
        order_id = int(match.group(1)) if match else None
    result = await asyncio.to_thread(
        store.create_ticket,
        user_id,
        ticket_type,
        event.raw_text,
        order_id=order_id,
    )
    record_event("human_handoff", "LisansArena", source="telegram_private")
    if SUPPORT_CHAT_ID:
        username = f"@{sender.username}" if getattr(sender, "username", None) else "yok"
        await bot.send_message(
            SUPPORT_CHAT_ID,
            f"📩 [LisansArena] {ticket_type.upper()} #{result['id']}\n"
            f"Kullanıcı ID: {event.sender_id}\nKullanıcı: {username}\n\n{event.raw_text}",
            parse_mode=None,
        )
    await event.respond(f"Talebin alındı: #{result['id']}. Yanıtını mağazadaki Profil > Taleplerim bölümünden takip edebilirsin.")


def _bot_api(method, *, payload=None, files=None):
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
        ("setChatMenuButton", {"menu_button": {"type": "web_app", "text": "🛍 Mağazayı Aç", "web_app": {"url": MINI_APP_URL}}}),
        ("setMyName", {"name": "LisansArena"}),
        ("setMyDescription", {"description": "Dijital ürünler, bakiye, otomatik ve manuel teslimat ile sipariş takibi için LisansArena mağazası."}),
        ("setMyShortDescription", {"short_description": "Dijital ürün mağazası · Stok · Bakiye · Sipariş"}),
    )
    for method, payload in calls:
        _bot_api(method, payload=payload)
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
            # Some Bot API versions/accounts do not expose this method yet;
            # command/menu configuration must still complete.
            logger.warning("Profile photo configuration skipped: %s", exc)


@bot.on(events.NewMessage(pattern=r"(?i)^/start(?:\s+(.+))?$"))
@once_per_command("start")
async def start_handler(event):
    PENDING_INPUT.pop(event.sender_id, None)
    try:
        store, user_id, _ = await _store_user(event)
        start_value = (event.pattern_match.group(1) or "").strip()
        if start_value.lower().startswith("ref_"):
            await asyncio.to_thread(store.apply_referral_code, user_id, start_value[4:])
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)
    await show_main_menu(event)


@bot.on(events.NewMessage(pattern=r"(?i)^/magaza$"))
@once_per_command("magaza")
async def store_handler(event):
    await event.respond("LisansArena mağazası", buttons=mini_app_markup())


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
    try:
        store, user_id, _ = await _store_user(event)
        wallet = await asyncio.to_thread(store.wallet_history, user_id, 12)
        lines = [f"BAKİYE GEÇMİŞİ · {wallet['balance']}", ""]
        lines.extend(f"• {row['entry_type']} · {row['amount']}" for row in wallet["entries"])
        if not wallet["entries"]:
            lines.append("Henüz hareket yok.")
        await event.respond("\n".join(lines), parse_mode=None)
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


@bot.on(events.NewMessage(pattern=r"(?i)^/kullanim$"))
@once_per_command("kullanim")
async def guides_handler(event):
    try:
        store, user_id, _ = await _store_user(event)
        rows = await asyncio.to_thread(store.order_history, user_id, 10)
        delivered = [row for row in rows if row["status"] == "delivered"]
        if not delivered:
            await event.respond("Teslim edilmiş siparişin bulunmuyor.")
            return
        blocks = ["TESLİMAT VE KULLANIM"]
        for row in delivered:
            blocks.append(f"\n#{row['id']} · {row['product_name']}")
            if row.get("delivery"):
                blocks.append("Teslimat: " + " | ".join(row["delivery"]))
            blocks.append("Rehber: " + (row.get("product_guide") or "Ürün talimatı için destek kaydı oluşturabilirsin."))
        await event.respond("\n".join(blocks)[:3900], parse_mode=None)
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


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
    try:
        store, user_id, _ = await _store_user(event)
        rows = await asyncio.to_thread(store.active_draws, user_id)
        if not rows:
            await event.respond("Şu anda aktif çekiliş yok. Açıldığında mağaza ve bu komutta görünür.")
            return
        text = ["AKTİF ÇEKİLİŞLER", ""] + [f"• {row['title']}" for row in rows]
        await event.respond("\n".join(text), buttons=mini_app_markup("Çekilişleri Aç"))
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


@bot.on(events.NewMessage(pattern=r"(?i)^/(ayarlar|dil)$"))
@once_per_command("ayarlar_dil")
async def settings_handler(event):
    await event.respond("Dil seçimi", buttons=[[Button.inline("Türkçe", b"lang_tr"), Button.inline("English", b"lang_en")]])


@bot.on(events.NewMessage(pattern=r"(?i)^/yardim$"))
@once_per_command("yardim")
async def help_handler(event):
    text = "LİSANSARENA KOMUTLARI\n\n" + "\n".join(f"/{command} — {description}" for command, description in BOT_COMMANDS)
    await event.respond(text, buttons=mini_app_markup())


@bot.on(events.CallbackQuery(pattern=rb"^menu_(products|balance|orders|profile)$"))
async def menu_callback(event):
    await event.answer()
    name = event.pattern_match.group(1).decode()
    if name == "products": await show_products(event, edit=True)
    elif name == "balance": await show_balance(event, edit=True)
    elif name == "orders": await show_orders(event, edit=True)
    else: await show_profile(event, edit=True)


@bot.on(events.CallbackQuery(pattern=rb"^ticket_(support|request|refund)$"))
async def ticket_callback(event):
    await event.answer()
    await begin_ticket(event, event.pattern_match.group(1).decode())


@bot.on(events.CallbackQuery(pattern=rb"^lang_(tr|en)$"))
async def language_callback(event):
    await event.answer()
    try:
        store, user_id, _ = await _store_user(event)
        language = event.pattern_match.group(1).decode()
        await asyncio.to_thread(store.set_language, user_id, language)
        await safe_edit(event, "Dil tercihin kaydedildi." if language == "tr" else "Language preference saved.", buttons=inline_menu())
    except (StoreUnavailable, ValueError) as exc:
        await respond_store_error(event, exc)


@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def private_message_handler(event):
    if getattr(event, "out", False) or not event.is_private or (event.raw_text or "").startswith("/"):
        return
    if event.sender_id == ADMIN_ID and event.is_reply:
        original = await event.get_reply_message()
        match = re.search(r"Kullanıcı ID:\s*(\d+)", original.raw_text or "") if original else None
        if match:
            await bot.send_message(int(match.group(1)), f"LisansArena destek yanıtı:\n\n{event.raw_text}", parse_mode=None)
            await event.respond("Yanıt kullanıcıya iletildi.")
        return
    incoming_event_id = getattr(event.message, "id", None)
    if incoming_event_id is None or not await claim_support_event(
        "LisansArena", event.sender_id, incoming_event_id, "incoming"
    ):
        return
    dm_intent = record_dm_event(
        "LisansArena", event.sender_id, event.raw_text or "",
        message_id=incoming_event_id,
    )

    # Product questions are handled before ticket forwarding, matching the
    # ad-account and Froxy support flows. A product claim is per user/product,
    # so asking about Windows does not suppress a later Office request.
    if event.raw_text and dm_intent == INTENT_SALES_LEAD:
        matched_products = match_sales_products(
            event.raw_text, load_sales_catalog("lisansarena"), limit=3
        )
        if matched_products:
            await send_product_card(event, matched_products)
            return

    pending = PENDING_INPUT.pop(event.sender_id, None)
    if pending:
        try:
            await save_ticket_from_message(event, pending)
        except (StoreUnavailable, ValueError) as exc:
            await respond_store_error(event, exc)
        return

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
            "Mesajın destek ekibine iletildi. Ürün, stok, bakiye ve sipariş işlemleri için mağazayı açabilirsin.",
            buttons=mini_app_markup(),
        )


async def main():
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            # BotFather configuration is not part of the reconnect loop.  The
            # Bot API rate-limits repeated setMyCommands/setChatMenuButton
            # calls for many hours, which used to leave an old Mini App URL in
            # the Telegram menu after a restart.  Set it explicitly only when
            # an operator asks for a one-time refresh.
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
