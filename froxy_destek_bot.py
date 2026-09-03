import os
import json
import logging
import re
import asyncio
import time
from functools import wraps
import urllib.request
from telethon import TelegramClient, events, Button
from telethon.tl import types
from telethon.errors import MessageNotModifiedError
from telethon.sessions import StringSession
import user_lang_helper
import firestore_helper
from sales_metrics import conversation_key, record_dm_event, record_event
from customer_intent import INTENT_SALES_LEAD
from shopier_catalog import fetch_shopier_catalog, match_catalog_products
from support_flow import claim_auto_reply_once, claim_first_greeting, claim_support_event, forward_customer_message, greeting_for, one_time_mode_enabled, release_product_claim, release_support_event, respond_with_floodwait, save_ticket_record
from sales_conversion import (
    apply_froxy_price_overrides,
    has_sales_query,
    load_sales_catalog,
    match_sales_products,
    parse_cta_start_parameter,
    listing_url,
)

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("FroxyDestekBot")
USER_EVENT_LOCKS = {}

def serialize_user_events(handler):
    async def serialized(event, *args, **kwargs):
        lock = USER_EVENT_LOCKS.setdefault(event.sender_id, asyncio.Lock())
        async with lock:
            return await handler(event, *args, **kwargs)
    return serialized

async def safe_event_edit(event, *args, **kwargs):
    """Repeated button taps are harmless; Telegram rejects identical edits."""
    try:
        edit_method = event.edit
        return await edit_method(*args, **kwargs)
    except MessageNotModifiedError:
        logger.debug("Ignored an identical callback edit for user %s.", event.sender_id)
        return None

_DESTEK_MEMORY_CLAIMS = set()

async def async_claim_event(event, scope):
    message_id = getattr(event.message, "id", None)
    if not message_id or event.chat_id is None:
        return True
    doc_id = f"dm_event_{scope}_{event.chat_id}_{message_id}"
    if doc_id in _DESTEK_MEMORY_CLAIMS:
        return False
    _DESTEK_MEMORY_CLAIMS.add(doc_id)
    if len(_DESTEK_MEMORY_CLAIMS) > 10000:
        _DESTEK_MEMORY_CLAIMS.clear()
        _DESTEK_MEMORY_CLAIMS.add(doc_id)
    fields = {"scope": scope, "chat_id": event.chat_id, "message_id": message_id}
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, firestore_helper.claim_document, doc_id, fields
        )
        if result is not True:
            return False
    except Exception:
        return False
    return True


def once_per_command(command):
    """Ensure a command update produces one reply across all workers."""
    def decorator(handler):
        @wraps(handler)
        async def wrapped(event, *args, **kwargs):
            if not await async_claim_event(event, f"froxy_cmd_{command}"):
                return
            return await handler(event, *args, **kwargs)
        return wrapped
    return decorator


_FROXY_PROD_CLAIMS = set()

async def claim_product_reply(user_id, product):
    """Persist a one-product-per-private-chat claim across restarts."""
    product_id = str(product.get("id") or product.get("url") or product.get("title") or "product")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_id)[:100]
    doc_id = f"support_product_once_froxy_{int(user_id)}_{safe_id}"
    if doc_id in _FROXY_PROD_CLAIMS:
        return False
    _FROXY_PROD_CLAIMS.add(doc_id)
    if len(_FROXY_PROD_CLAIMS) > 10000:
        _FROXY_PROD_CLAIMS.clear()
        _FROXY_PROD_CLAIMS.add(doc_id)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            firestore_helper.claim_remote_document,
            doc_id,
            {"brand": "froxy", "user_id": int(user_id), "product_id": product_id},
        )
        if result is False:
            return False
    except Exception:
        pass
    return True

