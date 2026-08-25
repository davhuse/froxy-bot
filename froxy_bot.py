import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
import time
from functools import wraps
from telethon import TelegramClient, events, Button
from telethon.errors import MessageNotModifiedError
from telethon.sessions import StringSession
from telethon.tl.types import KeyboardButtonRow, KeyboardButtonWebView, ReplyInlineMarkup
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
)

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
MESSAGE_BURST_DEBOUNCE_SECONDS = 1.5
LATEST_USER_MESSAGE_IDS = {}

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
        message_id = getattr(event.message, 'id', None)
        text = getattr(event, 'text', None)
        if user_id and message_id and text and not text.startswith('/'):
            LATEST_USER_MESSAGE_IDS[user_id] = message_id
            await asyncio.sleep(MESSAGE_BURST_DEBOUNCE_SECONDS)
            if LATEST_USER_MESSAGE_IDS.get(user_id) != message_id:
                logger.info("Ignoring superseded burst message for user %s (message %s)", user_id, message_id)
                return
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
    os.environ.get("KEYVADI_SUPPORT_BOT_TOKEN") or
    os.environ.get("KEYVADI_BOT_TOKEN") or
    config.get("support_bot_token") or
    config.get("keyvadi_bot_token") or
    ""
).strip()
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", config.get("admin_id", 0)) or 0)
BOT_USER_ID = None
PROFILE_CONFIGURED = False
SHOPIER_LINKS = config.get("shopier_links", {})
_PUBLIC_BASE_URL = (
    os.environ.get("RENDER_EXTERNAL_URL")
    or "https://froxy-bot-live.onrender.com"
).strip().rstrip("/")
KEYVADI_MINI_APP_URL = os.environ.get(
    "KEYVADI_MINI_APP_URL",
    f"{_PUBLIC_BASE_URL}/keyvadi/",
).strip().rstrip("/") + "/"

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("KEYVADI_SUPPORT_BOT_TOKEN is not configured. Exiting.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient(StringSession(), API_ID, API_HASH)

BOT_COMMANDS = [
    ("start", "KeyVadi ana menüyü aç"),
    ("magaza", "KeyVadi mağazasını aç"),
    ("urunler", "Ürün kataloğunu görüntüle"),
    ("destek", "Destek talebi oluştur"),
    ("referans", "Referans bağlantını görüntüle"),
    ("dil", "Dil seçimini değiştir"),
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
    """Configure the KeyVadi command list and persistent Mini App entry."""
    _bot_api_call("setMyCommands", {
        "commands": [
            {"command": command, "description": description}
            for command, description in BOT_COMMANDS
        ]
    })
    _bot_api_call("setChatMenuButton", {
        "menu_button": {
            "type": "web_app",
            "text": "🛍 Mağazayı Aç",
            "web_app": {"url": KEYVADI_MINI_APP_URL},
        }
    })
    _bot_api_call("setMyName", {"name": "KeyVadi"})
    _bot_api_call("setMyDescription", {
        "description": "Dijital ürünler, lisanslar, abonelikler ve güvenli Shopier alışverişi için KeyVadi mağazası."
    })
    _bot_api_call("setMyShortDescription", {
        "short_description": "Dijital ürün mağazası · Shopier · Destek"
    })


def mini_app_markup(label="Mağazayı Aç"):
    return ReplyInlineMarkup(rows=[KeyboardButtonRow(buttons=[
        KeyboardButtonWebView(text=f"🛍 {label}", url=KEYVADI_MINI_APP_URL)
    ])])

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
    {"id": "49099014", "title": "Netflix 4K UHD Ortak Profil", "price": "39.99 TL", "url": "https://www.shopier.com/49099014"},
    {"id": "49099013", "title": "Steam 200 Dolar Random Key", "price": "30.00 TL", "url": "https://www.shopier.com/49099013"},
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
    
    query_words = _get_words(msg_clean)
    
    # Brand keywords — query must contain at least one to trigger matching
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "creative",
        "4k", "uhd", "game", "lisans", "microsoft",
        "tradingview", "nordvpn", "vpn", "kaspersky", "envato", "freepik",
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot", "discord"
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
            "netflix", "prime video", "hbo", "crunchyroll", "exxen", "blutv",
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
            "akaryakıt", "puan",
        ]):
            cat_key = "coupons"
        elif any(k in t for k in [
            "steam", "xbox", "game pass", "gamepass", "fc26", "zula", "oyun",
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
            "⚡ **KeyVadi Satış Paneline Hoş Geldiniz!**\n\n"
            "Premium yapay zeka hesapları, lisanslar, onaylı mobil hesaplar ve özel fırsatlar en uygun fiyatlarla!\n\n"
            "Lütfen yapmak istediğiniz işlemi seçin 👇"
        ),
        "support_btn": "📞 Canlı Destek & İletişim",
        "lang_btn": "🌐 Dil Seçimi / Language",
        "main_menu": "↩️ Ana Menü",
        "cat_title_mapping": {
            "ai": "🌟 Yapay Zeka (AI) Çözümleri",
            "streaming": "📺 Dizi, Film & Müzik",
            "design": "🎨 Tasarım, Eğitim & Verimlilik",
            "social": "💬 Discord & Sosyal Platformlar",
            "coupons": "🎟️ Kupon, İndirim & Bakiye",
            "games": "🎮 Oyun & Game Pass",
            "accounts": "📱 Telegram, WhatsApp & Mobil Hesaplar",
            "license": "🔑 Windows, Office & Diğer Lisanslar"
        },
        "select_product": "Detaylarını görmek ve satın almak istediğiniz ürünü seçin:",
        "price": "Fiyat",
        "product_footer": "✅ Teslimat türü ürün detayında · 7/24 destek · Güvenli ödeme\n\nSatın almak için aşağıdaki butona tıklayın. Teslimat yöntemi ürün bilgisine göre uygulanır.",
        "buy_btn": "💳 Shopier ile Güvenli Satın Al",
        "support_title": "📞 **Destek Talebi & Sipariş Verme**",
        "support_desc": "Satın almak istediğiniz ürün, sipariş sorunu veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\nMesajınız doğrudan admin ekibimize iletilecektir. En kısa sürede yanıt alacaksınız.",
        "cancel": "↩️ Vazgeç ve İptal Et",
        "support_success": "✅ Mesajınız ekibimize iletildi. En kısa sürede yanıt alacaksınız.",
        "support_fail": "⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.",
        "support_inactive": "⚠️ Üzgünüz, şu anda destek sistemi aktif değil (Admin ID tanımlanmamış). Lütfen daha sonra deneyin.",
        "reply_prefix": "📨 **KeyVadi Destek Ekibinden Cevap:**\n\n",
        "choose_lang": "Lütfen dilinizi seçin / Please choose your language:"
    }
}

