import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
import time
import uuid
from functools import wraps
from telethon import TelegramClient, events, Button
from telethon.errors import MessageNotModifiedError
from telethon.sessions import StringSession
import user_lang_helper
import firestore_helper
from gemini_helper import get_ai_response
from sales_catalog import filter_keyvadi_products
from sales_metrics import conversation_key, record_dm_event, record_event
from customer_intent import INTENT_SALES_LEAD
from support_flow import claim_auto_reply_once, claim_first_greeting, claim_support_event, forward_customer_message, greeting_for, one_time_mode_enabled, release_product_claim, release_support_event, respond_with_floodwait, save_ticket_record
from update_keyvadi_links_json import fetch_live_catalog, write_catalog_atomic
from sales_conversion import (
    listing_url,
    load_sales_catalog,
    match_sales_products,
    parse_cta_start_parameter,
    purchase_url,
    resolve_smart_roadmap_reply,
)
from marketing_cards import (
    build_price_drop_card,
    build_selling_fast_card,
    parse_fiyatdusur_args,
    parse_sonstok_args,
)
from announcement_delivery import (
    AnnouncementQueue,
    build_announcement_item,
    drain_queue,
    load_subscribers,
    match_stock_product,
    parse_stock_command,
    send_telethon_item,
    stock_card_text,
)
from bot_runtime_status import invalid_token_error, write_bot_status
from lead_retargeting import record_lead_interaction, run_retargeting_loop

# Async wrappers for firestore_helper to prevent event loop deadlocks/freezes
async def async_get_document(doc_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.get_document, doc_id)

async def async_set_document(doc_id, fields_dict):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.set_document, doc_id, fields_dict)

async def async_delete_document(doc_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.delete_document, doc_id)

def get_event_claim_doc_id(event, scope):
    message_id = getattr(event.message, 'id', None)
    if not message_id or event.chat_id is None:
        return None
    return f"dm_event_{scope}_{event.chat_id}_{message_id}"

_FROXY_MEMORY_CLAIMS = set()

async def async_claim_event(event, scope):
    doc_id = get_event_claim_doc_id(event, scope)
    if not doc_id:
        return True
        
    if doc_id in _FROXY_MEMORY_CLAIMS:
        return False
    _FROXY_MEMORY_CLAIMS.add(doc_id)
    if len(_FROXY_MEMORY_CLAIMS) > 10000:
        _FROXY_MEMORY_CLAIMS.clear()
        _FROXY_MEMORY_CLAIMS.add(doc_id)
        
    try:
        result = await async_run_claim(doc_id, {"scope": scope, "chat_id": event.chat_id, "message_id": getattr(event.message, 'id', None)})
        if result is not True:
            return False
    except Exception:
        return False
    return True

async def async_release_event_claim(event, scope):
    doc_id = get_event_claim_doc_id(event, scope)
    if doc_id:
        await async_delete_document(doc_id)

async def async_run_claim(doc_id, fields):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.claim_document, doc_id, fields)


def once_per_command(command):
    """Ensure a command update is handled once even with duplicate workers."""
    def decorator(handler):
        @wraps(handler)
        async def wrapped(event, *args, **kwargs):
            if not await async_claim_event(event, f"keyvadi_cmd_{command}"):
                return
            return await handler(event, *args, **kwargs)
        return wrapped
    return decorator


_KEYVADI_PROD_CLAIMS = set()

async def claim_product_reply(user_id, product):
    """Persist a one-product-per-private-chat claim across restarts."""
    product_id = str(product.get("id") or product.get("url") or product.get("title") or "product")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_id)[:100]
    doc_id = f"support_product_once_keyvadi_{int(user_id)}_{safe_id}"
    if doc_id in _KEYVADI_PROD_CLAIMS:
        return False
    _KEYVADI_PROD_CLAIMS.add(doc_id)
    if len(_KEYVADI_PROD_CLAIMS) > 10000:
        _KEYVADI_PROD_CLAIMS.clear()
        _KEYVADI_PROD_CLAIMS.add(doc_id)
    try:
        result = await async_run_claim(
            doc_id,
            {"brand": "keyvadi", "user_id": int(user_id), "product_id": product_id},
        )
        if result is not True:
            return False
    except Exception:
        return False
    return True

PRODUCT_REPLY_COOLDOWN_SECONDS = 15 * 60
PRODUCT_REPLY_COOLDOWNS = {}
LAST_AI_REPLY_TIME = {}
AUTO_REPLY_COOLDOWN_SECONDS = 300
LAST_AUTO_REPLY_TIME = {}
SUPPORT_SALES_CONTEXT = {}
USER_CTA_ATTRIBUTION = {}
def _product_reply_key(user_id, product=None, fallback_key=None):
    if product:
        product_key = str(product.get('id') or product.get('url') or product.get('title') or '').lower()
    else:
        product_key = (fallback_key or 'fallback').strip().lower()[:100]
    return f"{user_id}:{product_key}"

def filter_products_outside_cooldown(user_id, products):
    now = time.monotonic()
    for key, expires in list(PRODUCT_REPLY_COOLDOWNS.items()):
        if expires <= now:
            PRODUCT_REPLY_COOLDOWNS.pop(key, None)
    return [
        product for product in products
        if PRODUCT_REPLY_COOLDOWNS.get(_product_reply_key(user_id, product), 0) <= now
    ]

def mark_product_reply_sent(user_id, products):
    expires = time.monotonic() + PRODUCT_REPLY_COOLDOWN_SECONDS
    for product in products:
        PRODUCT_REPLY_COOLDOWNS[_product_reply_key(user_id, product)] = expires

def is_auto_reply_cooling_down(user_id):
    return time.monotonic() - LAST_AUTO_REPLY_TIME.get(user_id, 0) < AUTO_REPLY_COOLDOWN_SECONDS

def mark_auto_reply_sent(user_id):
    LAST_AUTO_REPLY_TIME[user_id] = time.monotonic()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    # app.py captures stdout into froxy_bot_log.txt in production.
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KeyVadiBot")
USER_EVENT_LOCKS = {}

def serialize_user_events(handler):
    async def serialized(event, *args, **kwargs):
        user_id = event.sender_id
        lock = USER_EVENT_LOCKS.setdefault(user_id, asyncio.Lock())
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

API_ID = int(os.environ.get("TELEGRAM_API_ID", "31076280") or 31076280)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8").strip()
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
    os.environ.get("KEYVADI_SUPPORT_BOT_TOKEN") or
    os.environ.get("KEYVADI_BOT_TOKEN") or
    config.get("keyvadi_bot_token") or
    ""
).strip()
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", config.get("admin_id", 0)) or 0)
ADMIN_IDS = {
    8791896048,  # KeyVadiDestek (New ID)
    6196006704,  # KeyVadiDestek (Legacy ID)
    5359327143,  # User / ittersdv / Klyde
    8116518175,  # Habil
}