API_ID = int(os.environ.get("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "").strip()
CONFIG_FILE = "bot_config.json"

# Load config
def save_ticket_to_file(bot_type, user_id, first_name, last_name, username, message):
    try:
        save_ticket_record(bot_type, user_id, first_name, last_name, username, message)
    except Exception as e:
        logger.error(f"Error saving ticket to file: {e}")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Config load error: {e}")
        return None

config = load_config()
if not config:
    logger.error("bot_config.json could not be loaded. Exiting.")
    exit(1)

BOT_TOKEN = (
    os.environ.get("FROXY_SUPPORT_BOT_TOKEN")
    or os.environ.get("FROXY_BOT_TOKEN")
    or config.get("froxy_bot_token")
    or config.get("support_bot_token")
    or ""
).strip()
ADMIN_ID = int(os.environ.get("FROXY_ADMIN_ID", config.get("froxy_admin_id", config.get("admin_id", 0))) or 0)
BOT_USER_ID = None
FROXY_SHOPIER_URL = "https://www.shopier.com/froxyai"
_render_external_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
_configured_mini_app_url = os.environ.get("FROXY_MINI_APP_URL", "").strip().rstrip("/")
# Older deployments carried one of these retired hostnames in their env.  A
# service's Render URL is authoritative, so never keep advertising a retired
# copy when Render provides the current external URL.
if _configured_mini_app_url and any(
    retired in _configured_mini_app_url.lower()
    for retired in ("froxy-bot-live.onrender.com", "froxy-bot-live-r5se.onrender.com", "froxy-bot-wjzr.onrender.com")
):
    _configured_mini_app_url = ""
FROXY_MINI_APP_URL = (
    (f"{_render_external_url}/froxy" if _render_external_url else "")
    or _configured_mini_app_url
    or "https://froxy-bot-live-nvnp.onrender.com/froxy"
).rstrip("/") + "/"

BOT_COMMANDS = [
    ("start", "Froxy AI uygulamasını aç"),
    ("app", "Froxy AI uygulamasını aç"),
    ("magaza", "Froxy mağazasını aç"),
    ("destek", "Destek talebi oluştur"),
    ("dil", "Dil seçimini değiştir"),
]


def froxy_app_button(label="🚀 Froxy AI Uygulamasını Aç"):
    """A genuine Telegram Web App button, not an ordinary browser URL."""
    return types.KeyboardButtonWebView(text=label, url=FROXY_MINI_APP_URL)


def _bot_api_call(method, payload):
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("description") or method)
    return result


def configure_bot_profile():
    """Configure Froxy as a Telegram Mini App entry point."""
    calls = (
        ("setMyCommands", {
            "commands": [
                {"command": command, "description": description}
                for command, description in BOT_COMMANDS
            ]
        }),
        ("setChatMenuButton", {
            "menu_button": {
                "type": "web_app",
                "text": "🚀 Froxy AI",
                "web_app": {"url": FROXY_MINI_APP_URL},
            }
        }),
        ("setMyName", {"name": "Froxy"}),
        ("setMyDescription", {
            "description": "Froxy AI uygulaması: sohbet, görsel üretimi, AI kredileri, mağaza ve destek."
        }),
        ("setMyShortDescription", {
            "short_description": "AI sohbet · Görsel · Mağaza · Destek"
        }),
    )
    for method, payload in calls:
        _bot_api_call(method, payload)

DEFAULT_FROXY_PRODUCTS = [
    {"id": "49489768", "title": "Perplexity Pro (1 Aylık Ortak)", "price": "69,99 TL", "url": "https://www.shopier.com/froxyai/49489768"},
    {"id": "49489754", "title": "ChatGPT Go (3 Aylık İndirim Kodu)", "price": "49,99 TL", "url": "https://www.shopier.com/froxyai/49489754"},
    {"id": "49489749", "title": "Gemini Ultra (1 Aylık 2500 Kredili)", "price": "399,00 TL", "url": "https://www.shopier.com/froxyai/49489749"},
    {"id": "49489734", "title": "Gemini Ultra (1 Aylık Kredisiz)", "price": "299,00 TL", "url": "https://www.shopier.com/froxyai/49489734"},
    {"id": "49489726", "title": "Codex SMS Doğrulama Kodu", "price": "29,00 TL", "url": "https://www.shopier.com/froxyai/49489726"},
    {"id": "49489721", "title": "ChatGPT Plus + Codex (1 Aylık)", "price": "599,90 TL", "url": "https://www.shopier.com/froxyai/49489721"},
    {"id": "49489705", "title": "ChatGPT Plus (1 Aylık Ortak)", "price": "39,99 TL", "url": "https://www.shopier.com/froxyai/49489705"},
    {"id": "49489691", "title": "ChatGPT Plus 30 Gün - Kişisel", "price": "499,90 TL", "url": "https://www.shopier.com/froxyai/49489691"},
    {"id": "49489681", "title": "Gemini Pro + Antigravity (18 Aylık)", "price": "249,99 TL", "url": "https://www.shopier.com/froxyai/49489681"},
    {"id": "49489671", "title": "Gemini Pro + Antigravity (12 Aylık)", "price": "169,99 TL", "url": "https://www.shopier.com/froxyai/49489671"},
    {"id": "49489662", "title": "Gemini Pro (18 Aylık Davet)", "price": "99,99 TL", "url": "https://www.shopier.com/froxyai/49489662"},
    {"id": "49489651", "title": "Gemini Pro (12 Aylık Davet)", "price": "59,99 TL", "url": "https://www.shopier.com/froxyai/49489651"},
    {"id": "47408150", "key": "kurumsal", "title": "Kurumsal Paket", "price": "1.499,99 TL", "url": "https://www.shopier.com/froxyai/47408150"},
    {"id": "47408149", "key": "isletme", "title": "İşletme Paketi", "price": "799,99 TL", "url": "https://www.shopier.com/froxyai/47408149"},
    {"id": "47408145", "key": "gelistirici", "title": "Geliştirici Paketi", "price": "599,99 TL", "url": "https://www.shopier.com/froxyai/47408145"},
    {"id": "47408141", "key": "profesyonel", "title": "Profesyonel Paket", "price": "449,99 TL", "url": "https://www.shopier.com/froxyai/47408141"},
    {"id": "47408138", "key": "populer", "title": "Popüler Paket", "price": "249,99 TL", "url": "https://www.shopier.com/froxyai/47408138"},
    {"id": "47408136", "key": "baslangic", "title": "Başlangıç Paketi", "price": "129,99 TL", "url": "https://www.shopier.com/froxyai/47408136"},
]
DEFAULT_FROXY_SHOPIER_LINKS = {
    product["key"]: product["url"] for product in DEFAULT_FROXY_PRODUCTS if product.get("key")
}
FROXY_PRODUCTS = []

_MODEL_SUMMARY_CACHE = {"expires_at": 0.0, "count": None, "providers": None}


def load_froxy_products():
    global FROXY_PRODUCTS
    try:
        FROXY_PRODUCTS = [
            apply_froxy_price_overrides(product)
            for product in fetch_shopier_catalog("froxyai")
        ]
        if not FROXY_PRODUCTS:
            raise ValueError("Shopier showroom returned no products")
        logger.info("Loaded %s products from the Froxy Shopier showroom.", len(FROXY_PRODUCTS))
    except Exception as exc:
        logger.warning("Froxy Shopier catalog could not be refreshed: %s", exc)
        FROXY_PRODUCTS = [dict(product) for product in DEFAULT_FROXY_PRODUCTS]
    return FROXY_PRODUCTS


def live_model_summary():
    """Return a truthful, short model status for customer-facing messages.

    The Mini App is the source of truth.  We deliberately never claim a fixed
    model total: disabled providers and failed health checks must be reflected
    in the message users see.
    """
    now = time.time()
    if _MODEL_SUMMARY_CACHE["expires_at"] > now:
        return _MODEL_SUMMARY_CACHE["count"], _MODEL_SUMMARY_CACHE["providers"]

    api_url = FROXY_MINI_APP_URL.rstrip("/") + "/api/models"
    try:
        request = urllib.request.Request(api_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else []
        models = models if isinstance(models, list) else []
        count = payload.get("active_model_count") or payload.get("verified_total") or len(models)
        providers = payload.get("active_provider_count")
        if providers is None:
            providers = len({str(item.get("provider") or "").strip() for item in models if isinstance(item, dict)})
        count = max(0, int(count or 0))
        providers = max(0, int(providers or 0))
    except Exception as exc:
        logger.debug("Live model summary unavailable: %s", exc)
        count, providers = None, None
    _MODEL_SUMMARY_CACHE.update({"expires_at": now + 60, "count": count, "providers": providers})
    return count, providers


def model_count_label(lang="tr"):
    count, providers = live_model_summary()
    if count is None:
        return "kontrol ediliyor" if lang == "tr" else "checking now"
    if count == 0:
        return (
            "şu an doğrulanmış aktif model yok"
            if lang == "tr"
            else "no verified active models right now"
        )
    if lang == "tr":
        provider_text = f", {providers} sağlayıcı" if providers else ""
        return f"{count} doğrulanmış aktif model{provider_text}"
    provider_text = f", {providers} providers" if providers else ""
    return f"{count} verified active models{provider_text}"


def shopier_product_label(lang="tr"):
    count = len(FROXY_PRODUCTS or load_froxy_products())
    return f"{count} güncel ürün" if lang == "tr" else f"{count} current products"


def shopier_product_count():
    return len(FROXY_PRODUCTS or load_froxy_products())


def shopier_product_button(product):
    title = str(product.get("title") or "Shopier ürünü").strip()
    price = str(product.get("price") or "").strip()
    label = f"🛍️ {title}"
    if price:
        label += f" · {price}"
    return label[:60]


def shopier_delivery_label(product, lang="tr"):
    delivery_type = str(product.get("delivery_type") or "stock_or_manual").lower()
    if delivery_type == "ai_credit":
        return "Ödeme onayından sonra AI kredisi hesabınıza tanımlanır." if lang == "tr" else "AI credits are added after payment confirmation."
    if delivery_type == "instant":
        return "Stok uygunsa otomatik teslimat." if lang == "tr" else "Automatic delivery when stock is available."
    return (
        "Stok uygunsa otomatik; stok yoksa 1–3 iş günü manuel teslimat."
        if lang == "tr"
        else "Automatic when in stock; otherwise manual delivery in 1–3 business days."
    )


def shopier_menu(lang="tr"):
    """Build the Telegram store screen from the live Froxy catalog."""
    t = TEXTS[lang]
    products = list(FROXY_PRODUCTS or load_froxy_products())
    buttons = []
    for product in products:
        product_id = str(product.get("id") or "").strip()
        if not product_id:
            continue
        buttons.append([Button.inline(shopier_product_button(product), f"prod_{product_id}".encode())])
    buttons.extend([
        [froxy_app_button("🚀 Froxy AI Uygulamasını Aç" if lang == "tr" else "🚀 Open Froxy AI")],
        [Button.url("↗️ Shopier" if lang == "tr" else "↗️ Shopier", FROXY_SHOPIER_URL)],
        [Button.inline(t["main_menu"], b"menu_main")],
    ])
    title = t["pkg_menu_title"].format(product_count=shopier_product_count())
    return title, buttons

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("FROXY_SUPPORT_BOT_TOKEN is not configured. Exiting.")
    exit(1)
if not API_ID or not API_HASH:
    logger.error("TELEGRAM_API_ID / TELEGRAM_API_HASH is not configured. Exiting.")
    exit(1)

# In-memory user state
user_states = {}
PROCESSED_MESSAGE_EVENTS = set()
SUPPORT_SALES_CONTEXT = {}
USER_CTA_ATTRIBUTION = {}
PRODUCT_REPLY_COOLDOWNS = {}
PRODUCT_REPLY_COOLDOWN_SECONDS = 15 * 60

def filter_products_outside_cooldown(user_id, products):
    now = time.monotonic()
    for key, expires in list(PRODUCT_REPLY_COOLDOWNS.items()):
        if expires <= now:
            PRODUCT_REPLY_COOLDOWNS.pop(key, None)
    return [
        product for product in products
        if PRODUCT_REPLY_COOLDOWNS.get(f"{user_id}:{product['id']}", 0) <= now
    ]

def mark_product_reply_sent(user_id, products):
    expires = time.monotonic() + PRODUCT_REPLY_COOLDOWN_SECONDS
    for product in products:
        PRODUCT_REPLY_COOLDOWNS[f"{user_id}:{product['id']}"] = expires

# Initialize client
bot = TelegramClient("froxy_destek_bot_session", API_ID, API_HASH)

TEXTS = {
    "tr": {
        "welcome": (
            "⚡ **Froxy AI**\n\n"
            "Telegram içinde sohbet, görsel üretimi ve güvenli Shopier mağazası.\n"
            "🧠 **Model durumu:** {model_count}\n"
            "🛍️ **Mağaza:** {product_count}\n\n"
            "Uygulamayı açın; yalnızca o anda çalışan ve doğrulanan modeller gösterilir."
        ),
        "packages_btn": "🛍️ Shopier Mağazasını Gör",
        "ai_tools_btn": "🤖 Aktif Modelleri Gör",
        "support_btn": "💬 Froxy Desteğe Yaz",
        "web_btn": "🚀 Froxy AI'ı Aç",
        "lang_btn": "🌐 Dil Seçimi / Language",
        "main_menu": "↩️ Ana Menü",
        "pkg_btn_list": [],
        "ai_btn_list": [],
        "pkg_menu_title": "🛍️ **Froxy Shopier Mağazası**\n\n"
                          "{product_count} güncel ürün ve fiyatı aşağıda görebilirsiniz.\n"
                          "AI kredi paketleri ödeme onayından sonra tanımlanır; diğer ürünlerde stok yoksa teslimat 1–3 iş günüdür.\n\n"
                          "İncelemek istediğiniz ürünü seçin:",
        "back_to_pkgs": "↩️ Paketlere Dön",
        "buy_shopier": "💳 Shopier ile Güvenli Satın Al",
        "buy_web": "🛒 Shopier'den Satın Al",
        "product_header": "🛍️ **{title}**\n\n💰 **Fiyat:** {price}\n🚚 **Teslimat:** {delivery}\n\n{desc}\n\nÖdeme ve güncel ürün bilgisi için Shopier bağlantısını kullanın.",
        "support_title": "💬 **Froxy AI Desteği**",
        "support_desc": "Ürün, ödeme, kredi veya uygulama sorununu tek mesajda yazın.\n\nSipariş numaranız varsa ekleyin; destek ekibi buradan dönüş yapar.",
        "cancel": "↩️ Vazgeç ve İptal Et",
        "support_success": "✅ Mesajınız Froxy AI ekibine iletildi. En kısa sürede yanıt alacaksınız.",
        "support_fail": "⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.",
        "support_inactive": "⚠️ Destek yapılandırması şu anda kullanılamıyor. Lütfen uygulamadaki destek bağlantısından yazın.",
        "reply_prefix": "📨 **Froxy AI Destek Ekibinden Cevap:**\n\n",
        "choose_lang": "Lütfen dilinizi seçin / Please choose your language:",
        "products": {},
    },
    "en": {
        "welcome": (
            "⚡ **Froxy AI**\n\n"
            "Chat, image generation and the secure Shopier store in Telegram.\n"
            "🧠 **Model status:** {model_count}\n"
            "🛍️ **Store:** {product_count}\n\n"
            "Open the app; only models that are currently healthy and verified are shown."
        ),
        "packages_btn": "🛍️ View Shopier Store",
        "ai_tools_btn": "🤖 View Active Models",
        "support_btn": "💬 Contact Froxy Support",
        "web_btn": "🚀 Open Froxy AI",
        "lang_btn": "🌐 Language / Dil",
        "main_menu": "↩️ Main Menu",
        "pkg_btn_list": [],
        "ai_btn_list": [],
        "pkg_menu_title": "🛍️ **Froxy Shopier Store**\n\n"
                          "{product_count} current products and prices are listed below.\n"
                          "AI credit packages are added after payment confirmation; other products are delivered within 1–3 business days when out of stock.\n\n"
                          "Select a product:",
        "back_to_pkgs": "↩️ Back to Packages",
        "buy_shopier": "💳 Secure Purchase with Shopier",
        "buy_web": "🛒 Purchase on Shopier",
        "product_header": "🛍️ **{title}**\n\n💰 **Price:** {price}\n🚚 **Delivery:** {delivery}\n\n{desc}\n\nUse the Shopier link for the current product information and payment.",
        "support_title": "💬 **Froxy AI Support**",
        "support_desc": "Send one message describing your product, payment, credit or app issue.\n\nInclude your order number when available; the support team will reply here.",
        "cancel": "↩️ Cancel & Go Back",
        "support_success": "✅ Your message has been forwarded to the Froxy AI team. You will receive a response as soon as possible.",
        "support_fail": "⚠️ Your message could not be delivered. Please try again later.",
        "support_inactive": "⚠️ Support is not configured right now. Please use the support link inside the app.",
        "reply_prefix": "📨 **Reply from Froxy AI Support Team:**\n\n",
        "choose_lang": "Please choose your language / Lütfen dilinizi seçin:",
        "products": {},
    }
}

# Language Selection Screen Helper
async def show_lang_selection(event, is_callback=False):
    text = "Lütfen dilinizi seçin / Please choose your language:"
    buttons = [
        [froxy_app_button()],
        [Button.inline("🇹🇷 Türkçe", b"lang_tr"), Button.inline("🇺🇸 English", b"lang_en")]
    ]
    if is_callback:
        await safe_event_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)

# Main Menu Helper
async def show_main_menu(event, user_id, is_callback=False):
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]
    
    presence = firestore_helper.get_document("habil_presence") or {}
    is_online = presence.get("is_online", False)
    status_emoji = "🟢 **Destek Çevrimiçi / Support Online**" if is_online else "🔴 **Destek Çevrimdışı / Support Offline**"
    
    welcome_body = t["welcome"].format(
        model_count=model_count_label(lang),
        product_count=shopier_product_label(lang),
    )
    welcome_text = (
        f"{status_emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{welcome_body}"
    )
    
    buttons = [
        [froxy_app_button(t["web_btn"])],
        [Button.url("🛒 Shopier Ürün Sayfası", FROXY_SHOPIER_URL)],
        [Button.inline(t["support_btn"], b"menu_support")],
        [Button.inline(t["lang_btn"], b"menu_lang")],
    ]
    
    if is_callback:
        await safe_event_edit(event, welcome_text, buttons=buttons)
    else:
        await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))