# Main Menu Helper — Streamlined Mini App First Experience
async def show_lang_selection(event, is_callback=False):
    text = (
        "🇹🇷 **Lütfen dil seçin:**\n"
        "🇬🇧 **Please select your language:**"
    )
    buttons = [
        [Button.inline("🇹🇷 Türkçe", b"lang_tr"), Button.inline("🇬🇧 English", b"lang_en")]
    ]
    if is_callback:
        await safe_event_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)

async def show_main_menu(event, user_id, is_callback=False):
    welcome = (
        "🎮 **KEYVADI PRO — Dijital E-Pin & Oyun Mağazası** ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👋 **KeyVadi Dünyasına Hoş Geldiniz!**\n\n"
        "YouTube Premium, Canva Pro, Netflix 4K, ChatGPT Plus, Steam VIP Random Key, FC26, Xbox Game Pass ve tüm orijinal lisanslar %70 indirimle burada!\n\n"
        "💎 **Öne Çıkan Ayrıcalıklar:**\n"
        "• ⚡ 7/24 Anında Otomatik Kod & Lisans Teslimatı\n"
        "• 💳 3D Secure ile Güvenli Kartla Satın Alma & Bakiye Yükleme\n"
        "• 🎁 Arkadaşını Davet Et, Harcamalarından %10 Nakit Kazan!\n\n"
        "👇 **Alışverişe başlamak ve mağazayı açmak için aşağıdaki butona tıklayın:**"
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
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if not await async_claim_event(event, "keyvadi_sales"):
        return
    user_id = event.sender_id
    
    ban_data = await async_get_document(f"keyvadi_ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        await event.respond("⚠️ **Hesabınız askıya alınmıştır.** İletişime geçmek için yöneticinize başvurun.")
        return
        
    user_states[user_id] = None
    
    message_text = event.message.message or ""
    ref_id = None
    if " " in message_text:
        parts = message_text.split(" ", 1)
        param = parts[1].strip()
        if param.startswith("ref_"):
            ref_id = param.replace("ref_", "")
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
        await show_lang_selection(event)
    else:
        await show_main_menu(event, user_id)

@bot.on(events.NewMessage(pattern=r'/lang|/dil'))
@once_per_command("lang")
async def lang_cmd_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    await show_lang_selection(event)


@bot.on(events.NewMessage(pattern=r'(?i)^/magaza$'))
@once_per_command("magaza")
async def store_cmd_handler(event):
    await event.respond("KeyVadi mağazası", buttons=mini_app_markup())


@bot.on(events.NewMessage(pattern=r'(?i)^/urunler$'))
@once_per_command("urunler")
async def products_cmd_handler(event):
    await event.respond("Ürün kataloğunu açmak için aşağıdaki düğmeye dokunun.", buttons=mini_app_markup("Ürünleri Aç"))

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

@bot.on(events.CallbackQuery(data=b'menu_referral'))
async def menu_referral_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    user_data = await async_get_document(f"keyvadi_user_{user_id}") or {"referrals_count": 0}
    count = user_data.get("referrals_count", 0)
    
    coupon_info = ""
    if count >= 5:
        coupon_info = "🎁 **Tebrikler!** 5 referans barajını aştınız. Sizin için %15 indirim kuponunuz: **KEYVADI15**"
    else:
        coupon_info = f"🎁 5 arkadaşınızı davet ettiğinizde **%15 indirim kuponu** kazanırsınız! (Kalan: `{5 - count}` davet)"

    text = (
        "👥 **KeyVadi Davet & Kazan Sistemi**\n\n"
        f"👥 **Mevcut Davet Sayınız:** `{count} / 5`\n\n"
        f"{coupon_info}\n\n"
        "Arkadaşlarınızı davet edin, indirim kuponları kazanın! 🛍️\n\n"
        "🔗 **Sizin Davet Linkiniz:**\n"
        f"`https://t.me/KeyVadiSatisBot?start=ref_{user_id}`\n\n"
        "*(Yukarıdaki linke tıklayarak kopyalayabilir ve arkadaşlarınıza gönderebilirsiniz.)*"
    )
    buttons = [
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

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

@bot.on(events.NewMessage(pattern=r"(?i)^/siparisler$"))
@once_per_command("siparisler")
async def admin_siparisler_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    if event.sender_id != admin_chat_id:
        return

    doc = await async_get_document("keyvadi_users_data")
    users = doc.get("users", {}) if doc else {}
    
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
        
    lines = ["📦 **SON KEYVADI SİPARİŞLERİ (Son 10 İşlem)**\n━━━━━━━━━━━━━━━━━━━━"]
    for i, o in enumerate(all_orders[:10], 1):
        title = o.get("title") or "Ürün"
        price = o.get("price") or o.get("amount") or o.get("subtotal") or 0.0
        cust = o.get("customer")
        uid = o.get("user_id")
        code = o.get("license_key") or o.get("order_id") or ""
        lines.append(f"{i}. **{title}** (`₺{float(price):.2f}`)\n   👤 Müşteri: {cust} (`{uid}`)\n   🔑 Kod/ID: `{code}`")
        
    await event.respond("\n\n".join(lines))

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
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]
    
    user_states[user_id] = "AWAITING_SUPPORT"

    buttons = [
        [Button.inline(t["cancel"], b"menu_main")]
    ]
    await safe_event_edit(event, f"{t['support_title']}\n\n{t['support_desc']}", buttons=buttons)

PROCESSED_MESSAGE_EVENTS = set()

@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def message_handler(event):
    if getattr(event, 'out', False):
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

    if user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return
            
        input_val = event.text.strip().lower()
        if "@" in input_val:
            doc_id = "order_email_" + input_val.replace("@", "_").replace(".", "_")
        else:
            doc_id = "order_phone_" + input_val.replace("+", "").replace(" ", "")
            
        orders_doc = await async_get_document(doc_id)
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
        
        # Use global license delivery system
        alloc = allocate_license(prod_name, brand="keyvadi")
        license_key = alloc.get("license_key")
        
        # Mark order as claimed in local shopier email doc
        orders[unclaimed_idx]["claimed"] = True
        await async_set_document(doc_id, orders_doc)

        # Save order to keyvadi_users_data so it shows in /siparisler
        user_orders_doc = await async_get_document("keyvadi_users_data")
        u_data = user_orders_doc.get("users", {}) if user_orders_doc else {}
        str_uid = str(user_id)
        if str_uid not in u_data:
            u_data[str_uid] = {
                "id": user_id, "username": getattr(event.sender, "username", ""),
                "first_name": getattr(event.sender, "first_name", "Musteri"),
                "balance": 0.0, "orders": []
            }
        u_data[str_uid].setdefault("orders", []).append({
            "order_id": unclaimed_order.get("order_id"),
            "product_name": unclaimed_order.get("product_name"),
            "title": unclaimed_order.get("product_name"),
            "price": unclaimed_order.get("amount"),
            "status": alloc.get("status", "delivered" if license_key else "pending_delivery"),
            "license_key": license_key,
            "created_at": unclaimed_order.get("timestamp")
        })
        await async_set_document("keyvadi_users_data", {"users": u_data})
        
        if license_key:
            await event.respond(
                f"✅ **Ödemeniz Başarıyla Doğrulandı!**\n\n"
                f"📦 **Satın Alınan Ürün:** {unclaimed_order.get('product_name')}\n"
                f"🔑 **Lisans Anahtarınız:**\n"
                f"`{license_key}`\n\n"
                f"*(Lisans anahtarını kopyalamak için üzerine tıklayabilirsiniz.)*\n\n"
                f"KeyVadi'yi tercih ettiğiniz için teşekkür ederiz! 😊"
            )
            
            # Notify admin
            try:
                config = load_config() or {}
                admin_chat_id = config.get("admin_id", ADMIN_ID)
                support_chat_id = config.get("support_chat_id", admin_chat_id)
                if support_chat_id:
                    await bot.send_message(
                        support_chat_id, 
                        f"🎉 **KeyVadi Otomatik Satış Bildirimi!**\n"
                        f"👤 **Kullanıcı:** `{user_id}`\n"
                        f"📦 **Ürün:** {unclaimed_order.get('product_name')}\n"
                        f"🔑 **Lisans Kodu:** `{license_key}` (Otomatik teslim edildi)\n"
                        f"💰 **Tutar:** {unclaimed_order.get('amount')} ₺\n"
                        f"🛍️ **Shopier Sipariş ID:** `{unclaimed_order.get('order_id')}`\n\n"
                        f"*(Kullanıcıya lisans teslimat bilgileri bot üzerinden iletilmiştir.)*"
                    )
            except Exception:
                pass
        else:
            await event.respond(
                f"✅ **Ödemeniz Başarıyla Doğrulandı!**\n\n"
                f"📦 **Satın Alınan Ürün:** {unclaimed_order.get('product_name')}\n\n"
                f"⚠️ **Stok Uyarısı:** Satın aldığınız ürünün lisans anahtarı stokta kalmamıştır. "
                f"Yöneticiye bildirim gönderildi, en kısa sürede lisansınız Telegram üzerinden size iletilecektir."
            )
            
            # Notify admin about stock warning
            try:
                config = load_config() or {}
                admin_chat_id = config.get("admin_id", ADMIN_ID)
                if admin_chat_id:
                    await bot.send_message(
                        admin_chat_id, 
                        f"⚠️ **ACİL STOK UYARISI!**\n"
                        f"Kullanıcı `{user_id}` Shopier'den **{unclaimed_order.get('product_name')}** satın aldı ancak stokta lisans kodu yok!\n"
                        f"Lütfen en kısa sürede manuel teslimat yapın.\n"
                        f"📧 **Müşteri E-posta/Telefon:** {input_val}"
                    )
            except Exception:
                pass
                
        user_states[user_id] = None
        return

    # The support bot is the only customer-DM owner.  Forward every customer
    # message, but greet a customer only once across restarts/deploys.
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    support_chat_id = config.get("support_chat_id", admin_chat_id)
    is_admin_context = event.sender_id == admin_chat_id or event.chat_id == support_chat_id
    matched_products = []
    if not is_admin_context and event.text and dm_intent == INTENT_SALES_LEAD:
        matched_products = match_sales_products(event.text, load_sales_catalog("keyvadi"), limit=3)

    if one_time_mode_enabled() and not is_admin_context:
        buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"kv_adm_ban_{user_id}".encode())]]
        if not matched_products and await forward_customer_message(bot, event, support_chat_id, "KeyVadi", buttons):
            record_event("dm_manual_forwarded", "KeyVadi", source="telegram_private")
            if await claim_first_greeting("keyvadi", user_id):
                await event.respond(greeting_for("KeyVadi"))
                record_event("dm_greeting_sent", "KeyVadi", source="telegram_private")
        # A support-form message has already been forwarded above. Ordinary DMs
        # must continue so the product matcher can return the Shopier URL.
        if user_states.get(user_id) == "AWAITING_SUPPORT":
            user_states[user_id] = None
            return

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
        if not is_admin_context and dm_intent != INTENT_SALES_LEAD:
            record_event(
                "human_handoff", "KeyVadi", source="telegram_private",
                reason=dm_intent,
            )
            return
        full_catalog = load_sales_catalog("keyvadi")
        matched_products = matched_products or match_sales_products(event.text, full_catalog, limit=3)
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
                    f"📌 **{matched_product['title']}**\n"
                    f"💰 **{t['price']}:** {price}"
                )
                pid = matched_product.get('id', '')
                bot_app_url = f"https://t.me/KeyVadiSatisBot/app?startapp=p_{pid}"
                direct_url = listing_url(matched_product)
                buttons = [
                    [Button.url("🛍️ Mağazada Aç", bot_app_url), Button.url("💳 Direkt Al", direct_url)],
                    [Button.inline(t["support_btn"], b"menu_support")],
                ]
            else:
                product_msg = "🔍 **Uygun seçenekler:**\n"
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
                        Button.url(f"🛍️ {p['title'][:20]}", p_app_url),
                        Button.url("💳 Direkt Al", p_direct_url)
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