def is_admin(user_id):
    """Check if user_id is authorized admin."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
        if uid in ADMIN_IDS:
            return True
        cfg = load_config() or {}
        cfg_admin = cfg.get("admin_id")
        if cfg_admin and uid == int(cfg_admin):
            return True
        for a_id in cfg.get("admin_ids", []):
            if uid == int(a_id):
                return True
        if ADMIN_ID and uid == int(ADMIN_ID):
            return True
    except Exception:
        pass
    return False
BOT_USER_ID = None
PROFILE_CONFIGURED = False
SHOPIER_LINKS = config.get("shopier_links", {})
_PUBLIC_BASE_URL = (
    os.environ.get("RENDER_EXTERNAL_URL")
    or "https://bot-service-production-9d74.up.railway.app"
).strip().rstrip("/")
KEYVADI_MINI_APP_URL = os.environ.get(
    "KEYVADI_MINI_APP_URL",
    f"{_PUBLIC_BASE_URL}/keyvadi/",
).strip().rstrip("/") + "/"
KEYVADI_GROUP_LINK = os.environ.get(
    "KEYVADI_GROUP_LINK",
    config.get("keyvadi_group_link", "https://t.me/keyvadipazar"),
).strip()

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("KEYVADI_SUPPORT_BOT_TOKEN is not configured. Exiting.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient(StringSession(), API_ID, API_HASH)

BOT_COMMANDS = [
    ("start", "KeyVadi ana menuyu ac"),
    ("firsatlar", "Price Drop & Son Stok Firsatlari"),
    ("magaza", "KeyVadi magazasini ac"),
    ("urunler", "Urun katalogunu goruntule"),
    ("bakiye", "Cuzdan & Bakiye Yukle"),
    ("siparisler", "Siparis gecmisini gor"),
    ("destek", "Canli Destek ekibine baglan"),
    ("referans", "Davet et & indirim kazan"),
    ("stok", "Admin: stok duyurusu karti olustur"),
]


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
    """Configure the KeyVadi command list and persistent 3-line menu button."""
    _bot_api_call("setMyCommands", {
        "commands": [
            {"command": command, "description": description}
            for command, description in BOT_COMMANDS
        ]
    })
    _bot_api_call("setChatMenuButton", {
        "menu_button": {
            # A commands menu does not carry Telegram Web App initData.  Use
            # the persistent three-line Mini App entry point so wallet and
            # checkout requests can authenticate the customer.
            "type": "web_app",
            "text": "Magazayi Ac",
            "web_app": {"url": KEYVADI_MINI_APP_URL},
        }
    })
    _bot_api_call("setMyName", {"name": "KeyVadi"})
    _bot_api_call("setMyDescription", {
        "description": "Dijital urunler, lisanslar, abonelikler ve guvenli Shopier alisverisi icin KeyVadi magazasi."
    })
    _bot_api_call("setMyShortDescription", {
        "short_description": "Dijital urun magazasi - Shopier - Destek"
    })


def mini_app_markup(label="Magazayi Ac"):
    from telethon import Button
    app_launch_url = "https://t.me/KeyVadiSatisBot/app"
    return [
        [Button.url(label, app_launch_url)],
        [Button.inline("En Cok Satan Firsatlar", b"menu_top7")],
        [Button.inline("Kategoriler", b"menu_categories"), Button.inline("Urun Ara", b"menu_search_prompt")],
        [Button.inline("Gunluk Sans Kasasi", b"menu_daily_box"), Button.inline("Garanti ve Guvenlik", b"menu_faq")],
        [Button.inline("Siparis Sorgula", b"menu_order_status"), Button.inline("Canli Destek", b"menu_support")],
        [Button.inline("Davet & Kazan", b"menu_referral"), Button.inline("Cuzdan / Bakiye", b"menu_topup")],
        [Button.url("KeyVadi Resmi Topluluk Grubu", KEYVADI_GROUP_LINK)]
    ]

@bot.on(events.CallbackQuery())
async def acknowledge_callback(event):
    """Acknowledge Telegram callbacks immediately so the first click is not stuck."""
    try:
        await event.answer()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# KeyVadi Product Catalog - Shopier üzerinden satılan ürünler
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {}

# Products that are NOT in the Shopier showroom (hidden/delisted/paginated) but still active
# These are injected into the catalog alongside scraped products
INJECTED_PRODUCTS = [
    # Son yayinlanan ilanlar. keyvadi_shopier_links.json yeniden uretilse bile
    # bu urunlerin katalogdan dusmemesi icin burada da tutuluyor.
    {"id": "49099017", "title": "FC26 + Online Her Şeyi Değişen Hesap", "price": "299.99 TL", "url": "https://www.shopier.com/49099017"},
    {"id": "49099015", "title": "Zula Random Hesap", "price": "5.00 TL", "url": "https://www.shopier.com/49099015"},
    {"id": "50665156", "title": "Netflix 4K UHD Ortak Profil", "price": "39.99 TL", "url": "https://www.shopier.com/50665156"},
    {"id": "49099013", "title": "Steam 200 Dolar Random Key", "price": "30.00 TL", "url": "https://www.shopier.com/49099013"},
    {"id": "50576032", "title": "Tıkla Gelsin 400 TL'ye 200 TL İndirim Kuponu", "price": "80.00 TL", "url": "https://www.shopier.com/50576032"},
]

# Flat list of all products (rebuilt when products are loaded)
ALL_PRODUCTS_FLAT = []

# ═══════════════════════════════════════════════════════════════
# Smart Product Matching - Müşteri serbest metin yazınca ürün eşleştir
# ═══════════════════════════════════════════════════════════════

SALES_INTENT_KEYWORDS = {
    "fiyat", "ücret", "tl", "satın", "almak", "alacağım", "sipariş",
    "ürün", "stok", "link", "shopier", "ödeme", "ödemek", "kampanya",
    "indirim", "premium", "lisans", "hesap", "abonelik", "paket", "üyelik",
    "canva", "adobe", "netflix", "youtube", "spotify", "capcut", "chatgpt",
    "var mı", "mevcut mu", "nasıl alırım", "satın al",
    "minecraft", "s sport", "ssport", "yemeksepeti", "turna",
    "coffy", "cofy", "migros", "kupon", "kod", "bakiye", "market", "kahve",
    "3 ay", "1 ay", "aylık", "yıllık", "ortak", "kişisel",
    "tikla gelsin", "tıkla gelsin", "tiklagelsin", "tıklagelsin", "uber", "tod", "tiktak", "enuygun",
}

def has_sales_intent(text):
    normalized = (text or "").strip().lower()
    return bool(normalized) and any(
        re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", normalized)
        for keyword in SALES_INTENT_KEYWORDS
    )

def _get_words(text):
    """Tokenize text into lowercase words."""
    return re.findall(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+', text.lower())

def match_product_from_text(msg_text):
    """Try to match a product from free-text message. Returns (product_dict, score) or (None, 0)."""
    msg_clean = msg_text.lower().strip()
    
    # Aliases & normalization
    msg_clean = msg_clean.replace("you tube", "youtube")
    msg_clean = re.sub(r'\byt\b', 'youtube', msg_clean)
    msg_clean = re.sub(r'\bwin\b', 'windows', msg_clean)
    msg_clean = msg_clean.replace("win10", "windows")
    msg_clean = msg_clean.replace("win11", "windows")
    msg_clean = msg_clean.replace("office365", "office 365")
    msg_clean = msg_clean.replace("gamepass", "game pass")
    msg_clean = msg_clean.replace("cc", "creative cloud")
    msg_clean = msg_clean.replace("prime video", "prime")
    msg_clean = re.sub(r'\bmc\b', 'minecraft', msg_clean)
    
    query_words = _get_words(msg_clean)
    
    # Brand keywords — query must contain at least one to trigger matching
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "creative",
        "4k", "uhd", "game", "lisans", "microsoft",
        "tradingview", "nordvpn", "vpn", "kaspersky", "envato", "freepik",
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot", "discord",
        "minecraft", "amazon", "prime", "tikla", "tıkla", "gelsin", "yemeksepeti", "uber", "tod",
        "tiktak", "enuygun", "flo", "lumberjack", "zula", "fc26"
    }
    
    has_brand = any(w in brand_keywords for w in query_words)
    logger.info(f"Matching text: '{msg_text}' | words: {query_words} | has_brand: {has_brand}")
    if not has_brand:
        return None, 0
        
    query_brands = [w for w in query_words if w in brand_keywords]
    
    # Skip words — too generic to contribute to scoring
    skip_words = {
        "var", "mi", "mı", "mu", "mü", "ve", "de", "da", "için", "misiniz", "miyiz",
        "olur", "miyim", "yok", "acaba", "hizmeti", "ürünü", "hesabı", "kodu", "kuponu",
        "premium", "alacaktım", "hocam", "knk", "kanka", "bir", "alacağım", "alacaktim",
        "istiyorum", "lazım", "lazim", "alalım", "alalim", "kaç", "kac", "fiyat",
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi",
        "nasıl", "nasil", "nedir", "site", "link", "al", "almak", "satın"
    }
    
    best_product = None
    best_score = 0
    
    for p in ALL_PRODUCTS_FLAT:
        title_lower = p.get("title", "").lower()
        title_words = set(_get_words(title_lower))
        
        # Skip internal products
        if "bakiye" in title_lower or "keyvadi" in title_lower:
            continue
            
        # Enforce brand check: Matched product must contain at least one of the query's brand words
        if query_brands:
            if not any(b in title_words for b in query_brands):
                continue
        
        score = 0
        matched_brand = False
        
        # 1. Phrase match (2 consecutive query words found in title) — very strong signal
        for i in range(len(query_words) - 1):
            phrase = f"{query_words[i]} {query_words[i+1]}"
            if phrase in title_lower:
                score += 50
                
        # 2. Whole-word match (query word is a standalone token in title)
        for w in query_words:
            if w in skip_words:
                continue
            if len(w) <= 1:
                continue
            if w in title_words:
                score += 20
                if w in brand_keywords:
                    matched_brand = True
            # Partial match only for longer words (>5 chars)
            elif len(w) > 5:
                for tw in title_words:
                    if w in tw or tw in w:
                        score += 8
                        break
        
        # 3. If no brand word from the query matched this product's title, skip
        if not matched_brand and score < 50:
            continue
        
        # === PENALTIES ===
        # Variant mismatch: ultra vs pro vs davet (for AI products)
        if "ultra" in query_words and "ultra" not in title_words:
            score -= 100
        if "ultra" not in query_words and "ultra" in title_words and "pro" in query_words:
            score -= 100
        if "pro" in query_words and "pro" not in title_words and "davet" not in title_words:
            if any(bw in query_words for bw in ["gemini", "grok", "gamma"]):
                score -= 80
                
        # Duration mismatch
        q_durations = {"haftalık", "aylık", "yıllık", "günlük"}
        q_dur = [w for w in query_words if w in q_durations]
        q_nums = [w for w in query_words if w.isdigit()]
        if q_dur and q_nums:
            dur_phrase = f"{q_nums[0]} {q_dur[0]}"
            if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                score -= 15
        
        # Food vs Market
        if "yemek" in query_words and "yemek" not in title_words:
            score -= 100
        if "market" in query_words and "market" not in title_words:
            score -= 100
        if "yemek" not in query_words and "yemek" in title_words:
            score -= 50
        if "market" not in query_words and "market" in title_words:
            score -= 50
            
        # Windows vs Office
        if "windows" in query_words and "windows" not in title_words:
            score -= 80
        if "office" in query_words and "office" not in title_words:
            score -= 80
            
        if score > best_score:
            best_score = score
            best_product = p
            
    logger.info(f"Best match for '{msg_text}': {best_product['title'] if best_product else 'NONE'} with score {best_score}")
    if best_score >= 20:
        return best_product, best_score
    return None, 0

def match_multiple_products_from_text(msg_text):
    msg_clean = msg_text.lower().strip()
    msg_clean = msg_clean.replace("you tube", "youtube")
    msg_clean = re.sub(r'\byt\b', 'youtube', msg_clean)
    msg_clean = re.sub(r'\bwin\b', 'windows', msg_clean)
    msg_clean = msg_clean.replace("win10", "windows")
    msg_clean = msg_clean.replace("win11", "windows")
    msg_clean = msg_clean.replace("office365", "office 365")
    msg_clean = msg_clean.replace("gamepass", "game pass")
    msg_clean = msg_clean.replace("cc", "creative cloud")
    
    query_words = _get_words(msg_clean)
    
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "creative",
        "4k", "uhd", "game", "lisans", "microsoft",
        "tradingview", "nordvpn", "vpn", "kaspersky", "envato", "freepik",
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot", "discord",
        "hbo", "prime", "perplexity", "magnific", "telegram", "tg"
    }
    
    primary_brands = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "tradingview", "nordvpn", "vpn",
        "kaspersky", "envato", "freepik", "autocad", "figma", "elementor", 
        "grammarly", "deepl", "ideogram", "quillbot", "discord", "hbo", "prime", "perplexity",
        "magnific"
    }
    
    query_brands = [w for w in query_words if w in brand_keywords]
    if not query_brands:
        return []
        
    query_primary_brands = [w for w in query_words if w in primary_brands]
    target_brands = list(set(query_primary_brands if query_primary_brands else query_brands))
    
    skip_words = {
        "var", "mi", "mı", "mu", "mü", "ve", "de", "da", "için", "misiniz", "miyiz",
        "olur", "miyim", "yok", "acaba", "hizmeti", "ürünü", "hesabı", "kodu", "kuponu",
        "premium", "alacaktım", "hocam", "knk", "kanka", "bir", "alacağım", "alacaktim",
        "istiyorum", "lazım", "lazim", "alalım", "alalim", "kaç", "kac", "fiyat",
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi",
        "nasıl", "nasil", "nedir", "site", "link", "al", "almak", "satın"
    }
    
    matched_products = []
    
    for brand in target_brands:
        best_product = None
        best_score = 0
        
        for p in ALL_PRODUCTS_FLAT:
            title_lower = p.get("title", "").lower()
            title_words = set(_get_words(title_lower))
            
            if "bakiye" in title_lower or "keyvadi" in title_lower:
                continue
                
            # Enforce brand check
            if brand not in title_words:
                if brand == "adobe" and "creative" in title_words:
                    pass
                elif brand == "creative" and "adobe" in title_words:
                    pass
                else:
                    continue
                
            score = 0
            matched_brand = False
            
            for i in range(len(query_words) - 1):
                phrase = f"{query_words[i]} {query_words[i+1]}"
                if phrase in title_lower:
                    score += 50
                    
            for w in query_words:
                if w in skip_words:
                    continue
                if len(w) <= 1:
                    continue
                if w in title_words:
                    score += 20
                    if w in brand_keywords:
                        matched_brand = True
                elif len(w) > 5:
                    for tw in title_words:
                        if w in tw or tw in w:
                            score += 8
                            break
            
            # Duration mismatch
            q_durations = {"haftalık", "aylık", "yıllık", "günlük"}
            q_dur = [w for w in query_words if w in q_durations]
            q_nums = [w for w in query_words if w.isdigit()]
            if q_dur and q_nums:
                dur_phrase = f"{q_nums[0]} {q_dur[0]}"
                if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                    score -= 15
                            
            if not matched_brand and score < 50:
                continue
                
            # Penalties
            if "ultra" in query_words and "ultra" not in title_words:
                score -= 100
            if "ultra" not in query_words and "ultra" in title_words and "pro" in query_words:
                score -= 100
            if "pro" in query_words and "pro" not in title_words and "davet" not in title_words:
                if any(bw in query_words for bw in ["gemini", "grok", "gamma"]):
                    score -= 80
                    
            if q_dur and q_nums:
                dur_phrase = f"{q_nums[0]} {q_dur[0]}"
                if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                    score -= 30
                    
            if "yemek" in query_words and "yemek" not in title_words:
                score -= 100
            if "market" in query_words and "market" not in title_words:
                score -= 100
            if "yemek" not in query_words and "yemek" in title_words:
                score -= 50
            if "market" not in query_words and "market" in title_words:
                score -= 50
                
            if "windows" in query_words and "windows" not in title_words:
                score -= 80
            if "office" in query_words and "office" not in title_words:
                score -= 80
                
            if score > best_score:
                best_score = score
                best_product = p
                
        if best_product and best_score >= 20:
            if best_product not in matched_products:
                matched_products.append(best_product)
                
    return matched_products

def scrape_shopier():
    logger.info("Scraping Shopier showroom at https://www.shopier.com/keyvadi ...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request('https://www.shopier.com/keyvadi', headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_data = response.read()
            try:
                html_content = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                html_content = raw_data.decode('windows-1254', errors='ignore')
                
            # Regex to find product cards
            cards = html_content.split('class="product-card shopier--product-card')
            products = []
            
            for card in cards[1:]:
                # Extract link/ID
                link_match = re.search(r'href="(https://www\.shopier\.com/keyvadi/(\d+))"', card)
                title_match = re.search(r'class="shopier-store--store-product-card-title">([^<]+)</h3>', card)
                price_match = re.search(r'data-price="([^"]+)"', card)
                
                if link_match and title_match and price_match:
                    url = link_match.group(1)
                    pid = link_match.group(2)
                    title = html.unescape(title_match.group(1).strip())
                    price = price_match.group(1).strip()
                    price = re.sub(r'\s+', '', price)
                    
                    price_str = price
                    if not (price_str.endswith("TL") or price_str.endswith("₺")):
                        price_str = f"{price_str} TL"
                    
                    products.append({
                        "id": pid,
                        "title": title,
                        "price": price_str,
                        "url": url
                    })
            
            logger.info(f"Successfully scraped {len(products)} products from Shopier.")
            return products
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return []

def normalize_catalog_product(product):
    """Shopier API, eski katalog ve scraper kayıtlarını tek biçime getir."""
    if not isinstance(product, dict):
        return None
    normalized = dict(product)
    pid = str(normalized.get("id") or "").strip()
    title = str(normalized.get("title") or "").strip()
    url = str(normalized.get("url") or normalized.get("link") or "").strip()
    if not pid or not title or not url:
        return None

    price = normalized.get("price")
    if not price:
        price = (normalized.get("priceData") or {}).get("price", "")
    price = re.sub(r"(?:\s*(?:TL|₺))+\s*$", "", str(price or ""), flags=re.I).strip()

    normalized.update({
        "id": pid,
        "title": title,
        "url": url,
        "price": f"{price} TL" if price else "Fiyat için iletişime geçin",
    })
    return normalized


def normalize_catalog_products(products):
    normalized = []
    seen_ids = set()
    for product in products:
        item = normalize_catalog_product(product)
        if not item or item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        normalized.append(item)
    return normalized


def rebuild_categories(products):
    global CATEGORIES

    temp_categories = {
        "ai": {"title": "🌟 Yapay Zeka (AI) Çözümleri", "products": {}},
        "streaming": {"title": "📺 Dizi, Film & Müzik", "products": {}},
        "design": {"title": "🎨 Tasarım, Eğitim & Verimlilik", "products": {}},
        "social": {"title": "💬 Discord & Sosyal Platformlar", "products": {}},
        "coupons": {"title": "🎟️ Kupon, İndirim & Bakiye", "products": {}},
        "games": {"title": "🎮 Oyun & Game Pass", "products": {}},
        "accounts": {"title": "📱 Telegram, WhatsApp & Mobil Hesaplar", "products": {}},
        "license": {"title": "🔑 Windows, Office & Diğer Lisanslar", "products": {}},
    }

    for p in normalize_catalog_products(products):
        title = p["title"]
        pid = p["id"]
        t = title.casefold()

        if any(k in t for k in [
            "gemini", "grok", " ai", "ai ", "gamma", "kiro", "chatgpt",
            "openai", "copilot", "claude", "midjourney", "semrush", "deepl",
            "quill", "ideogram", "perplexity", "magnific", "grammarly",
        ]):
            cat_key = "ai"
        elif any(k in t for k in [
            "netflix", "prime video", "prime", "amazon", "hbo", "crunchyroll", "exxen", "blutv",
            "disney", "youtube", "spotify", "music",
        ]):
            cat_key = "streaming"
        elif any(k in t for k in [
            "canva", "adobe", "creative cloud", "express", "capcut", "duolingo",
            "scribd", "tasarım", "design",
        ]):
            cat_key = "design"
        elif any(k in t for k in ["discord", "nitro", "sunucu boost", "server boost"]):
            cat_key = "social"
        elif any(k in t for k in [
            "trendyol", "shell", "kupon", "indirim", "bakiye", "keyvadi.bond",
            "akaryakıt", "puan", "yemeksepeti", "coffy", "migros", "turna",
        ]):
            cat_key = "coupons"
        elif any(k in t for k in [
            "steam", "xbox", "game pass", "gamepass", "minecraft", "fc26", "zula", "oyun",
        ]):
            cat_key = "games"
        elif any(k in t for k in [
            "telegram", "whatsapp", "apple id", "icloud", "numara",
        ]):
            cat_key = "accounts"
        else:
            cat_key = "license"

        temp_categories[cat_key]["products"][pid] = {
            "title": title,
            "price": p["price"],
            "url": p["url"],
        }

    CATEGORIES = temp_categories
    logger.info(
        "In-memory categories rebuilt: %s",
        {key: len(value["products"]) for key, value in CATEGORIES.items()},
    )

def load_products_from_file_or_scrape():
    global ALL_PRODUCTS_FLAT
    products = []
    file_path = "parsed_keyvadi_products.json"
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)
            logger.info(f"Loaded {len(products)} products from local file {file_path}.")
        except Exception as e:
            logger.error(f"Error reading local products file: {e}")
            
    if not products:
        logger.info("Local products file not found or empty. Scraping Shopier showroom...")
        products = scrape_shopier()
        if products:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(products, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error saving scraped products to file: {e}")
    
    # Merge the authoritative local Shopier catalog so products missing from
    # the scraped cache are still searchable and return their purchase link.
    catalog_path = "keyvadi_shopier_links.json"
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog_products = json.load(f)
            cached_ids = {p.get("id") for p in products if p.get("id")}
            for catalog_product in catalog_products:
                if catalog_product.get("id") and catalog_product.get("id") not in cached_ids:
                    products.append(catalog_product)
                    cached_ids.add(catalog_product.get("id"))
            logger.info(f"Merged {len(catalog_products)} products from {catalog_path}.")
        except Exception as e:
            logger.error(f"Error reading authoritative Shopier catalog: {e}")

    # Merge injected products (hidden/delisted but still active)
    existing_ids = {p.get("id") for p in products if p.get("id")}
    for ip in INJECTED_PRODUCTS:
        if ip.get("id") and ip.get("id") not in existing_ids:
            products.append(ip)
            logger.info(f"Injected hidden product: {ip['title']}")
    
    # Invalid scraper satırlarını at, API/eski katalog fiyat biçimlerini düzelt.
    products = normalize_catalog_products(products)
    products = filter_keyvadi_products(products)

    # Build flat product list for smart matching
    ALL_PRODUCTS_FLAT = list(products)
    logger.info(f"Total products available for matching: {len(ALL_PRODUCTS_FLAT)}")
                
    # Rebuild in-memory categories
    rebuild_categories(products)

def refresh_live_catalog():
    """Refresh all Shopier pages; retain the last valid cache on any failure."""
    try:
        products = fetch_live_catalog("keyvadi")
        write_catalog_atomic(products, "keyvadi_shopier_links.json")
        logger.info("Refreshed all %s live KeyVadi products.", len(products))
        return products
    except Exception as exc:
        logger.warning("Live KeyVadi catalog refresh failed; cached catalog retained: %s", exc)
        return None


TEXTS = {
    "tr": {
        "welcome": (
            "**KeyVadi Satis Paneline Hos Geldiniz!**\n\n"
            "Premium yapay zeka hesaplari, lisanslar, onayli mobil hesaplar ve ozel firsatlar en uygun fiyatlarla!\n\n"
            "Lutfen yapmak istediginiz islemi secin:"
        ),
        "support_btn": "Canli Destek & Iletisim",
        "lang_btn": "Dil Secimi / Language",
        "main_menu": "<-- Ana Menu",
        "cat_title_mapping": {
            "ai": "Yapay Zeka (AI) Cozumleri",
            "streaming": "Dizi, Film & Muzik",
            "design": "Tasarim, Egitim & Verimlilik",
            "social": "Discord & Sosyal Platformlar",
            "coupons": "Kupon, Indirim & Bakiye",
            "games": "Oyun & Game Pass",
            "accounts": "Telegram, WhatsApp & Mobil Hesaplar",
            "license": "Windows, Office & Diger Lisanslar"
        },
        "select_product": "Detaylarini gormek ve satin almak istediginiz urunu secin:",
        "price": "Fiyat",
        "product_footer": "Teslimat turu urun detayinda - 7/24 destek - Guvenli odeme\n\nSatin almak icin asagidaki butona tiklayin.",
        "buy_btn": "Shopier ile Guvenli Satin Al",
        "support_title": "**Destek Talebi & Siparis Verme**",
        "support_desc": "Satin almak istediginiz urun, siparis sorunu veya destek talebinizi detaylica yazip bu sohbete gonderin.\n\nMesajiniz dogrudan admin ekibimize iletilecektir. En kisa surede yanit alacaksiniz.",
        "cancel": "Vazgec ve Iptal Et",
        "support_success": "Mesajiniz ekibimize iletildi. En kisa surede yanit alacaksiniz.",
        "support_fail": "Mesajiniz iletilemedi. Lutfen daha sonra tekrar deneyiniz.",
        "support_inactive": "Uzgunuz, su anda destek sistemi aktif degil. Lutfen daha sonra deneyin.",
        "reply_prefix": "**KeyVadi Destek Ekibinden Cevap:**\n\n",
        "choose_lang": "Lutfen dilinizi secin / Please choose your language:"
    }
}

# Main Menu Helper — Streamlined Mini App First Experience
async def show_lang_selection(event, is_callback=False):
    text = (
        "**Lutfen dil secin:**\n"
        "**Please select your language:**"
    )
    buttons = [
        [Button.inline("Turkce", b"lang_tr"), Button.inline("English", b"lang_en")]
    ]
    if is_callback:
        await safe_event_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)

async def show_main_menu(event, user_id, is_callback=False):
    welcome = (
        "**KEYVADI STORE — Dijital Lisans & E-Pin**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**KeyVadi Dunyasina Hos Geldiniz!**\n\n"
        "Netflix 4K, Gemini AI Pro, CapCut Pro, Xbox Game Pass ve Minecraft gibi tum populer lisanslar **%70 indirimle** aninda teslim!\n\n"
        "• **7/24 Aninda Otomatik Kod & Lisans Teslimati**\n"
        "• **Tam Sure Kesintisiz Degisim & Telafi Garantisi**\n"
        "• **3D Secure Guvenli Kartla Satin Alma**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "*Alisverise baslamak veya indirimli urunleri incelemek icin asagidaki butonlari kullanabilirsiniz:*"
    )
    buttons = mini_app_markup("Mağazayı Aç")
    if is_callback:
        await safe_event_edit(event, welcome, buttons=buttons)
    else:
        await event.respond(welcome, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_orders'))
async def menu_orders_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    
    users = {}
    try:
        doc = await async_get_document("keyvadi_users_data")
        if doc and "users" in doc and isinstance(doc["users"], dict):
            users = doc["users"]
    except Exception as exc:
        print(f"[KeyVadi Bot] Firestore load orders error: {exc}")
        
    if not users:
        users_file = Path("miniapp/users_data.json")
        if users_file.exists():
            try:
                users = json.loads(users_file.read_text(encoding="utf-8"))
            except Exception:
                pass
    u = users.get(str(user_id), {})
    orders = u.get("orders", [])
    
    if not orders:
        text = (
            "📦 **Sipariş Geçmişiniz**\n\n"
            "Henüz kayıtlı bir siparişiniz bulunmamaktadır.\n\n"
            "Mağazadan dilediğiniz ürünü 7/24 anında teslimat güvencesiyle satın alabilirsiniz!"
        )
        buttons = [
            [Button.url("🛍️ KeyVadi Mağazasını Aç", f"{KEYVADI_MINI_APP_URL}")],
            [Button.inline("↩️ Ana Menü", b"menu_main")]
        ]
        await safe_event_edit(event, text, buttons=buttons)
        return

    lines = ["📦 **Son Siparişleriniz:**\n"]
    for idx, o in enumerate(reversed(orders[-5:]), 1):
        title = o.get("title") or "Dijital Ürün"
        status = "✅ Teslim Edildi" if o.get("status") in ("delivered", "completed") or o.get("license_key") else "⏳ Hazırlanıyor"
        price = o.get("subtotal") or o.get("price") or o.get("amount") or 0
        lines.append(f"{idx}. **{title}** — `₺{price}` ({status})")
        if o.get("license_key"):
            lines.append(f"   🔑 Lisans Kodu: `{o.get('license_key')}`")
        elif o.get("status") == "pending_delivery":
            lines.append("   💬 *Manuel teslimat / Destek için @KeyVadiDestek ile iletişime geçin.*")
        lines.append("")

    text = "\n".join(lines)
    buttons = [
        [Button.url("🛍️ Siparişlerimi Mini App'te Gör", KEYVADI_MINI_APP_URL)],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_topup'))
async def menu_topup_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    text = (
        "💰 **KeyVadi Bakiye Yükleme (3D Secure)**\n\n"
        "Shopier altyapısı ile kredi/banka kartınızla güvenle anında bakiye yükleyebilirsiniz.\n\n"
        "• Minimum yükleme: ₺5.00\n"
        "• 3D Secure onayından sonra bakiyeniz **saniyeler içinde** cüzdanınıza aktarılır.\n"
        "• Yüklediğiniz bakiye ile dilediğiniz zaman tek tıkla lisans satın alabilirsiniz.\n\n"
        "👇 **Bakiye yüklemek için aşağıdaki butona tıklayın:**"
    )
    buttons = [
        [Button.url("⚡ Cüzdanı Aç & Bakiye Yükle", KEYVADI_MINI_APP_URL)],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))
async def verify_payment_callback(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_VERIFY_PAYMENT_INFO"
    
    text = (
        "💳 **Shopier Ödeme Doğrulama**\n\n"
        "Ödeme yaparken kullandığınız **E-posta** adresini veya **Telefon** numarasını yazıp bu sohbete gönderin. "
        "Satın aldığınız ürünün lisans kodu saniyeler içinde otomatik olarak teslim edilecektir.\n\n"
        "*(Vazgeçmek için /start yazabilirsiniz)*"
    )
    buttons = [
        [Button.inline("↩️ Vazgeç ve Geri Dön", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

# Start Handler
@bot.on(events.NewMessage(pattern=r'(?i)^/start(?:@\w+)?(?:\s+.*)?$'))
async def start_handler(event):
    if not await async_claim_event(event, "keyvadi_sales"):
        return
    user_id = event.sender_id
    
    ban_data = await async_get_document(f"keyvadi_ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        await event.respond("⚠️ **Hesabınız askıya alınmıştır.** İletişime geçmek için yöneticinize başvurun.")
        return
        
    user_states[user_id] = None
    record_lead_interaction(user_id)
    
    message_text = event.message.message or ""
    ref_id = None
    prod_key_to_show = None
    if " " in message_text:
        parts = message_text.split(" ", 1)
        param = parts[1].strip()
        if param.startswith("ref_"):
            ref_id = param.replace("ref_", "")
        elif param.startswith("p_"):
            prod_key_to_show = param.replace("p_", "")
        cta_data = parse_cta_start_parameter(param)
        if cta_data and cta_data["brand"] == "keyvadi":
            USER_CTA_ATTRIBUTION[user_id] = {
                **cta_data,
                "expires_at": time.monotonic() + 7 * 24 * 60 * 60,
            }
            record_event(
                "ad_cta_open", "KeyVadi", source="telegram_start",
                arm=cta_data["arm"], group_hash=cta_data["group_hash"],
            )
            
    user_doc_id = f"keyvadi_user_{user_id}"
    user_data = await async_get_document(user_doc_id)
    is_new = False
    
    if not user_data:
        is_new = True
        user_data = {
            "referrals_count": 0,
            "referred_by": ref_id or "",
            "id": user_id
        }
        await async_set_document(user_doc_id, user_data)
        
        if ref_id:
            ref_doc_id = f"keyvadi_user_{ref_id}"
            ref_data = await async_get_document(ref_doc_id)
            if ref_data:
                ref_data["referrals_count"] = ref_data.get("referrals_count", 0) + 1
                await async_set_document(ref_doc_id, ref_data)
                try:
                    await bot.send_message(int(ref_id), "🎉 **Tebrikler!** Bir arkadaşınız davetinizle KeyVadi'ye katıldı. Davet sayınız güncellendi!")
                except Exception:
                    pass
            else:
                ref_data = {
                    "referrals_count": 1,
                    "referred_by": "",
                    "id": int(ref_id)
                }
                await async_set_document(ref_doc_id, ref_data)

    lang = user_lang_helper.get_user_lang(user_id)
    if not lang:
        user_lang_helper.set_user_lang(user_id, 'tr')
        lang = 'tr'

    if prod_key_to_show:
        product = None
        cat_key_found = None
        for ck, cat in CATEGORIES.items():
            if prod_key_to_show in cat["products"]:
                product = cat["products"][prod_key_to_show]
                cat_key_found = ck
                break
        
        if product:
            t = TEXTS[lang]
            config = load_config() or {}
            links = config.get("shopier_links", SHOPIER_LINKS)
            shopier_url = links.get(prod_key_to_show, product.get("url", "https://www.shopier.com/keyvadi"))
            price = product['price']
            desc_text = (
                f"**{product['title']}**\n\n"
                f"**{t['price']}:** {price}\n\n"
                f"{t['product_footer']}"
            )
            cat_title = t["cat_title_mapping"].get(cat_key_found, CATEGORIES[cat_key_found]['title'])
            buttons = [
                [Button.url(t["buy_btn"], shopier_url)],
                [Button.inline(f"Geri: {cat_title}", f"cat_{cat_key_found}".encode())],
                [Button.inline(t["main_menu"], b"menu_main")]
            ]
            await event.respond(desc_text, buttons=buttons)
            return

    await show_main_menu(event, user_id)

@bot.on(events.NewMessage(pattern=r'/lang|/dil'))
@once_per_command("lang")
async def lang_cmd_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    await show_lang_selection(event)


@bot.on(events.NewMessage(pattern=r'(?i)^/(?:magaza|store|shop)(?:@\w+)?$'))
@once_per_command("magaza")
async def store_cmd_handler(event):
    welcome = (
        "🛍️ **KeyVadi Dijital Mağaza** ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Netflix 4K, Gemini AI Pro, CapCut Pro, Xbox Game Pass ve Minecraft gibi tüm popüler lisanslar **%70 indirimle** anında teslim!\n\n"
        "⚡ **7/24 Anında Otomatik Kod & Lisans Teslimatı**\n"
        "🎁 **Tam Süre Kesintisiz Değişim & Telafi Garantisi**\n"
        "💳 **3D Secure Güvenli Shopier Alışverişi**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👉 *Alışverişe başlamak veya indirimli ürünleri incelemek için aşağıdaki butonlara dokunun:*"
    )
    await event.respond(welcome, buttons=mini_app_markup("Mağazayı Aç"))


@bot.on(events.NewMessage(pattern=r'(?i)^/(?:urunler|katalog|products|kategoriler)(?:@\w+)?$'))
@once_per_command("urunler")
async def products_cmd_handler(event):
    t = TEXTS["tr"]
    text = (
        "📦 **KeyVadi Ürün Kataloğu & Kategoriler**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "İncelemek istediğiniz kategoriyi seçin veya mağazayı doğrudan açın:"
    )
    buttons = []
    cat_order = ["ai", "streaming", "design", "games", "coupons", "social", "accounts", "license"]
    for cat_key in cat_order:
        cat_info = CATEGORIES.get(cat_key)
        if cat_info and cat_info.get("products"):
            label = cat_info.get("title", cat_key)
            buttons.append([Button.inline(label, f"cat_{cat_key}".encode())])
    btn_app = Button.url("🛍️ Tüm Ürünleri Mini App'te Gör", KEYVADI_MINI_APP_URL)
    buttons.append([btn_app])
    buttons.append([Button.inline("↩️ Ana Menü", b"menu_main")])
    await event.respond(text, buttons=buttons)


@bot.on(events.CallbackQuery(pattern=r'lang_(\w+)'))
async def lang_select_callback(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    lang = event.data.decode('utf-8').replace("lang_", "")
    user_lang_helper.set_user_lang(user_id, lang)
    
    if lang == "tr":
        await event.answer("Dil Türkçe olarak ayarlandı.", alert=False)
    else:
        await event.answer("Language set to English.", alert=False)
        
    await show_main_menu(event, user_id, is_callback=True)


async def get_referral_details(user_id):
    user_data = await async_get_document(f"keyvadi_user_{user_id}") or {"referrals_count": 0}
    count = user_data.get("referrals_count", 0)
    
    if count >= 5:
        coupon_info = "🎁 **Tebrikler!** 5 referans barajını aştınız. Sizin için %15 indirim kuponunuz: **KEYVADI15**"
    else:
        coupon_info = f"🎁 5 arkadaşınızı davet ettiğinizde **%15 indirim kuponu** kazanırsınız! (Kalan: `{5 - count}` davet)"

    ref_link = f"https://t.me/KeyVadiSatisBot?start=ref_{user_id}"
    text = (
        "👥 **KeyVadi Davet & Kazan Sistemi**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Mevcut Davet Sayınız:** `{count} / 5`\n\n"
        f"{coupon_info}\n\n"
        "Arkadaşlarınızı davet edin, anında indirim kuponları kazanın! 🛍️\n\n"
        "🔗 **Sizin Özel Davet Linkiniz:**\n"
        f"`{ref_link}`\n\n"
        "*(Yukarıdaki linke tıklayarak kopyalayabilir veya butonla hemen paylaşabilirsiniz.)*"
    )
    import urllib.parse
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote('🔥 KeyVadi ile Netflix, Gemini Pro, Xbox Game Pass ve tüm lisansları %70 indirimle alabilirsiniz!')}"
    buttons = [
        [Button.url("🎁 Arkadaşınla Paylaş", share_url)],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    return text, buttons


@bot.on(events.CallbackQuery(data=b'menu_referral'))
async def menu_referral_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    text, buttons = await get_referral_details(event.sender_id)
    await safe_event_edit(event, text, buttons=buttons)


@bot.on(events.NewMessage(pattern=r"(?i)^/(?:referans|ref|davet)(?:@\w+)?$"))
@once_per_command("referans")
async def referans_cmd_handler(event):
    text, buttons = await get_referral_details(event.sender_id)
    await event.respond(text, buttons=buttons)


async def get_support_details(user_id):
    text = (
        "📞 **KeyVadi Canlı Destek & İletişim**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Değerli müşterimiz, 7/24 kesintisiz müşteri desteğimiz hizmetinizdedir.\n\n"
        "⚡ **Hangi konularda yardımcı olabiliriz?**\n"
        "• Shopier ödeme ve otomatik lisans teslimat sorgulama\n"
        "• Lisans aktivasyon ve kurulum yardımı\n"
        "• Garanti kapsamındaki anında değişim ve telafi işlemleri\n"
        "• Toplu lisans alımı ve kurumsal talepler\n\n"
        "👇 **Aşağıdaki butonları kullanarak hemen iletişime geçebilirsiniz:**"
    )
    buttons = [
        [Button.url("💬 Canlı Desteğe Yaz (@KeyVadiDestek)", "https://t.me/KeyVadiDestek")],
        [Button.url("📢 Resmi Topluluk Grubu", KEYVADI_GROUP_LINK)],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    return text, buttons


@bot.on(events.NewMessage(pattern=r"(?i)^/(?:destek|support|yardim|help)(?:@\w+)?$"))
@once_per_command("destek")
async def destek_cmd_handler(event):
    text, buttons = await get_support_details(event.sender_id)
    await event.respond(text, buttons=buttons)


@bot.on(events.CallbackQuery(data=b'menu_lang'))
async def menu_lang_callback(event):
    try:
        await event.answer()
    except Exception:
        pass
    await show_lang_selection(event, is_callback=True)


@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    await show_main_menu(event, user_id, is_callback=True)


@bot.on(events.CallbackQuery(data=b'menu_top7'))
async def menu_top7_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    
    text = (
        "**EN COK SATAN FIRSAT URUNLERI**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "KeyVadi guvencesiyle en cok tercih edilen dijital abonelik ve lisanslar:\n\n"
        "1. **Netflix 4K UHD** — 39,90 TL (Ortak) / 79,90 TL (Kisisel)\n"
        "2. **ChatGPT Plus** — 39,90 TL (Ortak Hesap)\n"
        "3. **Google Gemini Pro** — 59,90 TL (3 Ay) / 149,90 TL (18 Ay)\n"
        "4. **Canva Pro 1 Yil** — 49,90 TL (Kendi Hesabiniza)\n"
        "5. **CapCut Pro 30 Gun** — 40,00 TL (Ortak Hesap)\n"
        "6. **Duolingo Super 12 Ay** — 199,90 TL (Kisisel Aktivasyon)\n"
        "7. **Xbox Game Pass Ultimate** — 49,90 TL\n\n"
        "• 7/24 Aninda otomatik teslimat ve kesintisiz garanti.\n"
        "• Satin almak istediginiz urune asagidan tiklayabilirsiniz:"
    )
    buttons = [
        [Button.url("Netflix 4K Satin Al (79,90 TL)", "https://www.shopier.com/50665156")],
        [Button.url("Gemini Pro 18 Ay (149,90 TL)", "https://www.shopier.com/keyvadi/49362708")],
        [Button.url("ChatGPT Plus (39,90 TL)", "https://www.shopier.com/keyvadi/49467632")],
        [Button.url("Canva Pro 1 Yil (49,90 TL)", "https://www.shopier.com/keyvadi/49002145")],
        [Button.url("CapCut Pro 30 Gun (40,00 TL)", "https://www.shopier.com/keyvadi/49467632")],
        [Button.url("Magazayi Ac (Tum Urunler)", KEYVADI_MINI_APP_URL)],
        [Button.inline("Ana Menu", b"menu_main")]
    ]
    if isinstance(event, events.CallbackQuery.Event):
        await safe_event_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)


@bot.on(events.CallbackQuery(data=b'menu_daily_box'))
async def menu_daily_box_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    from daily_rewards import claim_daily_reward
    result = claim_daily_reward(user_id)
    
    if not result["eligible"]:
        rem_text = result["remaining_text"]
        last_code = result.get("last_code", "")
        code_info = f"\nSon kazandiginiz kod: `{last_code}`" if last_code else ""
        msg = (
            "**KEYVADI GUNLUK SANS KASASI**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Bugunku sans kasanizi zaten actiniz.\n\n"
            f"Yeni kasa acilisi icin kalan sure: **{rem_text}**{code_info}\n\n"
            "Kasanizi her 24 saatte bir acarak surpriz indirim kodlari kazanabilirsiniz."
        )
        buttons = [
            [Button.url("Magazaya Git", KEYVADI_MINI_APP_URL)],
            [Button.inline("Ana Menu", b"menu_main")]
        ]
    else:
        reward = result["reward"]
        if reward["win"]:
            code = reward["code"]
            msg = (
                "**KEYVADI GUNLUK SANS KASASI**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**TEBRIKLER! KASADAN ODUL KAZANDINIZ!**\n\n"
                f"Kazanilan Odul: **{reward['title']}**\n"
                f"Indirim Kodunuz: `{code}`\n\n"
                f"{reward['message']}\n\n"
                "Kodunuzu Shopier sepetinde uygulayarak aninda indirimli satin alabilirsiniz."
            )
            buttons = [
                [Button.url("Indirimle Alisveris Yap", KEYVADI_MINI_APP_URL)],
                [Button.inline("Kategorileri Gor", b"menu_categories")],
                [Button.inline("Ana Menu", b"menu_main")]
            ]
        else:
            msg = (
                "**KEYVADI GUNLUK SANS KASASI**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Bugun kasanizdan sansli kod cikmadi.\n\n"
                "Uzulmeyin! 24 saat sonra kasaniz yeniden acilacak. Sansinizi yarin tekrar deneyin.\n\n"
                "Mevcut indirimli urunlerimizi asagidaki butonlardan inceleyebilirsiniz."
            )
            buttons = [
                [Button.url("Magazayi Ac", KEYVADI_MINI_APP_URL)],
                [Button.inline("Ana Menu", b"menu_main")]
            ]
    await safe_event_edit(event, msg, buttons=buttons)


@bot.on(events.CallbackQuery(data=b'menu_faq'))
async def menu_faq_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    msg = (
        "**KEYVADI GUVENLIK VE GARANTI REHBERI**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Musterilerimizin en cok merak ettigi konular:\n\n"
        "1. **Nasil ve Ne Zaman Teslim Alirim?**\n"
        "Shopier uzerinden 3D Secure ile odemenizi tamamladiginiz anda lisans bilgileriniz ve kurulum rehberiniz otomatik olarak teslim edilir.\n\n"
        "2. **Garanti Sartlari Nelerdir?**\n"
        "Satin aldiginiz tum urunler taahhut edilen sure boyunca tam garanti kapsamindadir. Olası bir teknik sorunda aninda birebir telafi ve degisim yapilir.\n\n"
        "3. **Ortak ve Kisisel Hesap Farki Nedir?**\n"
        "Kisisel hesaplar yalnizca size ozel tanimlanir. Ortak hesaplar ise yuksek maliyetli premium servisleri (ChatGPT Plus, CapCut Pro) en uygun fiyatla kullanabilmeniz icin hazirlanmis profillerdir.\n\n"
        "4. **Sorun Yasarsam Kime Ulasabilirim?**\n"
        "Canli Destek butonuna basarak 7/24 yoneticilerimize dogrudan mesaj iletebilirsiniz."
    )
    buttons = [
        [Button.inline("Canli Destek Talebi", b"menu_support")],
        [Button.url("Shopier Magazamiz", "https://www.shopier.com/keyvadi")],
        [Button.inline("Ana Menu", b"menu_main")]
    ]
    await safe_event_edit(event, msg, buttons=buttons)


@bot.on(events.CallbackQuery(data=b'menu_search_prompt'))
async def menu_search_prompt_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    msg = (
        "**KEYVADI AKILLI URUN ARAMA**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Aradiginiz urune aninda ulasmak icin sohbet alanina istediginiz urunun adini yazabilirsiniz.\n\n"
        "Ornekler:\n"
        "• `/ara netflix`\n"
        "• `/ara chatgpt`\n"
        "• `/ara gemini`\n"
        "• `/ara canva`\n"
        "• veya dogrudan `netflix` yazip gonderebilirsiniz.\n\n"
        "Bot aninda urun kartini ve satin alma baglantisini karsiniza getirecektir."
    )
    buttons = [
        [Button.inline("Kategorileri Gor", b"menu_categories")],
        [Button.inline("Ana Menu", b"menu_main")]
    ]
    await safe_event_edit(event, msg, buttons=buttons)


@bot.on(events.CallbackQuery(data=b'menu_order_status'))
async def menu_order_status_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_VERIFY_PAYMENT_INFO"
    msg = (
        "**SIPARIS VE LISANS SORGULAMA**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Shopier uzerinden verdiginiz siparisin durumunu ogrenmek veya lisans bilgilerinizi almak icin:\n\n"
        "Lutfen Shopier **Siparis Numaranizi** (ornek: `987654321`) veya satin alirken kullandiginiz **E-posta Adresinizi** bu sohbete yazin.\n\n"
        "Alternatif olarak `/siparis <siparis_no>` seklinde de yazabilirsiniz.\n\n"
        "*(Iptal etmek icin /start yazabilirsiniz)*"
    )
    buttons = [
        [Button.inline("Canli Destek", b"menu_support")],
        [Button.inline("Ana Menu", b"menu_main")]
    ]
    await safe_event_edit(event, msg, buttons=buttons)


@bot.on(events.NewMessage(pattern=r"(?i)^/(?:ara|search|bul)(?:\s+(.+))?$"))
async def ara_cmd_handler(event):
    if not await async_claim_event(event, "keyvadi_sales"):
        return
    query = (event.pattern_match.group(1) or "").strip()
    if not query:
        msg = (
            "**KEYVADI URUN ARAMA**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Lutfen aramak istediginiz urun adini belirtin.\n\n"
            "Kullanim: `/ara <urun adi>`\n"
            "Ornek: `/ara netflix` veya `/ara canva`"
        )
        await event.respond(msg, buttons=[[Button.inline("Kategoriler", b"menu_categories")], [Button.inline("Ana Menu", b"menu_main")]])
        return

    full_catalog = load_sales_catalog("keyvadi")
    matched = match_sales_products(query, full_catalog, limit=4)
    if not matched:
        msg = (
            f"**Arama Sonucu: '{query}'**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Aradiginiz kriterlere uygun urun bulunamadi.\n\n"
            "Tum urunlerimizi gormek icin asagidaki butonlari kullanabilirsiniz:"
        )
        buttons = [
            [Button.url("Magazayi Ac (Mini App)", KEYVADI_MINI_APP_URL)],
            [Button.inline("Kategoriler", b"menu_categories")],
            [Button.inline("Canli Destek", b"menu_support")]
        ]
        await event.respond(msg, buttons=buttons)
        return

    if len(matched) == 1:
        p = matched[0]
        pid = p.get('id', '')
        bot_app_url = f"https://t.me/KeyVadiSatisBot/app?startapp=p_{pid}"
        direct_url = listing_url(p)
        msg = (
            f"**{p['title']}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Fiyat: **{p['price']}**\n\n"
            "• 7/24 Aninda otomatik teslimat\n"
            "• Tam sure kesintisiz telafi garantisi\n"
            "• 3D Secure guvenli Shopier odemesi"
        )
        buttons = [
            [Button.url("Shopier ile Guvenle Satin Al", direct_url)],
            [Button.url("Magazada Ac (Mini App)", bot_app_url)],
            [Button.inline("Ana Menu", b"menu_main")]
        ]
        await event.respond(msg, buttons=buttons)
    else:
        msg = f"**'{query}' icin bulunan urunler:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        buttons = []
        for i, p in enumerate(matched[:4]):
            msg += f"{i+1}. **{p['title']}** — {p['price']}\n"
            buttons.append([
                Button.url(f"Satin Al: {p['title'][:22]}", listing_url(p))
            ])
        buttons.append([Button.inline("Ana Menu", b"menu_main")])
        await event.respond(msg, buttons=buttons)


@bot.on(events.NewMessage(pattern=r"(?i)^/(?:siparis|order|sorgula)(?:\s+(.+))?$"))
async def siparis_cmd_handler(event):
    if not await async_claim_event(event, "keyvadi_sales"):
        return
    query = (event.pattern_match.group(1) or "").strip()
    if not query:
        user_id = event.sender_id
        user_states[user_id] = "AWAITING_VERIFY_PAYMENT_INFO"
        msg = (
            "**SIPARIS VE LISANS SORGULAMA**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Lutfen Shopier siparis numaranizi veya e-posta adresinizi girin.\n\n"
            "Kullanim: `/siparis <siparis_no>`\n"
            "Ornek: `/siparis 987654321`"
        )
        await event.respond(msg, buttons=[[Button.inline("Ana Menu", b"menu_main")]])
        return

    from order_fulfillment import fulfill_order_request
    fulfillment = await fulfill_order_request(
        query,
        tg_user_id=event.sender_id,
        tg_username=getattr(event.sender, "username", ""),
        brand_hint="keyvadi",
        client_or_bot=bot,
    )
    if fulfillment and fulfillment.get("message"):
        await event.respond(fulfillment["message"])
    else:
        await event.respond(
            "Girdiginiz siparis bilgisi sistemde eslesmedi. Lutfen bilgilerinizi kontrol edip tekrar deneyin veya Canli Destek ile iletisime gecin.",
            buttons=[[Button.inline("Canli Destek", b"menu_support")], [Button.inline("Ana Menu", b"menu_main")]]
        )


@bot.on(events.NewMessage(pattern=r"(?i)^/(?:firsat|firsatlar|deals)(?:@\w+)?$"))
@once_per_command("firsatlar")
async def firsatlar_cmd_handler(event):
    await menu_top7_handler(event)

@bot.on(events.CallbackQuery(data=b'menu_categories'))
async def menu_categories_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    
    t = TEXTS["tr"]
    text = (
        "📦 **KeyVadi Ürün Kategorileri**\n\n"
        "İncelemek istediğiniz kategoriyi seçin:"
    )
    buttons = []
    cat_order = ["ai", "streaming", "design", "games", "coupons", "social", "accounts", "license"]
    for cat_key in cat_order:
        cat_info = CATEGORIES.get(cat_key)
        if cat_info and cat_info.get("products"):
            label = cat_info.get("title", cat_key)
            buttons.append([Button.inline(label, f"cat_{cat_key}".encode())])
    buttons.append([Button.inline(t["main_menu"], b"menu_main")])
    await safe_event_edit(event, text, buttons=buttons)


# Admin update handler
@bot.on(events.NewMessage(pattern='/guncelle'))
@once_per_command("guncelle")
async def guncelle_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    
    if event.sender_id != admin_chat_id:
        return
        
    await event.respond("⏳ Shopier ürün listesi güncelleniyor, lütfen bekleyin...")
    
    loop = asyncio.get_event_loop()
    products = await loop.run_in_executor(None, refresh_live_catalog)
    
    if products:
        try:
            load_products_from_file_or_scrape()
            
            # Count products per category
            summary = "\n".join([f"- {cat['title']}: {len(cat['products'])} ürün" for cat_key, cat in CATEGORIES.items() if cat['products']])
            await event.respond(f"✅ Ürünler başarıyla güncellendi ve hafızaya yüklendi!\n\nToplam {len(products)} ürün bulundu:\n{summary}")
        except Exception as e:
            logger.error(f"Error saving updated products: {e}")
            await event.respond(f"❌ Güncelleme yapıldı fakat dosyaya yazılamadı: {e}")
    else:
        await event.respond("❌ Ürün listesi güncellenemedi (Shopier sayfasından veri çekilemedi).")

@bot.on(events.NewMessage(pattern=r"(?i)^/toplumesaj(?:\s+(.+))?$"))
@once_per_command("toplumesaj")
async def broadcast_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    if event.sender_id != admin_chat_id:
        return
        
    message_text = (event.pattern_match.group(1) or "").strip()
    if not message_text:
        await event.respond("⚠️ Kullanım: `/toplumesaj Duyuru mesajınız buraya...`")
        return
        
    await event.respond("⏳ **Toplu mesaj gönderimi başlatılıyor.**\n\nKullanıcı sayısına göre bu işlem vakit alabilir. İşlem bitene kadar lütfen yeni bir toplu mesaj başlatmayın.")
    
    doc = await async_get_document("keyvadi_users_data")
    users = doc.get("users", {}) if doc else {}
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

# ═══════════════════════════════════════════════════════════════
# Marketing Cards & Interactive Broadcast Notifications
# ═══════════════════════════════════════════════════════════════

_MARKETING_DRAFTS = {}
_STOCK_DRAFTS = {}


def _stock_draft(brand: str, raw_text: str):
    parsed = parse_stock_command(raw_text)
    if not parsed:
        return None, "⚠️ Kullanım: `/stok <ürün> <adet> [fiyat]`"
    query, count, custom_price = parsed
    product, matches = match_stock_product(brand, query)
    if not product:
        suggestions = ", ".join(str(item.get("title")) for item in matches[:3])
        suffix = f"\n\nBenzer ürünler: {suggestions}" if suggestions else ""
        return None, f"❌ Ürün katalogda bulunamadı.{suffix}"
    product = dict(product)
    product["url"] = purchase_url(product, brand, "stock_announcement")
    price = str(custom_price or product.get("price") or "Fiyat mağazada güncel")
    text = stock_card_text(product.get("title", query), count, price)
    item = build_announcement_item(
        brand,
        product,
        text=text,
        kind="stock",
        # Idempotency is intentionally product + stock count; changing the
        # optional display price must not resend the same stock alert.
        marker=str(count),
        recipients=load_subscribers(brand),
    )
    item.update({"stock_count": count, "price": price})
    return item, None


@bot.on(events.NewMessage(pattern=r"(?i)^/fiyatdusur(?:\s+(.+))?$"))
@once_per_command("fiyatdusur")
async def admin_fiyatdusur_handler(event):
    if not is_admin(event.sender_id):
        return

    raw_args = (event.pattern_match.group(1) or "").strip()
    parsed = parse_fiyatdusur_args(raw_args)
    if not parsed:
        await event.respond(
            "⚠️ **Kullanım:** `/fiyatdusur <ürün> <yeni_fiyat> <eski_fiyat> [toplu_fiyat]`\n\n"
            "💡 **Örnekler:**\n"
            "• `/fiyatdusur gemini 99 149`\n"
            "• `/fiyatdusur capcut 49 79 39`\n"
            "• `/fiyatdusur netflix 4k 69 119`"
        )
        return

    prod_query, new_p, old_p, bulk_p = parsed
    matched, score = match_product_from_text(prod_query)
    if matched:
        title = matched.get("title", prod_query.title())
        buy_url = matched.get("url") or KEYVADI_MINI_APP_URL
    else:
        title = prod_query.title()
        buy_url = KEYVADI_MINI_APP_URL

    card_text, card_buttons = build_price_drop_card(title, new_p, old_p, buy_url, bulk_p)

    import uuid
    draft_id = str(uuid.uuid4())[:8]
    _MARKETING_DRAFTS[draft_id] = {
        "text": card_text,
        "buttons": card_buttons,
        "created_at": time.time(),
        "title": title,
        "type": "Price Drop",
    }

    btn_confirm = Button.inline(
        "🚀 Tüm Müşterilere Gönder",
        f"confirm_card:{draft_id}".encode("utf-8")
    )
    btn_cancel = Button.inline(
        "❌ İptal Et",
        f"cancel_card:{draft_id}".encode("utf-8")
    )
    confirm_buttons = [[btn_confirm], [btn_cancel]]

    # 1. Send the exact card as live preview
    await event.respond(card_text, buttons=card_buttons, parse_mode="md")

    # 2. Send control confirmation panel
    await event.respond(
        f"📢 **Yukarıdaki 'Price Drop' kartı tüm müşterilere gönderilsin mi?**\n\n"
        f"• **Ürün:** {title}\n"
        f"• **Buton Linki:** {buy_url}\n\n"
        "Onaylamak için aşağıdaki butona tıklayın:",
        buttons=confirm_buttons,
        parse_mode="md",
    )


@bot.on(events.NewMessage(pattern=r"(?i)^/sonstok(?:\s+(.+))?$"))
@once_per_command("sonstok")
async def admin_sonstok_handler(event):
    if not is_admin(event.sender_id):
        return

    raw_args = (event.pattern_match.group(1) or "").strip()
    parsed = parse_sonstok_args(raw_args)
    if not parsed:
        await event.respond(
            "⚠️ **Kullanım:** `/sonstok <ürün> <kalan_adet> [fiyat]`\n\n"
            "💡 **Örnekler:**\n"
            "• `/sonstok capcut 2`\n"
            "• `/sonstok xbox 1 129`\n"
            "• `/sonstok netflix 3`"
        )
        return

    prod_query, count, custom_price = parsed
    matched, score = match_product_from_text(prod_query)
    if matched:
        title = matched.get("title", prod_query.title())
        buy_url = matched.get("url") or KEYVADI_MINI_APP_URL
        price = custom_price or matched.get("price", "49 TL")
    else:
        title = prod_query.title()
        buy_url = KEYVADI_MINI_APP_URL
        price = custom_price or "49 TL"

    card_text, card_buttons = build_selling_fast_card(title, price, count, buy_url)

    import uuid
    draft_id = str(uuid.uuid4())[:8]
    _MARKETING_DRAFTS[draft_id] = {
        "text": card_text,
        "buttons": card_buttons,
        "created_at": time.time(),
        "title": title,
        "type": "Selling Fast",
    }

    btn_confirm = Button.inline(
        "🚀 Tüm Müşterilere Gönder",
        f"confirm_card:{draft_id}".encode("utf-8")
    )
    btn_cancel = Button.inline(
        "❌ İptal Et",
        f"cancel_card:{draft_id}".encode("utf-8")
    )
    confirm_buttons = [[btn_confirm], [btn_cancel]]

    # 1. Send the exact card as live preview
    await event.respond(card_text, buttons=card_buttons, parse_mode="md")

    # 2. Send control confirmation panel
    await event.respond(
        f"📢 **Yukarıdaki 'Selling Fast' aciliyet kartı tüm müşterilere gönderilsin mi?**\n\n"
        f"• **Ürün:** {title}\n"
        f"• **Kalan Stok:** {count} adet\n"
        f"• **Buton Linki:** {buy_url}\n\n"
        "Onaylamak için aşağıdaki butona tıklayın:",
        buttons=confirm_buttons,
        parse_mode="md",
    )


@bot.on(events.NewMessage(pattern=r"(?i)^/stok(?:@\w+)?(?:\s+(.+))?$"))
@once_per_command("stok")
async def admin_stok_handler(event):
    if not is_admin(event.sender_id):
        return
    item, error = _stock_draft("keyvadi", event.text or "")
    if error:
        await event.respond(error, parse_mode="md")
        return
    draft_id = uuid.uuid4().hex[:10]
    _STOCK_DRAFTS[draft_id] = item
    buttons = [[Button.url(item.get("button_text", "🛒 Satın Al"), item["button_url"])]] if item.get("button_url") else []
    buttons.extend([
        [Button.inline("🚀 Abonelere Gönder", f"confirm_stock:{draft_id}".encode())],
        [Button.inline("❌ İptal", f"cancel_stock:{draft_id}".encode())],
    ])
    preview = f"{item['text']}\n\n👁️ **Önizleme:** Onaylarsanız yalnız KeyVadi bot abonelerine gönderilir."
    if str(item.get("image_url") or "").startswith("https://"):
        await event.respond(preview, file=item["image_url"], buttons=buttons, parse_mode="md")
    else:
        await event.respond(preview, buttons=buttons, parse_mode="md")


@bot.on(events.CallbackQuery(pattern=r"^confirm_stock:(.+)$"))
async def confirm_stock_callback_handler(event):
    if not is_admin(event.sender_id):
        await event.answer("Bu işlem yalnızca admin içindir.", alert=True)
        return
    draft_id = event.pattern_match.group(1).decode("utf-8")
    item = _STOCK_DRAFTS.pop(draft_id, None)
    if not item:
        await event.edit("⚠️ Bu stok duyurusu taslağı süresi dolmuş veya zaten gönderilmiş.")
        return
    queue = AnnouncementQueue("keyvadi", "stock")
    queued, created = queue.enqueue(item)
    if not created:
        await event.edit("ℹ️ Bu ürün ve stok adedi zaten duyuruldu.")
        return
    await event.edit("⏳ Stok duyurusu abonelere gönderiliyor...")

    async def send_one(user_id, current):
        return await send_telethon_item(bot, Button.url, user_id, current)

    result = await drain_queue(queue, send_one)
    await event.respond(
        f"✅ Stok duyurusu tamamlandı. Başarılı: {result['success']} · Başarısız: {result['failed']}"
    )


@bot.on(events.CallbackQuery(pattern=r"^cancel_stock:(.+)$"))
async def cancel_stock_callback_handler(event):
    if not is_admin(event.sender_id):
        await event.answer("Bu işlem yalnızca admin içindir.", alert=True)
        return
    draft_id = event.pattern_match.group(1).decode("utf-8")
    _STOCK_DRAFTS.pop(draft_id, None)
    await event.edit("❌ Stok duyurusu iptal edildi.")


@bot.on(events.NewMessage(pattern=r"(?i)^/kartonizle(?:\s+(.+))?$"))
@once_per_command("kartonizle")
async def admin_kartonizle_handler(event):
    if not is_admin(event.sender_id):
        return

    raw_args = (event.pattern_match.group(1) or "").strip()
    tokens = raw_args.split()
    if not tokens:
        await event.respond(
            "⚠️ **Kullanım:**\n"
            "• `/kartonizle fiyatdusur gemini 99 149`\n"
            "• `/kartonizle sonstok capcut 2`"
        )
        return

    sub = tokens[0].lower()
    rest = " ".join(tokens[1:])
    if sub in ("fiyatdusur", "pricedrop"):
        parsed = parse_fiyatdusur_args(rest)
        if not parsed:
            await event.respond("⚠️ Örnek: `/kartonizle fiyatdusur gemini 99 149`")
            return
        prod_query, new_p, old_p, bulk_p = parsed
        matched, _ = match_product_from_text(prod_query)
        title = matched.get("title", prod_query.title()) if matched else prod_query.title()
        buy_url = (matched.get("url") if matched else None) or KEYVADI_MINI_APP_URL
        card_text, card_buttons = build_price_drop_card(title, new_p, old_p, buy_url, bulk_p)
        await event.respond(card_text, buttons=card_buttons, parse_mode="md")
    elif sub in ("sonstok", "sellingfast"):
        parsed = parse_sonstok_args(rest)
        if not parsed:
            await event.respond("⚠️ Örnek: `/kartonizle sonstok capcut 2`")
            return
        prod_query, count, custom_price = parsed
        matched, _ = match_product_from_text(prod_query)
        title = matched.get("title", prod_query.title()) if matched else prod_query.title()
        buy_url = (matched.get("url") if matched else None) or KEYVADI_MINI_APP_URL
        price = custom_price or (matched.get("price", "49 TL") if matched else "49 TL")
        card_text, card_buttons = build_selling_fast_card(title, price, count, buy_url)
        await event.respond(card_text, buttons=card_buttons, parse_mode="md")
    else:
        await event.respond("⚠️ Desteklenen tipler: `fiyatdusur` veya `sonstok`")


@bot.on(events.CallbackQuery(pattern=r"^confirm_card:(.+)$"))
async def confirm_card_callback_handler(event):
    draft_id = event.pattern_match.group(1).decode("utf-8")
    if not is_admin(event.sender_id):
        await event.answer("Bu işlemi yalnızca admin yapabilir.", alert=True)
        return

    draft = _MARKETING_DRAFTS.pop(draft_id, None)
    if not draft:
        await event.edit("⚠️ Bu taslak süresi dolmuş veya zaten gönderilmiş.")
        return

    await event.edit("⏳ **Kart tüm müşterilere gönderiliyor...**\nLütfen işlem bitene kadar bekleyin.")

    user_ids = set()
    try:
        doc = await async_get_document("keyvadi_users_data")
        if doc and isinstance(doc.get("users"), dict):
            user_ids.update(doc["users"].keys())
    except Exception as e:
        logger.warning(f"Could not load keyvadi_users_data: {e}")

    if os.path.exists("welcomed_users.json"):
        try:
            with open("welcomed_users.json", "r", encoding="utf-8") as f_w:
                welcomed = json.load(f_w)
                if isinstance(welcomed, list):
                    user_ids.update(str(x) for x in welcomed if str(x).isdigit())
        except Exception:
            pass

    # Ensure admin itself is also in list for verification
    if str(admin_chat_id) not in user_ids:
        user_ids.add(str(admin_chat_id))

    success_count = 0
    fail_count = 0
    text = draft["text"]
    buttons = draft["buttons"]

    from telethon.errors import FloodWaitError
    for uid in user_ids:
        try:
            await bot.send_message(int(uid), text, buttons=buttons, parse_mode="md")
            success_count += 1
        except FloodWaitError as fe:
            await asyncio.sleep(fe.seconds + 1)
            try:
                await bot.send_message(int(uid), text, buttons=buttons, parse_mode="md")
                success_count += 1
            except Exception:
                fail_count += 1
        except Exception:
            fail_count += 1
        await asyncio.sleep(0.05)

    await event.respond(
        f"🎉 **Pazarlama Kartı Başarıyla Dağıtıldı!**\n\n"
        f"📦 **Ürün:** {draft.get('title')}\n"
        f"🏷️ **Tür:** {draft.get('type')}\n"
        f"✅ İletilen Müşteri: **{success_count}**\n"
        f"⚠️ Ulaşılamayan: **{fail_count}**\n\n"
        "Müşteriler kartı anında tıklayıp satın alabilir."
    )


@bot.on(events.CallbackQuery(pattern=r"^cancel_card:(.+)$"))
async def cancel_card_callback_handler(event):
    draft_id = event.pattern_match.group(1).decode("utf-8")
    _MARKETING_DRAFTS.pop(draft_id, None)
    await event.edit("❌ Kart yayını iptal edildi.")

@bot.on(events.NewMessage(pattern=r"(?i)^/(?:id|myid|kimim)$"))
@once_per_command("myid")
async def my_id_handler(event):
    sender = await event.get_sender()
    uname = f"@{sender.username}" if getattr(sender, "username", None) else "Belirtilmemiş"
    first = getattr(sender, "first_name", "") or ""
    last = getattr(sender, "last_name", "") or ""
    full_name = f"{first} {last}".strip() or "Kullanıcı"
    await event.respond(
        f"🆔 **Sizin Telegram Bilgileriniz:**\n\n"
        f"👤 **İsim:** {full_name}\n"
        f"💬 **Kullanıcı Adı:** {uname}\n"
        f"🔢 **Telegram ID:** `{event.sender_id}`\n\n"
        f"*(Admin olmak için bu ID numarasını sisteme tanımlatabilirsiniz.)*"
    )

@bot.on(events.NewMessage(pattern=r"(?i)^/kullanici(?:\s+(.+))?$"))
@once_per_command("kullanici")
async def admin_kullanici_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    if event.sender_id != admin_chat_id:
        return
    query = (event.pattern_match.group(1) or "").strip()
    if not query:
        await event.respond("⚠️ Kullanım: `/kullanici <Telegram_ID veya Kullanıcı_Adı>`\nÖrn: `/kullanici 5755476041`")
        return

    doc = await async_get_document("keyvadi_users_data")
    users = doc.get("users", {}) if doc else {}
    
    matched_uid = None
    target_user = None
    
    clean_q = query.lstrip("@").lower()
    if query in users:
        matched_uid = query
        target_user = users[query]
    else:
        for uid, udata in users.items():
            if str(uid) == clean_q or (udata.get("username") or "").lower() == clean_q or (udata.get("email") or "").lower() == clean_q:
                matched_uid = uid
                target_user = udata
                break
                
    if not target_user:
        await event.respond(f"❌ `{query}` kimliğine sahip kullanıcı KeyVadi veritabanında bulunamadı.")
        return
        
    full_name = f"{target_user.get('first_name', '')} {target_user.get('last_name', '')}".strip() or "Müşteri"
    uname = f"@{target_user.get('username')}" if target_user.get("username") else "Yok"
    bal = target_user.get("balance", 0.0)
    orders = target_user.get("orders", [])
    
    order_lines = []
    for i, o in enumerate(orders[-10:], 1):
        o_title = o.get("title") or "Ürün"
        o_price = o.get("price") or o.get("amount") or o.get("subtotal") or 0.0
        o_type = o.get("type") or "ürün_satın_alma"
        o_status = o.get("status") or "tamamlandı"
        o_code = o.get("license_key") or o.get("order_id") or ""
        order_lines.append(f"{i}. **{o_title}** — `₺{float(o_price):.2f}`\n   ↳ Tip: `{o_type}` | Durum: `{o_status}` | Kod/ID: `{o_code}`")
        
    orders_text = "\n".join(order_lines) if order_lines else "Henüz sipariş kaydı yok."
    
    resp = (
        f"👤 **KULLANICI DETAYI (KeyVadi)**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID:** `{matched_uid}`\n"
        f"👤 **İsim:** {full_name}\n"
        f"💬 **Kullanıcı Adı:** {uname}\n"
        f"💰 **Mevcut Bakiye:** `₺{float(bal):.2f}`\n"
        f"👥 **Referans:** {target_user.get('referrals_count', 0)} kişi (Davet eden: `{target_user.get('referred_by') or 'Yok'}`)\n\n"
        f"📦 **Son Sipariş / İşlem Geçmişi ({len(orders)} işlem):**\n"
        f"{orders_text}"
    )
    await event.respond(resp)

@bot.on(events.NewMessage(pattern=r"(?i)^/(?:siparisler|siparislerim|orders)(?:@\w+)?$"))
@once_per_command("siparisler")
async def siparisler_command_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    user_id = event.sender_id

    users = {}
    try:
        doc = await async_get_document("keyvadi_users_data")
        if doc and "users" in doc and isinstance(doc["users"], dict):
            users = doc["users"]
    except Exception as exc:
        print(f"[KeyVadi Bot] Firestore load orders error: {exc}")

    if not users:
        users_file = Path("miniapp/users_data.json")
        if users_file.exists():
            try:
                users = json.loads(users_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    if event.sender_id == admin_chat_id:
        all_orders = []
        for uid, udata in users.items():
            if isinstance(udata, dict):
                u_name = f"{udata.get('first_name', '')} {udata.get('last_name', '')}".strip() or udata.get('username') or f"#{uid}"
                for ord_item in udata.get("orders", []):
                    if isinstance(ord_item, dict):
                        all_orders.append({
                            "user_id": uid,
                            "customer": u_name,
                            **ord_item
                        })
                        
        all_orders.sort(key=lambda o: str(o.get("created_at") or o.get("date") or 0), reverse=True)
        
        if not all_orders:
            await event.respond("📦 Henüz sistemde kayıtlı bir sipariş bulunmuyor.")
            return
            
        lines = ["📦 **SON KEYVADI SİPARİŞLERİ (Admin Görünümü - Son 10 İşlem)**\n━━━━━━━━━━━━━━━━━━━━"]
        for i, o in enumerate(all_orders[:10], 1):
            title = o.get("title") or "Ürün"
            price = o.get("price") or o.get("amount") or o.get("subtotal") or 0.0
            cust = o.get("customer")
            uid = o.get("user_id")
            code = o.get("license_key") or o.get("order_id") or ""
            lines.append(f"{i}. **{title}** (`₺{float(price):.2f}`)\n   👤 Müşteri: {cust} (`{uid}`)\n   🔑 Kod/ID: `{code}`")
            
        await event.respond("\n\n".join(lines))
        return

    # Regular Customer View
    u = users.get(str(user_id), {})
    orders = u.get("orders", [])
    if not orders:
        text = (
            "📦 **Sipariş Geçmişiniz**\n\n"
            "Henüz kayıtlı bir siparişiniz bulunmamaktadır.\n\n"
            "KeyVadi mağazasından 7/24 anında teslimatla güvenle alışveriş yapabilirsiniz!"
        )
        buttons = [
            [Button.url("🛍️ KeyVadi Mağazasını Aç", KEYVADI_MINI_APP_URL)]
        ]
        await event.respond(text, buttons=buttons)
        return

    lines = ["📦 **Son Siparişleriniz:**\n"]
    for idx, o in enumerate(reversed(orders[-5:]), 1):
        title = o.get("title") or "Dijital Ürün"
        status = "✅ Teslim Edildi" if o.get("status") in ("delivered", "completed") or o.get("license_key") else "⏳ Hazırlanıyor"
        price = o.get("subtotal") or o.get("price") or o.get("amount") or 0
        lines.append(f"{idx}. **{title}** — `₺{price}` ({status})")
        if o.get("license_key"):
            lines.append(f"   🔑 Lisans Kodu: `{o.get('license_key')}`")
        elif o.get("status") == "pending_delivery":
            lines.append("   💬 *Manuel teslimat / Destek için @KeyVadiDestek ile iletişime geçin.*")
        lines.append("")

    buttons = [
        [Button.url("🛍️ Siparişlerimi Mini App'te Gör", KEYVADI_MINI_APP_URL)]
    ]
    await event.respond("\n".join(lines), buttons=buttons)

@bot.on(events.NewMessage(pattern=r"(?i)^/(?:bakiye|cuzdan|wallet)(?:@\w+)?$"))
@once_per_command("bakiye")
async def bakiye_command_handler(event):
    user_id = event.sender_id
    users = {}
    try:
        doc = await async_get_document("keyvadi_users_data")
        if doc and "users" in doc and isinstance(doc["users"], dict):
            users = doc["users"]
    except Exception as exc:
        print(f"[KeyVadi Bot] Firestore load balance error: {exc}")

    if not users:
        users_file = Path("miniapp/users_data.json")
        if users_file.exists():
            try:
                users = json.loads(users_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    u = users.get(str(user_id), {})
    balance = float(u.get("balance", 0.0))
    text = (
        f"💰 **KeyVadi Cüzdanınız**\n\n"
        f"Mevcut Bakiyeniz: `₺{balance:.2f}`\n\n"
        f"Shopier altyapısı ile anında bakiye yükleyebilir ve mağazadaki tüm ürünleri tek tıkla satın alabilirsiniz."
    )
    buttons = [
        [Button.url("⚡ Cüzdanı Aç & Bakiye Yükle", KEYVADI_MINI_APP_URL)]
    ]
    await event.respond(text, buttons=buttons)

@bot.on(events.NewMessage(pattern=r"(?i)^/bakiye_ekle\s+(\d+)\s+([\d\.,]+)$"))
@once_per_command("bakiye_ekle")
async def admin_bakiye_ekle_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    if event.sender_id != admin_chat_id:
        return
        
    target_uid = str(event.pattern_match.group(1)).strip()
    amount_str = event.pattern_match.group(2).replace(",", ".").strip()
    try:
        amount = float(amount_str)
    except ValueError:
        await event.respond("❌ Geçersiz tutar formatı.")
        return
        
    doc = await async_get_document("keyvadi_users_data")
    users = doc.get("users", {}) if doc else {}
    
    if target_uid not in users:
        users[target_uid] = {
            "id": int(target_uid),
            "username": "",
            "first_name": "Müşteri",
            "last_name": "",
            "balance": 0.0,
            "orders": []
        }
        
    old_bal = users[target_uid].get("balance", 0.0)
    new_bal = round(old_bal + amount, 2)
    users[target_uid]["balance"] = new_bal
    users[target_uid].setdefault("orders", []).append({
        "type": "admin_credit",
        "order_id": f"ADM-{int(time.time())}",
        "title": f"Yönetici Bakiye Yüklemesi (+₺{amount:.2f})",
        "amount": amount,
        "status": "completed",
        "created_at": int(time.time())
    })
    
    await async_set_document("keyvadi_users_data", {"users": users})
    await event.respond(f"✅ **Bakiye Başarıyla Eklendi!**\n\n👤 Kullanıcı ID: `{target_uid}`\n💰 Eklenen: `₺{amount:.2f}`\n💵 Yeni Bakiye: `₺{new_bal:.2f}`")
    
    try:
        await bot.send_message(
            int(target_uid),
            f"🎉 **Hesabınıza Bakiye Yüklendi!**\n\n💰 Yüklenen Tutar: `₺{amount:.2f}`\n💵 Güncel Bakiyeniz: `₺{new_bal:.2f}`\n\nMağazadan dilediğiniz ürünü hemen satın alabilirsiniz!",
            buttons=mini_app_markup("Mağazayı Aç")
        )
    except Exception:
        pass

# Category handler
@bot.on(events.CallbackQuery(pattern=r'cat_(\w+)'))
async def category_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]
    
    cat_key = event.data.decode('utf-8').replace("cat_", "")
    cat = CATEGORIES.get(cat_key)
    if not cat:
        err_msg = "Kategori bulunamadı!" if lang == "tr" else "Category not found!"
        await event.answer(err_msg, alert=True)
        return

    buttons = []
    for prod_key, prod in cat["products"].items():
        price = prod['price']
        if lang == "en":
            price = user_lang_helper.convert_price_to_usd(price)
            
        label = f"{prod['title']} — {price}"
        # Truncate label to 64 chars for Telegram button limit
        if len(label) > 64:
            label = label[:61] + "..."
        buttons.append([Button.inline(label, f"prod_{prod_key}".encode())])
    buttons.append([Button.inline(t["main_menu"], b"menu_main")])

    cat_title = t["cat_title_mapping"].get(cat_key, cat["title"])
    await safe_event_edit(event, f"**{cat_title}**\n\n{t['select_product']}", buttons=buttons)

# Product detail handler
@bot.on(events.CallbackQuery(pattern=r'prod_(\w+)'))
async def product_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]

    prod_key = event.data.decode('utf-8').replace("prod_", "")

    # Find product across all categories
    product = None
    cat_key_found = None
    for ck, cat in CATEGORIES.items():
        if prod_key in cat["products"]:
            product = cat["products"][prod_key]
            cat_key_found = ck
            break

    if not product:
        err_msg = "Ürün bulunamadı!" if lang == "tr" else "Product not found!"
        await event.answer(err_msg, alert=True)
        return

    record_lead_interaction(user_id, product.get('title'))

    config = load_config() or {}
    links = config.get("shopier_links", SHOPIER_LINKS)
    shopier_url = links.get(prod_key, product.get("url", "https://www.shopier.com/keyvadi"))

    price = product['price']
    if lang == "en":
        price = user_lang_helper.convert_price_to_usd(price)

    desc_text = (
        f"🌟 **{product['title']}**\n\n"
        f"💰 **{t['price']}:** {price}\n\n"
        f"{t['product_footer']}"
    )
    
    cat_title = t["cat_title_mapping"].get(cat_key_found, CATEGORIES[cat_key_found]['title'])
    buttons = [
        [Button.url(t["buy_btn"], shopier_url)],
        [Button.inline(f"↩️ {cat_title}", f"cat_{cat_key_found}".encode())],
        [Button.inline(t["main_menu"], b"menu_main")]
    ]
    await safe_event_edit(event, desc_text, buttons=buttons)

# Support Menu
@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"
    text, buttons = await get_support_details(user_id)
    await safe_event_edit(event, text, buttons=buttons)

PROCESSED_MESSAGE_EVENTS = set()

@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def message_handler(event):
    if getattr(event, 'out', False) or not getattr(event, 'is_private', False):
        return
    if event.text and event.text.startswith('/'):
        return
    claim_scope = "keyvadi_sales"
    event_key = (event.chat_id, getattr(event.message, 'id', None))
    if event_key in PROCESSED_MESSAGE_EVENTS:
        return
    PROCESSED_MESSAGE_EVENTS.add(event_key)
    if len(PROCESSED_MESSAGE_EVENTS) > 10000:
        PROCESSED_MESSAGE_EVENTS.clear()
    if not await async_claim_event(event, claim_scope):
        return
    user_id = event.sender_id
    sender = await event.get_sender()
    uname = getattr(sender, 'username', '') or ''
    fname = getattr(sender, 'first_name', '') or ''
    lname = getattr(sender, 'last_name', '') or ''
    msg_text = event.text or ''

    logger.info(f"📥 [KeyVadi] DM Alındı: GÖNDEREN={user_id} (@{uname}) MESAJ='{msg_text}'")
    print(f"📥 [KeyVadi] DM Alındı: GÖNDEREN={user_id} (@{uname}) MESAJ='{msg_text}'", flush=True)

    try:
        save_ticket_record(
            "KeyVadi",
            user_id,
            fname,
            lname,
            f"@{uname}" if uname else "Yok",
            msg_text,
        )
    except Exception as exc:
        logger.warning("Ticket kaydı hatası: %s", exc)

    dm_intent = record_dm_event(
        "KeyVadi", user_id, event.text or "",
        message_id=getattr(event.message, "id", None),
    )
    ban_data = await async_get_document(f"keyvadi_ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        logger.info(f"User {user_id} is banned, ignoring.")
        return

    from order_fulfillment import extract_order_id, extract_email, fulfill_order_request
    order_num = extract_order_id(event.text)
    email_addr = extract_email(event.text)
    is_awaiting = user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO"
    has_order_words = any(w in (event.text or "").lower() for w in (
        "sipariş", "siparis", "kod", "satın aldım", "satin aldim", "aldım", "aldim", "fatura"
    ))

    if is_awaiting or order_num or (has_order_words and (order_num or email_addr)):
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        query = order_num or email_addr or event.text.strip()
        fulfillment = await fulfill_order_request(
            query,
            tg_user_id=user_id,
            tg_username=getattr(event.sender, "username", ""),
            brand_hint="keyvadi",
            user_email=email_addr,
            client_or_bot=bot,
        )
        user_states[user_id] = None
        if fulfillment and fulfillment.get("message"):
            await event.respond(fulfillment["message"])
            return

    # The support bot is the only customer-DM owner.  Forward every customer
    # message, but greet a customer only once across restarts/deploys.
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    support_chat_id = config.get("support_chat_id", admin_chat_id)
    is_admin_context = event.sender_id == admin_chat_id or event.chat_id == support_chat_id
    matched_products = []
    if not is_admin_context and event.text and dm_intent == INTENT_SALES_LEAD:
        matched_products = match_sales_products(event.text, load_sales_catalog("keyvadi"), limit=6)

    if user_states.get(user_id) == "AWAITING_SUPPORT":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        config = load_config() or {}
        admin_chat_id = config.get("admin_id", ADMIN_ID)
        support_chat_id = config.get("support_chat_id", admin_chat_id)
        lang = user_lang_helper.get_user_lang(user_id) or "tr"
        t = TEXTS[lang]

        if not support_chat_id:
            await event.respond(t["support_inactive"])
            user_states[user_id] = None
            return

        user = await event.get_sender()
        username = f"@{user.username}" if user.username else "Yok"
        first_name = user.first_name or ""
        last_name = user.last_name or ""

        admin_msg = (
            f"📩 **[KeyVadi] Yeni Destek Talebi!**\n"
            f"👤 **Kullanıcı ID:** `{user_id}`\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\n"
            f"💬 **Kullanıcı Adı:** {username}\n"
            f"🌐 **Dil/Lang:** {lang.upper()}\n"
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        # Admin action buttons
        admin_buttons = [
            [
                Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"kv_adm_ban_{user_id}".encode())
            ]
        ]

        try:
            await bot.send_message(support_chat_id, admin_msg, buttons=admin_buttons)
            await event.respond(t["support_success"])
            save_ticket_to_file("KeyVadi", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    # ── Smart Product Matching for free-text messages ──
    # If user is NOT in any special state and NOT admin, try to match a product
    if event.text and not event.text.startswith('/'):
        # Hizli urun esleme (kullanici dogrudan netflix, canva, chatgpt gibi urun aradiginda)
        full_catalog = load_sales_catalog("keyvadi")
        quick_matches = match_sales_products(event.text.strip(), full_catalog, limit=3)
        if quick_matches and len(event.text.strip().split()) <= 4:
            if len(quick_matches) == 1:
                p = quick_matches[0]
                pid = p.get('id', '')
                bot_app_url = f"https://t.me/KeyVadiSatisBot/app?startapp=p_{pid}"
                direct_url = listing_url(p)
                p_msg = (
                    f"**{p['title']}**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Fiyat: **{p['price']}**\n\n"
                    "• 7/24 Aninda otomatik teslimat\n"
                    "• Tam sure kesintisiz garanti\n"
                    "• 3D Secure guvenli Shopier odemesi\n\n"
                    "Satin almak icin asagidaki baglantiya tiklayabilirsiniz:"
                )
                p_buttons = [
                    [Button.url("Shopier ile Guvenle Satin Al", direct_url)],
                    [Button.url("Magazada Ac (Mini App)", bot_app_url)],
                    [Button.inline("Ana Menu", b"menu_main")]
                ]
                await event.respond(p_msg, buttons=p_buttons)
                return
            else:
                p_msg = f"**'{event.text.strip()}' ile ilgili urunler:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                p_buttons = []
                for i, p_item in enumerate(quick_matches):
                    p_msg += f"{i+1}. **{p_item['title']}** — {p_item['price']}\n"
                    p_buttons.append([
                        Button.url(f"Satin Al: {p_item['title'][:22]}", listing_url(p_item))
                    ])
                p_buttons.append([Button.inline("Ana Menu", b"menu_main")])
                await event.respond(p_msg, buttons=p_buttons)
                return

        if (
            not is_admin_context
            and user_states.get(user_id) != "AWAITING_SUPPORT"
            and dm_intent != INTENT_SALES_LEAD
        ):
            await event.respond(
                greeting_for("KeyVadi"),
                buttons=mini_app_markup("KeyVadi Magazasini Ac"),
            )
            asyncio.create_task(
                forward_customer_message(
                    bot,
                    event,
                    support_chat_id,
                    "KeyVadi",
                    [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"kv_adm_ban_{user_id}".encode())]],
                )
            )
            record_event(
                "human_handoff", "KeyVadi", source="telegram_private",
                reason=dm_intent,
            )
            record_event("dm_reply_sent", "KeyVadi", source="telegram_private", product="generic_menu")
            return
        roadmap_reply = resolve_smart_roadmap_reply(event.text, "keyvadi")
        if roadmap_reply:
            reply_event_id = getattr(event.message, "id", None)
            if reply_event_id is not None and not await claim_support_event("KeyVadi", user_id, reply_event_id, "product_card"):
                record_event("duplicate_suppressed", "KeyVadi", source="telegram_private", reason="product_event_already_claimed")
                return
            await respond_with_floodwait(event, roadmap_reply)
            return
        full_catalog = load_sales_catalog("keyvadi")
        matched_products = matched_products or match_sales_products(event.text, full_catalog, limit=6)
        # A product name by itself (for example "Gemini" or "Perplexity") is
        # valid sales intent even when the customer does not say "fiyat/link".
        if not has_sales_intent(event.text) and not matched_products:
            logger.info("Ignoring non-sales message: %r", event.text)
            return
        if matched_products:
            reply_event_id = getattr(event.message, "id", None)
            if reply_event_id is None or not await claim_support_event("KeyVadi", user_id, reply_event_id, "product_card"):
                record_event("duplicate_suppressed", "KeyVadi", source="telegram_private", reason="product_event_already_claimed")
                return
            candidate_products = filter_products_outside_cooldown(user_id, matched_products)
            claimed_products = []
            for product in candidate_products:
                if await claim_product_reply(user_id, product):
                    claimed_products.append(product)
            if not claimed_products:
                logger.info("Suppressing duplicate product reply for user %s: %r", user_id, event.text)
                record_event(
                    "human_handoff", "KeyVadi", source="telegram_private",
                    product=matched_products[0].get("title", ""),
                    reason="duplicate_product_suppressed",
                )
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
            
            if len(matched_products) == 1:
                matched_product = matched_products[0]
                price = matched_product['price']
                if lang == "en":
                    price = user_lang_helper.convert_price_to_usd(price)
                
                product_msg = (
                    f"**{matched_product['title']}**\n"
                    f"**{t['price']}:** {price}"
                )
                pid = matched_product.get('id', '')
                bot_app_url = f"https://t.me/KeyVadiSatisBot/app?startapp=p_{pid}"
                direct_url = listing_url(matched_product)
                buttons = [
                    [Button.url("Magazada Ac", bot_app_url), Button.url("Direkt Al", direct_url)],
                    [Button.inline(t["support_btn"], b"menu_support")],
                ]
            else:
                product_msg = "**Uygun secenekler:**\n"
                buttons = []
                for i, p in enumerate(matched_products[:3]):
                    price = p['price']
                    if lang == "en":
                        price = user_lang_helper.convert_price_to_usd(price)
                    product_msg += f"{i+1}. **{p['title']}** — {price}\n"
                    p_id = p.get('id', '')
                    p_app_url = f"https://t.me/KeyVadiSatisBot/app?startapp=p_{p_id}"
                    p_direct_url = listing_url(p)
                    buttons.append([
                        Button.url(p['title'][:25], p_app_url),
                        Button.url("Direkt Al", p_direct_url)
                    ])
                buttons.append([Button.inline(t["support_btn"], b"menu_support")])
                
            try:
                await respond_with_floodwait(event, product_msg, buttons=buttons)
            except Exception:
                PROCESSED_MESSAGE_EVENTS.discard(event_key)
                await async_release_event_claim(event, claim_scope)
                await release_support_event("KeyVadi", user_id, reply_event_id, "product_card")
                for product in matched_products:
                    await release_product_claim(
                        "keyvadi", user_id,
                        str(product.get("id") or product.get("url") or product.get("title") or "product"),
                    )
                raise
            mark_product_reply_sent(user_id, matched_products)
            SUPPORT_SALES_CONTEXT[user_id] = {
                "product": dict(matched_products[0]),
                "expires_at": time.monotonic() + 15 * 60,
            }
            safe_conversation = conversation_key("KeyVadi", user_id)
            record_event("product_matched", "KeyVadi", source="telegram_private", product=matched_products[0].get('title', ''), product_count=len(matched_products), arm=arm, conversation_key=safe_conversation)
            for product in matched_products:
                record_event(
                    "purchase_cta_sent", "KeyVadi", source="telegram_private",
                    product=product.get('title', ''), product_id=product.get('id', ''),
                    cta_key=product.get('_cta_id', ''), arm=arm,
                    conversation_key=safe_conversation,
                )
            record_event("dm_reply_sent", "KeyVadi", source="telegram_private", product=matched_products[0].get('title', '') if matched_products else '')
            logger.info(f"Smart match for user {user_id}: '{event.text}' -> matched products successfully.")
            return
        elif SUPPORT_SALES_CONTEXT.get(user_id, {}).get("expires_at", 0) > time.monotonic():
            product = SUPPORT_SALES_CONTEXT[user_id]["product"]
            record_event("human_handoff", "KeyVadi", source="telegram_private", product=product.get("title", ""), reason="unverified_product_fact")
            logger.info("Product follow-up handed to panel without an automatic reply for user %s", user_id)
            return
        elif has_sales_intent(event.text):
            if not await claim_auto_reply_once("KeyVadi", user_id, "clarification", event.chat_id):
                logger.info("Suppressing repeated clarification reply for user %s", user_id)
                record_event("human_handoff", "KeyVadi", source="telegram_private", reason="clarification_already_sent")
                return
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            await event.respond(
                "Aradığınız ürünü doğru bulabilmem için ürün adını ve varsa kişisel/ortak ya da süre tercihinizi yazar mısınız?",
                buttons=[[Button.inline(t["support_btn"], b"menu_support")]],
            )
            record_event("human_handoff", "KeyVadi", source="telegram_private", reason="no_product_match")
            record_event("dm_reply_sent", "KeyVadi", source="telegram_private", product="clarification")
            return

    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    support_chat_id = config.get("support_chat_id", admin_chat_id)

    # Allow replies from admin in private chat OR in the support chat group
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

@bot.on(events.CallbackQuery(pattern=r'kv_adm_ban_(\d+)'))
async def kv_admin_ban_user_callback(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    if event.sender_id != admin_chat_id:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    target_user_id = int(event.pattern_match.group(1))
    
    ban_doc_id = f"keyvadi_ban_{target_user_id}"
    await async_set_document(ban_doc_id, {"banned": True, "id": target_user_id})
    
    await event.answer("🚫 Kullanıcı engellendi.", alert=True)
    original_text = event.message.text
    await safe_event_edit(event, f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")


async def _send_pending_stock(user_id, item):
    return await send_telethon_item(bot, Button.url, user_id, item)

if __name__ == '__main__':
    import asyncio
    from telethon.errors import FloodWaitError
    
    logger.info("Loading KeyVadi products cache...")
    refresh_live_catalog()
    load_products_from_file_or_scrape()
    
    async def start_with_retry():
        global BOT_USER_ID, PROFILE_CONFIGURED
        write_bot_status(
            "keyvadi", state="connecting", telegram_ready=False, token=BOT_TOKEN
        )
        while True:
            try:
                logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
                await bot.start(bot_token=BOT_TOKEN)
                me = await bot.get_me()
                BOT_USER_ID = me.id
                write_bot_status(
                    "keyvadi",
                    state="ready",
                    telegram_ready=True,
                    token=BOT_TOKEN,
                    bot_username=getattr(me, "username", None),
                    connected=True,
                )
                if not PROFILE_CONFIGURED:
                    if os.environ.get("KEYVADI_CONFIGURE_PROFILE", "0").strip().lower() in {"1", "true", "yes"}:
                        try:
                            await asyncio.to_thread(configure_bot_profile)
                            PROFILE_CONFIGURED = True
                            logger.info("KeyVadi commands and Mini App menu configured")
                        except Exception as profile_error:
                            logger.warning("KeyVadi profile configuration warning: %s", profile_error)
                    else:
                        PROFILE_CONFIGURED = True
                        logger.info("KeyVadi profile configuration skipped; canonical Mini App URL is %s", KEYVADI_MINI_APP_URL)
                logger.info(f"KeyVadi Sales Bot started successfully! Bot User ID: {BOT_USER_ID}")
                await drain_queue(
                    AnnouncementQueue("keyvadi", "stock"),
                    _send_pending_stock,
                )
                asyncio.create_task(run_retargeting_loop(bot))
                await bot.run_until_disconnected()
            except FloodWaitError as e:
                write_bot_status(
                    "keyvadi", state="retrying", telegram_ready=False,
                    token=BOT_TOKEN, last_error=type(e).__name__,
                )
                logger.warning(f"FloodWait: Telegram {e.seconds} saniye beklememizi istiyor. Bekleniyor...")
                await asyncio.sleep(e.seconds + 5)
                logger.info("FloodWait süresi bitti, tekrar deneniyor...")
            except Exception as e:
                if invalid_token_error(e):
                    write_bot_status(
                        "keyvadi", state="invalid_token", telegram_ready=False,
                        token=BOT_TOKEN, last_error=type(e).__name__,
                    )
                    logger.error("Bot token is invalid or expired; waiting for a replacement token.")
                    return
                write_bot_status(
                    "keyvadi", state="error", telegram_ready=False,
                    token=BOT_TOKEN, last_error=type(e).__name__,
                )
                logger.error(f"Bot başlatma hatası: {e}")
                await asyncio.sleep(30)
    
    bot.loop.run_until_complete(start_with_retry())