async def verify_payment_callback(event):
    try:
        await event.answer()
    except:
        pass
    text = (
        "⚡ **Froxy AI Uygulaması**\n\n"
        "Sohbet, görsel, kredi ve siparişler için uygulamayı açın."
    )
    buttons = [
        [froxy_app_button()],
        [Button.url("🛒 Shopier Ürün Sayfası", FROXY_SHOPIER_URL)],
        [Button.inline("↩️ Vazgeç ve Geri Dön", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if not await async_claim_event(event, "froxy_support"):
        return
    user_id = event.sender_id
    
    ban_data = firestore_helper.get_document(f"ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        await event.respond("⚠️ **Hesabınız askıya alınmıştır.** İletişime geçmek için yöneticinize başvurun.")
        return
        
    user_states[user_id] = None
    
    message_text = event.message.message or ""
    if " " in message_text:
        parts = message_text.split(" ", 1)
        param = parts[1].strip()
        cta_data = parse_cta_start_parameter(param)
        if cta_data and cta_data["brand"] == "froxy":
            USER_CTA_ATTRIBUTION[user_id] = {
                **cta_data,
                "expires_at": time.monotonic() + 7 * 24 * 60 * 60,
            }
            record_event(
                "ad_cta_open", "Froxy AI", source="telegram_start",
                arm=cta_data["arm"], group_hash=cta_data["group_hash"],
            )
            
    lang = user_lang_helper.get_user_lang(user_id)
    if not lang:
        await show_lang_selection(event)
    else:
        await show_main_menu(event, user_id)

@bot.on(events.NewMessage(pattern=r'/lang|/dil'))
@once_per_command("lang")
async def lang_cmd_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    await show_lang_selection(event)


@bot.on(events.NewMessage(pattern=r'/magaza'))
async def store_cmd_handler(event):
    if not await async_claim_event(event, "froxy_support"):
        return
    await event.respond(
        "⚡ Froxy AI uygulamasını aşağıdaki düğmeden açabilirsiniz.",
        buttons=[[froxy_app_button()], [Button.url("🛒 Shopier Ürün Sayfası", FROXY_SHOPIER_URL)]],
    )


@bot.on(events.NewMessage(pattern=r'/app'))
@once_per_command("app")
async def app_cmd_handler(event):
    await event.respond(
        "⚡ **Froxy AI**\n\nSohbet, görsel üretimi, mağaza ve siparişlerini tek uygulamada yönet.",
        buttons=[[froxy_app_button()]],
    )


@bot.on(events.NewMessage(pattern=r'/destek'))
async def support_cmd_handler(event):
    if not await async_claim_event(event, "froxy_support"):
        return
    user_states[event.sender_id] = "AWAITING_SUPPORT"
    lang = user_lang_helper.get_user_lang(event.sender_id) or "tr"
    t = TEXTS[lang]
    await event.respond(
        f"{t['support_title']}\n\n{t['support_desc']}",
        buttons=[[Button.inline(t["cancel"], b"menu_main")]],
    )

@bot.on(events.CallbackQuery(pattern=r'lang_(\w+)'))
async def lang_select_callback(event):
    user_id = event.sender_id
    lang = event.data.decode('utf-8').replace("lang_", "")
    user_lang_helper.set_user_lang(user_id, lang)
    
    if lang == "tr":
        await event.answer("Dil Türkçe olarak ayarlandı.", alert=False)
    else:
        await event.answer("Language set to English.", alert=False)
        
    await show_main_menu(event, user_id, is_callback=True)

@bot.on(events.CallbackQuery(data=b'menu_lang'))
async def menu_lang_callback(event):
    await show_lang_selection(event, is_callback=True)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    await show_main_menu(event, user_id, is_callback=True)

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    try:
        await event.answer()
    except:
        pass
    lang = user_lang_helper.get_user_lang(event.sender_id) or "tr"
    text, buttons = shopier_menu(lang)
    await safe_event_edit(event, text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_ai_tools'))
async def ai_tools_menu_handler(event):
    try:
        await event.answer()
    except:
        pass
    lang = user_lang_helper.get_user_lang(event.sender_id) or "tr"
    text, buttons = shopier_menu(lang)
    try:
        await safe_event_edit(event, text, buttons=buttons)
    except Exception:
        pass


@bot.on(events.CallbackQuery(pattern=r"prod_(\d+)"))
async def shopier_product_handler(event):
    """Show a catalog product using the same source as the Mini App."""
    try:
        await event.answer()
    except Exception:
        pass
    lang = user_lang_helper.get_user_lang(event.sender_id) or "tr"
    product_id = event.data.decode("utf-8").split("_", 1)[1]
    product = next(
        (item for item in (FROXY_PRODUCTS or load_froxy_products()) if str(item.get("id")) == product_id),
        None,
    )
    if not product:
        await safe_event_edit(
            event,
            "Bu ürün artık katalogda bulunmuyor. Güncel listeyi yeniden açın." if lang == "tr" else "This product is no longer in the catalog. Open the current list again.",
            buttons=[[Button.inline("↩️ Mağazaya Dön" if lang == "tr" else "↩️ Back to Store", b"menu_packages")]],
        )
        return
    t = TEXTS[lang]
    description = str(product.get("description") or "Shopier ürün sayfasında güncel açıklama ve ödeme bilgisi gösterilir.")
    text = t["product_header"].format(
        title=product.get("title") or "Shopier ürünü",
        price=product.get("price") or "Shopier sayfasında",
        delivery=shopier_delivery_label(product, lang),
        desc=description,
    )
    product_url = str(product.get("url") or FROXY_SHOPIER_URL)
    buttons = [
        [froxy_app_button("🚀 Froxy AI'da Aç" if lang == "tr" else "🚀 Open in Froxy AI")],
        [Button.url("💳 Shopier'de İncele / Satın Al" if lang == "tr" else "💳 View / Buy on Shopier", product_url)],
        [Button.inline("↩️ Mağazaya Dön" if lang == "tr" else "↩️ Back to Store", b"menu_packages")],
    ]
    await safe_event_edit(event, text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_referral'))
async def menu_referral_handler(event):
    await safe_event_edit(
        event,
        "⚡ Froxy AI kredileri ve siparişleri uygulama üzerinden yönetilir. Shopier ürün sayfası alternatif olarak aşağıdadır.",
        buttons=[
            [froxy_app_button()],
            [Button.url("🛒 Shopier Ürün Sayfası", FROXY_SHOPIER_URL)],
            [Button.inline("↩️ Ana Menü", b"menu_main")],
        ],
    )

# Package detail handler
@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    try:
        await event.answer()
    except:
        pass
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]

    pkg_key = event.data.decode('utf-8').replace("pkg_", "")
    package_product_ids = {
        "baslangic": "47408136",
        "populer": "47408138",
        "profesyonel": "47408141",
        "gelistirici": "47408145",
        "isletme": "47408149",
        "kurumsal": "47408150",
        "chatgpt_kisisel": "49489691",
        "chatgpt_codex": "49489721",
        "chatgpt_ortak": "49489705",
        "codex_sms": "49489726",
        "gemini_12m": "49489651",
        "gemini_18m": "49489662",
        "gemini_anti_12m": "49489671",
        "gemini_anti_18m": "49489681",
        "gemini_ultra_kredisiz": "49489734",
        "gemini_ultra_25k": "49489749",
        "chatgpt_go": "49489754",
        "perplexity_ortak": "49489768",
    }
    selected_id = package_product_ids.get(pkg_key)
    selected_product = next((p for p in load_sales_catalog("froxy") if str(p.get("id")) == selected_id), None)
    if not selected_product:
        selected_product = next((p for p in FROXY_PRODUCTS if str(p.get("id")) == selected_id), None)
    if not selected_product:
        selected_product = next((p for p in DEFAULT_FROXY_PRODUCTS if str(p.get("id")) == selected_id), None)
    p_data = {
        "title": selected_product.get("title") if selected_product else pkg_key.replace("_", " ").title(),
        "price": selected_product.get("price", "") if selected_product else "",
        "credits": "",
        "desc": "Ürün detayları ve güvenli ödeme Shopier ürün sayfasında gösterilir.",
    }
    shopier_url = listing_url(selected_product) if selected_product else ""

    text = t["product_header"].format(
        title=p_data['title'],
        price=p_data['price'],
        credits=p_data['credits'],
        delivery=shopier_delivery_label(selected_product or {}, lang),
        desc=p_data['desc']
    )
    
    buttons = [
        [froxy_app_button("🚀 Froxy AI'da Aç")],
        [Button.url(t["buy_shopier"], shopier_url)] if shopier_url else [Button.inline("💬 Destek üzerinden sipariş", b"menu_support")],
        [Button.inline(t["back_to_pkgs"], b"menu_packages")]
    ]
    try:
        await safe_event_edit(event, text, buttons=buttons)
    except Exception:
        pass

# Support Menu
@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]
    
    user_states[user_id] = "AWAITING_SUPPORT"

    buttons = [
        [Button.inline(t["cancel"], b"menu_main")]
    ]
    await safe_event_edit(event, f"{t['support_title']}\n\n{t['support_desc']}", buttons=buttons)

@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def message_handler(event):
    if getattr(event, "out", False) or not event.text or event.text.startswith('/'):
        return
    event_key = (event.chat_id, getattr(event.message, "id", None))
    if event_key in PROCESSED_MESSAGE_EVENTS:
        return
    PROCESSED_MESSAGE_EVENTS.add(event_key)
    if len(PROCESSED_MESSAGE_EVENTS) > 10000:
        PROCESSED_MESSAGE_EVENTS.clear()
    if not await async_claim_event(event, "froxy_support"):
        return

    user_id = event.sender_id
    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
    support_chat_id = config.get("support_chat_id", admin_chat_id)
    
    # Ban check
    ban_data = firestore_helper.get_document(f"ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        return

    is_admin_context = event.sender_id == admin_chat_id or event.chat_id == support_chat_id

    sender = await event.get_sender()
    uname = getattr(sender, 'username', '') or ''
    fname = getattr(sender, 'first_name', '') or ''
    lname = getattr(sender, 'last_name', '') or ''
    msg_text = event.text or ''

    logger.info(f"📥 [Froxy AI] DM Alındı: GÖNDEREN={user_id} (@{uname}) MESAJ='{msg_text}'")
    print(f"📥 [Froxy AI] DM Alındı: GÖNDEREN={user_id} (@{uname}) MESAJ='{msg_text}'", flush=True)

    if not is_admin_context:
        try:
            save_ticket_record(
                "Froxy AI",
                user_id,
                fname,
                lname,
                f"@{uname}" if uname else "Yok",
                msg_text,
            )
        except Exception as exc:
            logger.warning("Ticket kaydı hatası: %s", exc)

    dm_intent = record_dm_event(
        "Froxy AI", user_id, event.text or "",
        message_id=getattr(event.message, "id", None),
        has_sales_context=bool(SUPPORT_SALES_CONTEXT.get(user_id)),
    )

    # Resolve sales intent before the generic greeting.  Product questions
    # must result in one product card, not a greeting followed by a card.
    matched_products = []
    if not is_admin_context and event.text and dm_intent == INTENT_SALES_LEAD:
        matched_products = match_sales_products(event.text, load_sales_catalog("froxy"), limit=3)

    if matched_products:
        reply_event_id = getattr(event.message, "id", None)
        if reply_event_id is None or not await claim_support_event("Froxy AI", user_id, reply_event_id, "product_card"):
            record_event("duplicate_suppressed", "Froxy AI", source="telegram_private", reason="product_event_already_claimed")
            return
        candidate_products = filter_products_outside_cooldown(user_id, matched_products)
        claimed_products = []
        for product in candidate_products:
            if await claim_product_reply(user_id, product):
                claimed_products.append(product)
        if not claimed_products:
            record_event("duplicate_suppressed", "Froxy AI", source="telegram_private", reason="product_already_sent")
            return
        matched_products = claimed_products
        for product in matched_products:
            product["_cta_id"] = os.urandom(8).hex()
        attribution = USER_CTA_ATTRIBUTION.get(user_id, {})
        if attribution.get("expires_at", 0) <= time.monotonic():
            attribution = {}
            USER_CTA_ATTRIBUTION.pop(user_id, None)
        arm = attribution.get("arm", "")
        lang = user_lang_helper.get_user_lang(user_id) or "tr"
        t = TEXTS[lang]
        lines = ["🔎 **Uygun Froxy ürünleri:**", ""]
        buttons = [[froxy_app_button("🚀 Froxy AI Uygulamasını Aç")]]
        for product in matched_products:
            price = product.get("price") or "Fiyat ürün sayfasında"
            lines.append(f"• **{product['title']}** — {price}")
            buttons.append([Button.url(f"🛒 {product['title'][:40]}", listing_url(product))])
        buttons.append([Button.inline(t["support_btn"], b"menu_support")])
        try:
            await respond_with_floodwait(event, "\n".join(lines), buttons=buttons)
        except Exception:
            await release_support_event("Froxy AI", user_id, reply_event_id, "product_card")
            for product in matched_products:
                await release_product_claim(
                    "froxy", user_id,
                    str(product.get("id") or product.get("url") or product.get("title") or "product"),
                )
            raise
        mark_product_reply_sent(user_id, matched_products)
        SUPPORT_SALES_CONTEXT[user_id] = {
            "product": dict(matched_products[0]),
            "expires_at": asyncio.get_running_loop().time() + 15 * 60,
        }
        safe_conversation = conversation_key("Froxy AI", user_id)
        record_event("product_matched", "Froxy AI", source="telegram_private", product=matched_products[0].get("title", ""), product_count=len(matched_products), arm=arm, conversation_key=safe_conversation)
        for product in matched_products:
            record_event(
                "purchase_cta_sent", "Froxy AI", source="telegram_private",
                product=product.get("title", ""), product_id=product.get("id", ""),
                cta_key=product.get("_cta_id", ""), arm=arm,
                conversation_key=safe_conversation,
            )
        record_event("dm_reply_sent", "Froxy AI", source="telegram_private", product=matched_products[0].get("title", ""))
        return

    if one_time_mode_enabled() and not is_admin_context:
        buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"adm_ban_{user_id}".encode())]]
        if await forward_customer_message(bot, event, support_chat_id, "Froxy AI", buttons):
            record_event("dm_manual_forwarded", "Froxy AI", source="telegram_private")
            if await claim_first_greeting("froxy", user_id):
                await event.respond(greeting_for("Froxy AI"))
                record_event("dm_greeting_sent", "Froxy AI", source="telegram_private")
        if user_states.get(user_id) == "AWAITING_SUPPORT":
            user_states[user_id] = None
            return

    if user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return
            
        input_val = event.text.strip().lower()
        if "@" in input_val:
            doc_id = "order_email_" + input_val.replace("@", "_").replace(".", "_")
        else:
            doc_id = "order_phone_" + input_val.replace("+", "").replace(" ", "")
            
        orders_doc = firestore_helper.get_document(doc_id)
        if not orders_doc or not orders_doc.get("orders"):
            await event.respond("❌ **Sipariş bulunamadı!** Girdiğiniz bilgiyi kontrol edip tekrar deneyin veya desteğe yazın. (Ödeme sonrası 1-2 dakika gecikme olabilir).")
            user_states[user_id] = None
            return
            
        orders = orders_doc.get("orders", [])
        unclaimed_order = None
        unclaimed_idx = -1
        for i, o in enumerate(orders):
            if not o.get("claimed", False):
                unclaimed_order = o
                unclaimed_idx = i
                break
                
        if not unclaimed_order:
            await event.respond("⚠️ **Bu bilgilere ait tüm siparişler zaten tanımlanmış!** Yardım isterseniz canlı destekten bize yazabilirsiniz.")
            user_states[user_id] = None
            return
            
        prod_name = unclaimed_order.get("product_name", "").lower()
        credits_to_add = 0
        pkg_title = "Bilinmeyen Paket"
        
        if "baslangic" in prod_name or "5.000" in prod_name or "5k" in prod_name or "starter" in prod_name:
            credits_to_add = 5000
            pkg_title = "🚀 Başlangıç Paketi (5.000 Kredi)"
        elif "populer" in prod_name or "15.000" in prod_name or "15k" in prod_name or "popular" in prod_name:
            credits_to_add = 15000
            pkg_title = "⭐ Popüler Paket (15.000 Kredi)"
        elif "profesyonel" in prod_name or "50.000" in prod_name or "50k" in prod_name or "professional" in prod_name:
            credits_to_add = 50000
            pkg_title = "💼 Profesyonel Paket (50.000 Kredi)"
        else:
            credits_to_add = 5000
            pkg_title = f"Özel Paket ({unclaimed_order.get('product_name')})"
            
        user_doc_id = f"user_{user_id}"
        user_data = firestore_helper.get_document(user_doc_id) or {
            "credits": 100,
            "referred_by": "",
            "id": user_id
        }
        user_data["credits"] = user_data.get("credits", 100) + credits_to_add
        firestore_helper.set_document(user_doc_id, user_data)
        
        orders[unclaimed_idx]["claimed"] = True
        firestore_helper.set_document(doc_id, orders_doc)
        
        await event.respond(
            f"✅ **Ödemeniz Başarıyla Doğrulandı!**\n\n"
            f"📦 **Satın Alınan:** {pkg_title}\n"
            f"🎯 **Tanımlanan Kredi:** +{credits_to_add} Kredi\n"
            f"💰 **Yeni Kredi Bakiyeniz:** {user_data['credits']} Kredi\n\n"
            f"Froxy AI'ı keyifle kullanın! 🤖"
        )
        user_states[user_id] = None
        
        try:
            config = load_config() or {}
            support_chat_id = config.get("support_chat_id", config.get("admin_id", ADMIN_ID))
            if support_chat_id:
                await bot.send_message(
                    support_chat_id, 
                    f"🎉 **Shopier Otomatik Satış Bildirimi!**\n"
                    f"👤 **Kullanıcı:** `{user_id}`\n"
                    f"📦 **Ürün:** {pkg_title}\n"
                    f"💰 **Tutar:** {unclaimed_order.get('amount')} ₺\n"
                    f"🛍️ **Sipariş ID:** `{unclaimed_order.get('order_id')}`\n"
                    f"📧 **E-posta/Telefon:** {input_val}"
                )
        except Exception:
            pass
            
        user_states[user_id] = None
        return

    if not is_admin_context and event.text:
        if dm_intent != INTENT_SALES_LEAD:
            record_event(
                "human_handoff", "Froxy AI", source="telegram_private",
                reason=dm_intent,
            )
            return
        context = SUPPORT_SALES_CONTEXT.get(user_id)
        if context and context.get("expires_at", 0) > asyncio.get_running_loop().time():
            product = context["product"]
            record_event("human_handoff", "Froxy AI", source="telegram_private", product=product.get("title", ""), reason="followup_after_product")
            return
        if has_sales_query(event.text):
            if not await claim_auto_reply_once("Froxy AI", user_id, "clarification", event.chat_id):
                return
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            await event.respond(
                "Aradığınız ürünü doğru bulabilmem için ürün adını ve varsa kişisel/ortak ya da süre tercihinizi yazar mısınız?",
                buttons=[[Button.inline(t["support_btn"], b"menu_support")]],
            )
            record_event("human_handoff", "Froxy AI", source="telegram_private", reason="no_product_match")
            record_event("dm_reply_sent", "Froxy AI", source="telegram_private", product="clarification")
            return

    if user_states.get(user_id) == "AWAITING_SUPPORT":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        lang = user_lang_helper.get_user_lang(user_id) or "tr"
        t = TEXTS[lang]

        if not admin_chat_id:
            await event.respond(t["support_inactive"])
            user_states[user_id] = None
            return

        user = await event.get_sender()
        username = f"@{user.username}" if user.username else "Yok"
        first_name = user.first_name or ""
        last_name = user.last_name or ""

        admin_msg = (
            f"📩 **Yeni Froxy AI Destek Talebi!**\n"
            f"👤 **Kullanıcı ID:** `{user_id}`\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\n"
            f"💬 **Kullanıcı Adı:** {username}\n"
            f"🌐 **Dil/Lang:** {lang.upper()}\n"
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        admin_buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"adm_ban_{user_id}".encode())]]

        try:
            await bot.send_message(admin_chat_id, admin_msg, buttons=admin_buttons)
            await event.respond(t["support_success"])
            save_ticket_to_file("Froxy AI", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    if event.sender_id == admin_chat_id or event.chat_id == support_chat_id:
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                # Ensure the replied-to message was sent by this bot itself to prevent cross-talk
                match = re.search(r"(?:Kullanıcı ID|User ID|ID):\*\*?\s*`?(\d+)`?", reply_msg.text, re.IGNORECASE)

                if match:
                    target_user_id = int(match.group(1))
                    target_lang = user_lang_helper.get_user_lang(target_user_id) or "tr"
                    prefix = TEXTS[target_lang]["reply_prefix"]
                    
                    # Clean event.text if it starts with #reply or /reply prefix
                    text_to_send = event.text.strip()
                    clean_match = re.match(r"^(?:#reply|/reply)\s*(.*)$", text_to_send, re.DOTALL | re.IGNORECASE)
                    if clean_match:
                        text_to_send = clean_match.group(1).strip()
                        
                    if not text_to_send:
                        await event.reply("⚠️ Lütfen boş mesaj göndermeyin.")
                        return

                    try:
                        await bot.send_message(target_user_id, f"{prefix}{text_to_send}")
                        await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                    except Exception as e:
                        logger.error(f"Failed to reply to user {target_user_id}: {e}")
                        await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")
        elif event.text.startswith("#reply") or event.text.startswith("/reply"):
            # Command style: #reply <user_id> <message>
            cmd_match = re.match(r"^(?:#reply|/reply)\s+(\d+)\s+(.+)$", event.text, re.DOTALL | re.IGNORECASE)
            if cmd_match:
                target_user_id = int(cmd_match.group(1))
                message_body = cmd_match.group(2).strip()
                target_lang = user_lang_helper.get_user_lang(target_user_id) or "tr"
                prefix = TEXTS[target_lang]["reply_prefix"]
                try:
                    await bot.send_message(target_user_id, f"{prefix}{message_body}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")
            else:
                await event.reply("⚠️ Yanlış format! Kullanım: `#reply [kullanıcı_id] [mesajınız]`")

# Admin Action Callbacks
@bot.on(events.CallbackQuery(pattern=r'adm_add_(\d+)_(\d+)'))
async def admin_add_credits_callback(event):
    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
    if event.sender_id != admin_chat_id:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    await event.answer("Froxy kredi sistemi kapatıldı; satışlar yalnız Shopier üzerinden yürütülür.", alert=True)

@bot.on(events.CallbackQuery(pattern=r'adm_ban_(\d+)'))
async def admin_ban_user_callback(event):
    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
    if event.sender_id != admin_chat_id:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    target_user_id = int(event.pattern_match.group(1))
    
    ban_doc_id = f"ban_{target_user_id}"
    firestore_helper.set_document(ban_doc_id, {"banned": True, "id": target_user_id})
    
    await event.answer("🚫 Kullanıcı engellendi.", alert=True)
    original_text = event.message.text
    await safe_event_edit(event, f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

if __name__ == '__main__':
    import asyncio
    from telethon.errors import FloodWaitError

    logger.info("Loading Froxy Shopier products cache...")
    load_froxy_products()
    
    async def start_with_retry():
        global BOT_USER_ID
        while True:
            try:
                logger.info("Starting Froxy AI Support Bot (@FroxyDestekBOT)...")
                await bot.start(bot_token=BOT_TOKEN)
                me = await bot.get_me()
                BOT_USER_ID = me.id
                try:
                    configure_bot_profile()
                    logger.info("Froxy Telegram profile and menu configured for Shopier.")
                except Exception as exc:
                    logger.warning("Froxy Telegram profile configuration failed: %s", exc)
                logger.info(f"Froxy AI Support Bot started successfully! Bot User ID: {BOT_USER_ID}")
                await bot.run_until_disconnected()
            except FloodWaitError as e:
                logger.warning(f"FloodWait: Telegram {e.seconds} saniye beklememizi istiyor. Bekleniyor...")
                await asyncio.sleep(e.seconds + 5)
                logger.info("FloodWait süresi bitti, tekrar deneniyor...")
            except Exception as e:
                logger.error(f"Bot başlatma hatası: {e}")
                await asyncio.sleep(30)
    
    bot.loop.run_until_complete(start_with_retry())