if __name__ == '__main__':
    import asyncio
    from telethon.errors import FloodWaitError
    
    logger.info("Loading KeyVadi products cache...")
    refresh_live_catalog()
    load_products_from_file_or_scrape()
    
    async def start_with_retry():
        global BOT_USER_ID, PROFILE_CONFIGURED
        while True:
            try:
                logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
                await bot.start(bot_token=BOT_TOKEN)
                me = await bot.get_me()
                BOT_USER_ID = me.id
                if not PROFILE_CONFIGURED:
                    try:
                        await asyncio.to_thread(configure_bot_profile)
                        PROFILE_CONFIGURED = True
                        logger.info("KeyVadi commands and Mini App menu configured")
                    except Exception as profile_error:
                        logger.warning("KeyVadi profile configuration warning: %s", profile_error)
                logger.info(f"KeyVadi Sales Bot started successfully! Bot User ID: {BOT_USER_ID}")
                await bot.run_until_disconnected()
            except FloodWaitError as e:
                logger.warning(f"FloodWait: Telegram {e.seconds} saniye beklememizi istiyor. Bekleniyor...")
                await asyncio.sleep(e.seconds + 5)
                logger.info("FloodWait süresi bitti, tekrar deneniyor...")
            except Exception as e:
                logger.error(f"Bot başlatma hatası: {e}")
                await asyncio.sleep(30)
    
    bot.loop.run_until_complete(start_with_retry())
