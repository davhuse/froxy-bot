import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import MessageNotModifiedError
from telethon.sessions import StringSession
import user_lang_helper
import firestore_helper
from gemini_helper import get_ai_response
from sales_metrics import record_event
from support_flow import claim_first_greeting, forward_customer_message, greeting_for, one_time_mode_enabled
from update_keyvadi_links_json import fetch_live_catalog, write_catalog_atomic

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

async def async_claim_event(event, scope):
    doc_id = get_event_claim_doc_id(event, scope)
    if not doc_id:
        return True
    result = await async_run_claim(doc_id, {"scope": scope, "chat_id": event.chat_id, "message_id": getattr(event.message, 'id', None)})
    return result is not False

async def async_release_event_claim(event, scope):
    doc_id = get_event_claim_doc_id(event, scope)
    if doc_id:
        await async_delete_document(doc_id)

async def async_run_claim(doc_id, fields):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.claim_document, doc_id, fields)

PRODUCT_REPLY_COOLDOWN_SECONDS = 90
PRODUCT_REPLY_COOLDOWNS = {}
LAST_AI_REPLY_TIME = {}
AUTO_REPLY_COOLDOWN_SECONDS = 300
LAST_AUTO_REPLY_TIME = {}
MESSAGE_BURST_DEBOUNCE_SECONDS = 1.5
LATEST_USER_MESSAGE_IDS = {}

def _product_reply_key(user_id, products=None, fallback_key=None):
    if products:
        parts = []
        for product in products[:4]:
            parts.append(str(product.get('id') or product.get('url') or product.get('title') or '').lower())
        product_key = '|'.join(parts)
    else:
        product_key = (fallback_key or 'fallback').strip().lower()[:100]
    return f"{user_id}:{product_key}"

def is_product_reply_cooling_down(user_id, products=None, fallback_key=None):
    now = time.monotonic()
    for key, expires in list(PRODUCT_REPLY_COOLDOWNS.items()):
        if expires <= now:
            PRODUCT_REPLY_COOLDOWNS.pop(key, None)
    key = _product_reply_key(user_id, products, fallback_key)
    return PRODUCT_REPLY_COOLDOWNS.get(key, 0) > now

def mark_product_reply_sent(user_id, products=None, fallback_key=None):
    PRODUCT_REPLY_COOLDOWNS[_product_reply_key(user_id, products, fallback_key)] = time.monotonic() + PRODUCT_REPLY_COOLDOWN_SECONDS

def is_auto_reply_cooling_down(user_id):
    return time.monotonic() - LAST_AUTO_REPLY_TIME.get(user_id, 0) < AUTO_REPLY_COOLDOWN_SECONDS

def mark_auto_reply_sent(user_id):
    LAST_AUTO_REPLY_TIME[user_id] = time.monotonic()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    # app.py captures stdout into lisansarena_bot_log.txt in production.
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("LisansArenaBot")
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
LINKS_FILE = "lisansarena_shopier_links.json"

# The public Shopier catalog is the source of truth.  These two Game Pass
# listings are no longer public; the four 9999999x IDs were temporary manual
# placeholders and therefore must never be shown as purchasable products.
RETIRED_SHOPIER_PRODUCT_IDS = {
    "48901882", "48901888",
    "99999991", "99999992", "99999993", "99999994",
}

# Products that were published after the last exported Shopier catalog.  Keep
# full Shopier IDs here so the bot always sends a real product URL, rather than
# a synthetic fallback link.  This list is deliberately merged at load time so
# refreshing the exported JSON later cannot create duplicate products.
SHOPIER_CATALOG_ADDITIONS = [
    {
        "id": "49099069",
        "title": "FC26 + Online Her Seyi Degisen Hesap",
        "description": "FC26 + Online Her Seyi Degisen Hesap.",
        "type": "digital",
        "url": "https://www.shopier.com/49099069",
        "priceData": {"currency": "TRY", "price": "299.99"},
    },
    {
        "id": "49099023",
        "title": "FC26 + Online Her Seyi Degisen Hesap",
        "description": "FC26 + Online Her Seyi Degisen Hesap.",
        "type": "digital",
        "url": "https://www.shopier.com/49099023",
        "priceData": {"currency": "TRY", "price": "299.99"},
    },
    {
        "id": "49099022",
        "title": "Zula Random Hesap",
        "description": "Zula Random Hesap.",
        "type": "digital",
        "url": "https://www.shopier.com/49099022",
        "priceData": {"currency": "TRY", "price": "5.00"},
    },
    {
        "id": "49099021",
        "title": "Netflix 4K UHD Ortak Profil",
        "description": "Netflix 4K UHD Ortak Profil.",
        "type": "digital",
        "url": "https://www.shopier.com/49099021",
        "priceData": {"currency": "TRY", "price": "39.99"},
    },
    {
        "id": "49099018",
        "title": "Steam 200 Dolar Random Key",
        "description": "Steam 200 Dolar Random Key.",
        "type": "digital",
        "url": "https://www.shopier.com/49099018",
        "priceData": {"currency": "TRY", "price": "30.00"},
    },
]

def save_ticket_to_file(bot_type, user_id, first_name, last_name, username, message):
    file_path = "tickets.json"
    new_ticket = {
        "bot_type": bot_type,
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    tickets = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tickets = json.load(f)
        except:
            tickets = []
    tickets.insert(0, new_ticket)
    tickets = tickets[:200]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
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

# Read token for LisansArena

IBAN_NO = "TR570082900009491531109206"
IBAN_ALICI = "Mahmut Rençber"
IBAN_UYARI = "🔴 **ÖNEMLİ UYARI:** Havale / EFT ödemesi yaparken **AÇIKLAMA alanını KESİNLİKLE BOŞ BIRAKINIZ!** Açıklama kısmına hiçbir şey yazmayınız."

BOT_TOKEN = os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", config.get("admin_id", 0)) or 0)
BOT_USER_ID = None

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("LisansArena Telegram secrets are not configured. Exiting.")
    exit(1)

# In-memory user state
user_states = {}
bot_username = "LisansArenaBot" # default, updated dynamically on start

# Initialize client
bot = TelegramClient(StringSession(), API_ID, API_HASH)

@bot.on(events.CallbackQuery())
async def acknowledge_callback(event):
    """Acknowledge Telegram callbacks immediately so the first click is not stuck."""
    try:
        await event.answer()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# Product Catalog - Shopier üzerinden satılan ürünler
# ═══════════════════════════════════════════════════════════════
CATEGORIES = {}
ALL_PRODUCTS_FLAT = []

def load_products_from_links_json():
    global ALL_PRODUCTS_FLAT, CATEGORIES
    products = []
    
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    pid = item.get("id")
                    title = item.get("title")
                    url = item.get("url")
                    
                    price_val = item.get("price")
                    if price_val is None:
                        price_val = item.get("priceData", {}).get("price", "0")
                    price_text = str(price_val).strip()
                    price_text = re.sub(r"\s*(?:TL|₺)\s*$", "", price_text, flags=re.I)
                    price_str = f"{price_text} TL"
                    
                    products.append({
                        "id": pid,
                        "title": title,
                        "price": price_str,
                        "url": url,
                        "desc": item.get("description", "")
                    })
            logger.info(f"Loaded {len(products)} products from {LINKS_FILE}.")
        except Exception as e:
            logger.error(f"Error loading {LINKS_FILE}: {e}")
            
    ALL_PRODUCTS_FLAT = list(products)
    
    # Rebuild categories
    temp_categories = {
        "firsatlar": {"title": "🔥 Kaçırılmayacak Fırsatlar", "products": {}},
        "ai": {"title": "🌟 Yapay Zeka (AI) Çözümleri", "products": {}},
        "streaming": {"title": "📺 Dizi & Film Platformları", "products": {}},
        "design": {"title": "🎨 Tasarım & Eğlence Üyelikleri", "products": {}},
        "license": {"title": "🔑 Lisans, Oyun & Diğer", "products": {}}
    }
    
    for p in products:
        title = p["title"]
        pid = p["id"]
        price = p["price"]
        url = p["url"]
        
        t = title.lower()
        
        # 1. Yapay Zeka (AI) Çözümleri
        if any(k in t for k in ["gemini", "perplexity", "magnific", "deepl", "ai", "grok", "chatgpt", "openai", "copilot", "claude", "midjourney", "semrush", "gamma", "quill", "ideogram"]):
            cat_key = "ai"
        # 2. Dizi & Film Platformları
        elif any(k in t for k in ["netflix", "prime video", "hbo max", "hbo", "crunchyroll", "exxen", "blutv", "disney"]):
            cat_key = "streaming"
        # 3. Tasarım & Eğlence Üyelikleri
        elif any(k in t for k in ["canva", "adobe", "creative cloud", "express", "capcut", "duolingo", "scribd", "design", "tasarım", "spotify", "youtube", "music"]):
            cat_key = "design"
        # 4. Lisans, Oyun & Diğer
        else:
            cat_key = "license"
            
        temp_categories[cat_key]["products"][pid] = {
            "title": title,
            "price": price,
            "url": url,
            "desc": p["desc"]
        }
        
    # Inject popular deals into firsatlar
    f_count = 0
    for p in products:
        if f_count >= 4:
            break
        t = p["title"].lower()
        if "netflix" in t or "canva" in t or "youtube" in t or "office" in t:
            temp_categories["firsatlar"]["products"][p["id"]] = {
                "title": p["title"],
                "price": p["price"],
                "url": p["url"],
                "desc": p["desc"]
            }
            f_count += 1
        
    CATEGORIES = temp_categories
    logger.info("In-memory categories rebuilt successfully.")

def refresh_live_catalog():
    """Refresh all Shopier pages; retain the last valid cache on any failure."""
    try:
        products = fetch_live_catalog("lisansarena")
        write_catalog_atomic(products, LINKS_FILE)
        logger.info("Refreshed all %s live LisansArena products.", len(products))
        return products
    except Exception as exc:
        logger.warning("Live LisansArena catalog refresh failed; cached catalog retained: %s", exc)
        return None

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
    return re.findall(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+', text.lower())

def match_product_from_text(msg_text):
    msg_clean = msg_text.lower().strip()
    msg_clean = msg_clean.replace("you tube", "youtube")
    msg_clean = re.sub(r'\byt\b', 'youtube', msg_clean)
    msg_clean = re.sub(r'\bwin\b', 'windows', msg_clean)
    msg_clean = msg_clean.replace("win10", "windows")
    msg_clean = msg_clean.replace("win11", "windows")
    msg_clean = msg_clean.replace("office365", "office 365")
    msg_clean = msg_clean.replace("gamepass", "game pass")
    
    query_words = _get_words(msg_clean)
    
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "steam", "whatsapp", "apple", "perplexity",
        "crunchyroll", "chatgpt", "midjourney", "creative", "deepl", "magnific"
    }
    
    has_brand = any(w in brand_keywords for w in query_words)
    if not has_brand:
        return None, 0
        
    query_brands = [w for w in query_words if w in brand_keywords]
    
    skip_words = {
        "var", "mi", "mı", "mu", "mü", "ve", "de", "da", "için", "misiniz", "miyiz",
        "olur", "miyim", "yok", "acaba", "hizmeti", "ürünü", "hesabı", "kodu", "kuponu",
        "premium", "alacaktım", "hocam", "knk", "kanka", "bir", "alacağım", "alacaktim",
        "istiyorum", "lazım", "lazim", "alalım", "alalim", "kaç", "kac", "fiyat",
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi"
    }
    
    best_product = None
    best_score = 0
    
    for p in ALL_PRODUCTS_FLAT:
        title_lower = p.get("title", "").lower()
        title_words = set(_get_words(title_lower))
        
        if query_brands:
            if not any(b in title_words for b in query_brands):
                continue
        
        score = 0
        matched_brand = False
        
        for i in range(len(query_words) - 1):
            phrase = f"{query_words[i]} {query_words[i+1]}"
            if phrase in title_lower:
                score += 50
                
        for w in query_words:
            if w in skip_words or len(w) <= 1:
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
        
        if not matched_brand and score < 50:
            continue
            
        # Penalties
        if "ultra" in query_words and "ultra" not in title_words:
            score -= 100
        if "pro" in query_words and "pro" not in title_words:
            score -= 50
        if "1 aylık" in title_lower and "haftalık" in query_words:
            score -= 80
            
        if score > best_score:
            best_score = score
            best_product = p
            
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
        "scribd", "gamma", "steam", "whatsapp", "apple", "perplexity",
        "crunchyroll", "chatgpt", "midjourney", "creative", "deepl", "magnific"
    }
    
    primary_brands = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "steam", "whatsapp", "apple", "perplexity",
        "crunchyroll", "chatgpt", "midjourney", "creative", "deepl", "magnific"
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
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi"
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
                if w in skip_words or len(w) <= 1:
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
            if "pro" in query_words and "pro" not in title_words:
                score -= 50
            if "1 aylık" in title_lower and "haftalık" in query_words:
                score -= 80
                
            if score > best_score:
                best_score = score
                best_product = p
                
        if best_product and best_score >= 20:
            if best_product not in matched_products:
                matched_products.append(best_product)
                
    return matched_products

TEXTS = {
    "tr": {
        "welcome": (
            "🚀 **LisansArena'ya Hoş Geldiniz! - Dijital Dünyanın Zirvesi** 🚀\n\n"
            "İhtiyacınız olan tüm premium yazılımlar, oyunlar, yapay zeka araçları ve eğlence paketleri tek bir yerde!\n\n"
            "Hemen aşağıdaki menüden kategorinizi seçin 👇"
        ),
        "support_btn": "💬 Bize Ulaşın / Destek",
        "lang_btn": "🌍 Dil Değiştir / Language",
        "main_menu": "🏠 Ana Menüye Dön",
        "cat_title_mapping": {
            "firsatlar": "🔥 Kaçırılmayacak Fırsatlar",
            "ai": "🌟 Yapay Zeka (AI) Çözümleri",
            "streaming": "📺 Dizi & Film Platformları",
            "design": "🎨 Tasarım & Eğlence Üyelikleri",
            "license": "🔑 Lisans, Oyun & Diğer"
        },
        "select_product": "İncelemek veya satın almak istediğiniz ürünü seçiniz:",
        "price": "Fiyatımız",
        "product_footer": "✅ Güvenli Havale/EFT Ödemesi · ⚡ Hızlı Teslimat · 🤝 Kesintisiz Destek\n\nÜrünü satın almak için aşağıdaki IBAN ödeme butonunu kullanabilirsiniz.",
        "buy_btn": "💳 IBAN Bilgileri ile Satın Al",
        "support_title": "💬 **Müşteri Hizmetleri & İletişim**",
        "support_desc": "Sorularınızı, satın almak istediğiniz ürünü veya karşılaştığınız bir sorunu detaylıca buraya yazabilirsiniz.\n\nYetkili ekibimiz en kısa sürede size dönüş yapacaktır.",
        "cancel": "❌ İşlemi İptal Et",
        "support_success": "✅ Talebiniz başarıyla alındı. Müşteri temsilcimiz size en kısa sürede cevap verecektir.",
        "support_fail": "⚠️ Bir sorun oluştu ve mesajınız iletilemedi. Lütfen bir süre sonra tekrar deneyin.",
        "support_inactive": "⚠️ Şu anda müşteri hizmetleri sistemimiz geçici olarak çevrimdışıdır. Lütfen daha sonra tekrar deneyiniz.",
        "reply_prefix": "🔔 **LisansArena Ekibinden Mesaj:**\n\n",
        "choose_lang": "Lütfen dil seçiminizi yapın / Please choose your language:"
    },
    "en": {
        "welcome": (
            "🚀 **Welcome to LisansArena! - The Summit of the Digital World** 🚀\n\n"
            "All the premium software, games, AI tools, and entertainment packages you need in one place!\n\n"
            "Select your category from the menu below 👇"
        ),
        "support_btn": "💬 Contact Us / Support",
        "lang_btn": "🌍 Language / Dil Değiştir",
        "main_menu": "🏠 Back to Main Menu",
        "cat_title_mapping": {
            "firsatlar": "🔥 Kaçırılmayacak Fırsatlar / Super Deals",
            "ai": "🌟 Yapay Zeka (AI) Çözümleri / AI Solutions",
            "streaming": "📺 Dizi & Film Platformları / Streaming Platforms",
            "design": "🎨 Tasarım & Eğlence Üyelikleri / Design & Fun",
            "license": "🔑 Lisans, Oyun & Diğer / Licenses & Games"
        },
        "select_product": "Select the product you'd like to review or purchase:",
        "price": "Our Price",
        "product_footer": "✅ Secure Transaction · ⚡ Fast Delivery · 🤝 Continuous Support\n\nYou can use the secure payment button below to purchase the product.",
        "buy_btn": "💳 Pay via Bank IBAN Transfer",
        "support_title": "💬 **Customer Service & Contact**",
        "support_desc": "You can write your questions, the product you want to buy, or any problem you encountered in detail here.\n\nOur authorized team will get back to you as soon as possible.",
        "cancel": "❌ Cancel Action",
        "support_success": "✅ Your request has been successfully received. Our customer representative will reply to you shortly.",
        "support_fail": "⚠️ An error occurred and your message could not be sent. Please try again later.",
        "support_inactive": "⚠️ Our customer service system is temporarily offline right now. Please try again later.",
        "reply_prefix": "🔔 **Message from LisansArena Team:**\n\n",
        "choose_lang": "Please choose your language / Lütfen dil seçiminizi yapın:"
    }
}

async def show_lang_selection(event, is_callback=False):
    text = "Lütfen dilinizi seçin / Please choose your language:"
    buttons = [
        [Button.inline("🇹🇷 Türkçe", b"lang_tr"), Button.inline("🇺🇸 English", b"lang_en")]
    ]
    if is_callback:
        await safe_event_edit(event, text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)

async def show_main_menu(event, user_id, is_callback=False):
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]
    
    presence = await async_get_document("habil_presence") or {}
    is_online = presence.get("is_online", False)
    status_emoji = "🟢 **Destek Çevrimiçi / Support Online**" if is_online else "🔴 **Destek Çevrimdışı / Support Offline**"
    
    welcome = (
        f"{status_emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t['welcome']}"
    )
    
    buttons = []
    for cat_key, cat in CATEGORIES.items():
        if cat["products"]:
            title = t["cat_title_mapping"].get(cat_key, cat["title"])
            buttons.append([Button.inline(title, f"cat_{cat_key}".encode())])
            
    buttons.append([Button.inline("👥 Arkadaşını Davet Et / Invite Friends", b"menu_referral")])
    buttons.append([Button.inline(t["support_btn"], b"menu_support")])
    buttons.append([Button.inline(t["lang_btn"], b"menu_lang")])
    
    if is_callback:
        await safe_event_edit(event, welcome, buttons=buttons)
    else:
        await event.respond(welcome, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))
async def verify_payment_callback(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_states[event.sender_id] = None
    await event.answer("LisansArena ödemeleri yalnızca IBAN ve dekont ile alınır.", alert=True)
    await show_main_menu(event, event.sender_id, is_callback=True)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if not await async_claim_event(event, "lisansarena_sales"):
        return
    user_id = event.sender_id
    
    ban_data = await async_get_document(f"lisansarena_ban_{user_id}")
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
            
    user_doc_id = f"lisansarena_user_{user_id}"
    user_data = await async_get_document(user_doc_id)
    
    if not user_data:
        user_data = {
            "referrals_count": 0,
            "referred_by": ref_id or "",
            "id": user_id
        }
        await async_set_document(user_doc_id, user_data)
        
        if ref_id:
            ref_doc_id = f"lisansarena_user_{ref_id}"
            ref_data = await async_get_document(ref_doc_id)
            if ref_data:
                ref_data["referrals_count"] = ref_data.get("referrals_count", 0) + 1
                await async_set_document(ref_doc_id, ref_data)
                try:
                    await bot.send_message(int(ref_id), "🎉 **Tebrikler!** Bir arkadaşınız davetinizle LisansArena'ya katıldı. Davet sayınız güncellendi!")
                except Exception:
                    pass

    lang = user_lang_helper.get_user_lang(user_id)
    if not lang:
        await show_lang_selection(event)
    else:
        await show_main_menu(event, user_id)

@bot.on(events.NewMessage(pattern=r'/lang|/dil'))
async def lang_cmd_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    await show_lang_selection(event)

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
    user_data = await async_get_document(f"lisansarena_user_{user_id}") or {"referrals_count": 0}
    count = user_data.get("referrals_count", 0)
    
    coupon_info = ""
    if count >= 5:
        coupon_info = "🎁 **Tebrikler!** 5 referans barajını aştınız. Sizin için %15 indirim kuponunuz: **LISANSARENA15**"
    else:
        coupon_info = f"🎁 5 arkadaşınızı davet ettiğinizde **%15 indirim kuponu** kazanırsınız! (Kalan: `{5 - count}` davet)"

    text = (
        "👥 **LisansArena Davet & Kazan Sistemi**\n\n"
        f"👥 **Mevcut Davet Sayınız:** `{count} / 5`\n\n"
        f"{coupon_info}\n\n"
        "Arkadaşlarınızı davet edin, indirim kuponları kazanın! 🛍️\n\n"
        "🔗 **Sizin Davet Linkiniz:**\n"
        f"`https://t.me/{bot_username}?start=ref_{user_id}`\n\n"
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

@bot.on(events.NewMessage(pattern='/guncelle'))
async def guncelle_handler(event):
    if event.sender_id != ADMIN_ID:
        return
        
    await event.respond("⏳ Ürün listesi güncelleniyor, lütfen bekleyin...")
    try:
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(None, refresh_live_catalog)
        if not products:
            raise RuntimeError("Canlı Shopier kataloğu alınamadı; eski katalog korundu.")
        load_products_from_links_json()
        summary = "\n".join([f"- {cat['title']}: {len(cat['products'])} ürün" for cat_key, cat in CATEGORIES.items() if cat['products']])
        await event.respond(f"✅ Ürünler başarıyla güncellendi ve hafızaya yüklendi!\n\nToplam {len(ALL_PRODUCTS_FLAT)} ürün bulundu:\n{summary}")
    except Exception as e:
        await event.respond(f"❌ Güncelleme hatası: {e}")

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

    shopier_url = product.get("url", "https://www.shopier.com/lisansarena")

    price = product['price']
    if lang == "en":
        price = user_lang_helper.convert_price_to_usd(price)

    desc_text = (
        f"🌟 **{product['title']}**\n"
        f"📝 {product['desc']}\n\n"
        f"💰 **{t['price']}:** {price}\n\n"
        f"{t['product_footer']}"
    )
    
    cat_title = t["cat_title_mapping"].get(cat_key_found, CATEGORIES[cat_key_found]['title'])
    buttons = [
        [Button.inline("💳 IBAN Bilgileri & Satın Al", f"iban_{prod_key}".encode())],
        [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{prod_key}".encode())],
        [Button.inline(f"↩️ {cat_title}", f"cat_{cat_key_found}".encode())],
        [Button.inline(t["main_menu"], b"menu_main")]
    ]
    await safe_event_edit(event, desc_text, buttons=buttons)


# IBAN Ödeme Bilgileri Gösterici
@bot.on(events.CallbackQuery(pattern=r'iban_(\w+)'))
async def iban_info_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    prod_key = event.data.decode('utf-8').replace("iban_", "")
    
    product = None
    cat_key_found = None
    for ck, cat in CATEGORIES.items():
        if prod_key in cat["products"]:
            product = cat["products"][prod_key]
            cat_key_found = ck
            break
            
    title = product['title'] if product else "Seçilen Ürün"
    price = product['price'] if product else "0 TL"
    
    if lang == "en":
        price = user_lang_helper.convert_price_to_usd(price)

    iban_text = (
        f"💳 **LisansArena IBAN Ödeme Bilgileri**\n\n"
        f"📦 **Satın Alınacak Ürün:** {title}\n"
        f"💰 **Ödenecek Tutar:** `{price}`\n\n"
        f"🏦 **IBAN:**\n`{IBAN_NO}`\n\n"
        f"👤 **Alıcı Adı Soyadı:**\n`{IBAN_ALICI}`\n\n"
        f"{IBAN_UYARI}\n\n"
        f"Ödemenizi yaptıktan sonra aşağıdaki **'📸 Ödemeyi Doğrula / Dekont Gönder'** butonuna tıklayarak dekont fotoğrafını bu sohbete gönderebilirsiniz.\n\n"
        f"💬 **Destek / İletişim:** @LisansArenaAdmin"
    )
    buttons = [
        [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{prod_key}".encode())],
        [Button.inline("↩️ Ürün Sayfasına Dön", f"prod_{prod_key}".encode())],
        [Button.inline("🏠 Ana Menü", b"menu_main")]
    ]
    await safe_event_edit(event, iban_text, buttons=buttons)

# Dekont Bekleme Durumu Başlatıcı
@bot.on(events.CallbackQuery(pattern=r'verify_iban_(\w+)'))
async def verify_iban_handler(event):
    try:
        await event.answer()
    except Exception:
        pass
    user_id = event.sender_id
    prod_key = event.data.decode('utf-8').replace("verify_iban_", "")
    user_states[user_id] = f"AWAITING_DEKONT:{prod_key}"
    
    text = (
        "📸 **Ödeme Doğrulama & Dekont Gönderimi**\n\n"
        "Lütfen Havale/EFT ödemenize ait **dekont fotoğrafını veya ekran görüntüsünü** bu sohbete gönderin.\n\n"
        "Ödeme ve dekontunuz yetkili ekibimize anında iletilecek ve lisans kodunuz bu sohbet üzerinden tarafınıza teslim edilecektir.\n\n"
        "💬 İletişim / Canlı Destek: @LisansArenaAdmin\n"
        "*(Vazgeçmek için /start yazabilirsiniz)*"
    )
    buttons = [
        [Button.inline("↩️ Vazgeç ve Ana Menü", b"menu_main")]
    ]
    await safe_event_edit(event, text, buttons=buttons)

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
    buttons = [[Button.inline(t["cancel"], b"menu_main")]]
    await safe_event_edit(event, f"{t['support_title']}\n\n{t['support_desc']}", buttons=buttons)

PROCESSED_MESSAGE_EVENTS = set()

@bot.on(events.NewMessage(incoming=True))
@serialize_user_events
async def message_handler(event):
    if getattr(event, 'out', False):
        return
    if event.text and event.text.startswith('/'):
        return
    claim_scope = "lisansarena_sales"
    event_key = (event.chat_id, getattr(event.message, 'id', None))
    if event_key in PROCESSED_MESSAGE_EVENTS:
        return
    PROCESSED_MESSAGE_EVENTS.add(event_key)
    if len(PROCESSED_MESSAGE_EVENTS) > 10000:
        PROCESSED_MESSAGE_EVENTS.clear()
    if not await async_claim_event(event, claim_scope):
        return
    user_id = event.sender_id
    record_event("dm_received", "LisansArena", source="telegram_private")
    
    ban_data = await async_get_document(f"lisansarena_ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
        return

    # LisansArena Shopier doğrulama akışı kapatıldı; eski state'ler de IBAN'a yönlendirilir.
    if user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO":
        user_states[user_id] = None
        await event.respond("LisansArena ödemeleri yalnızca IBAN ile alınır. Ürünü menüden seçip IBAN bilgileri veya dekont gönderme adımını kullanabilirsiniz.")
        return

    if False and user_states.get(user_id) == "AWAITING_VERIFY_PAYMENT_INFO":
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
        
        # Check license category for auto delivery
        cat = None
        if "canva" in prod_name:
            cat = "canva"
        elif "adobe" in prod_name:
            cat = "adobe"
        elif "windows" in prod_name:
            cat = "windows"
        elif "office" in prod_name:
            cat = "office"
        elif "netflix" in prod_name:
            cat = "netflix"
        elif "youtube" in prod_name or "yt " in prod_name:
            cat = "youtube"
            
        license_key = None
        if cat:
            try:
                with open("licenses.json", "r", encoding="utf-8") as f:
                    stocks = json.load(f)
                keys = stocks.get(cat, [])
                if keys:
                    license_key = keys.pop(0)
                    stocks[cat] = keys
                    with open("licenses.json", "w", encoding="utf-8") as f:
                        json.dump(stocks, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error reading licenses.json: {e}")
                
        orders[unclaimed_idx]["claimed"] = True
        await async_set_document(doc_id, orders_doc)
        
        if license_key:
            await event.respond(
                f"✅ **Ödemeniz Başarıyla Doğrulandı!**\n\n"
                f"📦 **Satın Alınan Ürün:** {unclaimed_order.get('product_name')}\n"
                f"🔑 **Lisans Anahtarınız:**\n"
                f"`{license_key}`\n\n"
                f"*(Lisans anahtarını kopyalamak için üzerine tıklayabilirsiniz.)*\n\n"
                f"LisansArena'yı tercih ettiğiniz için teşekkür ederiz! 😊"
            )
            
            # Notify admin
            try:
                support_chat_id = config.get("support_chat_id", ADMIN_ID)
                if support_chat_id:
                    await bot.send_message(
                        support_chat_id, 
                        f"🎉 **LisansArena Otomatik Satış Bildirimi!**\n"
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
                support_chat_id = config.get("support_chat_id", ADMIN_ID)
                if support_chat_id:
                    await bot.send_message(
                        support_chat_id, 
                        f"🚨 **ACİL STOK UYARISI!**\n"
                        f"Kullanıcı `{user_id}` Shopier'den **{unclaimed_order.get('product_name')}** satın aldı ancak stokta lisans kodu yok!\n"
                        f"Lütfen en kısa sürede manuel teslimat yapın.\n"
                        f"📧 **Müşteri E-posta/Telefon:** {input_val}"
                    )
            except Exception:
                pass
                
        user_states[user_id] = None
        return

    config = load_config() or {}
    support_chat_id = config.get("support_chat_id", ADMIN_ID)
    is_admin_context = event.sender_id == ADMIN_ID or event.chat_id == support_chat_id
    if one_time_mode_enabled() and not is_admin_context:
        buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"la_adm_ban_{user_id}".encode())]]
        if await forward_customer_message(bot, event, support_chat_id, "LisansArena", buttons):
            record_event("dm_manual_forwarded", "LisansArena", source="telegram_private")
            if await claim_first_greeting("lisansarena", user_id):
                await event.respond(greeting_for("LisansArena"))
                record_event("dm_greeting_sent", "LisansArena", source="telegram_private")
        return

    if user_states.get(user_id) == "AWAITING_SUPPORT":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        lang = user_lang_helper.get_user_lang(user_id) or "tr"
        t = TEXTS[lang]

        support_chat_id = config.get("support_chat_id", ADMIN_ID)
        if not support_chat_id:
            await event.respond(t["support_inactive"])
            user_states[user_id] = None
            return

        user = await event.get_sender()
        username = f"@{user.username}" if user.username else "Yok"
        first_name = user.first_name or ""
        last_name = user.last_name or ""

        admin_msg = (
            f"📩 **[LisansArena] Yeni Destek Talebi!**\n"
            f"👤 **Kullanıcı ID:** `{user_id}`\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\n"
            f"💬 **Kullanıcı Adı:** {username}\n"
            f"🌐 **Dil/Lang:** {lang.upper()}\n"
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        admin_buttons = [[Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"la_adm_ban_{user_id}".encode())]]

        try:
            await bot.send_message(ADMIN_ID, admin_msg, buttons=admin_buttons)
            await event.respond(t["support_success"])
            save_ticket_to_file("LisansArena", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    # Smart Product Matching
    if event.text and not event.text.startswith('/'):
        if not has_sales_intent(event.text):
            logger.info("Ignoring non-sales message: %r", event.text)
            return
        if is_auto_reply_cooling_down(user_id):
            logger.info("Suppressing automatic sales reply for user %s (global 5-minute cooldown)", user_id)
            return
        matched_products = match_multiple_products_from_text(event.text)
        if matched_products:
            if is_product_reply_cooling_down(user_id, matched_products):
                logger.info("Suppressing duplicate product reply for user %s: %r", user_id, event.text)
                return
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            
            if len(matched_products) == 1:
                matched_product = matched_products[0]
                product_msg = (
                    f"🔍 **{matched_product['title']}**\n"
                    f"📝 {matched_product['desc']}\n\n"
                    f"💰 **{t['price']}:** {matched_product['price']}\n\n"
                    f"{t['product_footer']}"
                )
                buttons = [
                    [Button.inline("💳 IBAN Bilgileri & Satın Al", f"iban_{matched_product['id']}".encode())],
                    [Button.inline("📸 Ödemeyi Doğrula (Dekont Gönder)", f"verify_iban_{matched_product['id']}".encode())],
                    [Button.inline(t["support_btn"], b"menu_support")],
                    [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
                ]
            else:
                product_msg = "🔍 **Aradığınız Ürünler / Matched Products:**\n\n"
                buttons = []
                for i, p in enumerate(matched_products[:4]):
                    product_msg += f"{i+1}. **{p['title']}**\n💰 {t['price']}: {p['price']}\n👉 {p['url']}\n\n"
                    buttons.append([Button.url(f"Satın Al / Buy ({p['title'][:20]}...)", p.get('url', ''))])
                product_msg += f"{t['product_footer']}"
                buttons.append([Button.inline(t["support_btn"], b"menu_support")])
                buttons.append([Button.inline("📋 Ana Menü / Main Menu", b"menu_main")])
                
            try:
                await event.respond(product_msg, buttons=buttons)
            except Exception:
                PROCESSED_MESSAGE_EVENTS.discard(event_key)
                await async_release_event_claim(event, claim_scope)
                raise
            mark_product_reply_sent(user_id, matched_products)
            mark_auto_reply_sent(user_id)
            record_event("dm_reply_sent", "LisansArena", source="telegram_private", product=matched_products[0].get('title', '') if matched_products else '')
            return
        else:
            # Yapay Zeka Akıllı Satış Asistanı
            products = list(ALL_PRODUCTS_FLAT)
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            fallback_key = re.sub(r'\s+', ' ', event.text.strip().lower())
            if is_product_reply_cooling_down(user_id, fallback_key=fallback_key):
                logger.info("Suppressing duplicate AI fallback for user %s: %r", user_id, event.text)
                return
            
            # Global per-user AI response rate limit (15 seconds)
            now = time.monotonic()
            last_reply = LAST_AI_REPLY_TIME.get(user_id, 0)
            if now - last_reply < 15:
                logger.info("Suppressing consecutive AI response for user %s (global AI cooldown)", user_id)
                return
                
            ai_reply = get_ai_response(event.text, "LisansArena", products)
            if ai_reply:
                buttons = [
                    [Button.inline(t["support_btn"], b"menu_support")],
                    [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
                ]
                try:
                    await event.respond(ai_reply, buttons=buttons)
                except Exception:
                    PROCESSED_MESSAGE_EVENTS.discard(event_key)
                    await async_release_event_claim(event, claim_scope)
                    raise
                LAST_AI_REPLY_TIME[user_id] = now
                mark_product_reply_sent(user_id, fallback_key=fallback_key)
                mark_auto_reply_sent(user_id)
                record_event("dm_reply_sent", "LisansArena", source="telegram_private", product="AI")
                logger.info(f"AI response for user {user_id}: '{event.text}'")
                return

    support_chat_id = config.get("support_chat_id", ADMIN_ID)
    if event.sender_id == ADMIN_ID or event.chat_id == support_chat_id:
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                # Ensure the replied-to message was sent by this bot itself to prevent cross-talk
                match = None
                if reply_msg.sender_id == BOT_USER_ID:
                    match = re.search(r"Kullanıcı ID:\*\* `(\d+)`", reply_msg.text)
                if not match:
                    match = re.search(r"Kullanıcı ID: (\d+)", reply_msg.text)

                if match:
                    target_user_id = int(match.group(1))
                    target_lang = user_lang_helper.get_user_lang(target_user_id) or "tr"
                    prefix = TEXTS[target_lang]["reply_prefix"]
                    
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

@bot.on(events.CallbackQuery(pattern=r'la_adm_ban_(\d+)'))
async def la_admin_ban_user_callback(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    target_user_id = int(event.pattern_match.group(1))
    ban_doc_id = f"lisansarena_ban_{target_user_id}"
    await async_set_document(ban_doc_id, {"banned": True, "id": target_user_id})
    await event.answer("🚫 Kullanıcı engellendi.", alert=True)
    original_text = event.message.text
    await safe_event_edit(event, f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

async def get_bot_info():
    global bot_username, BOT_USER_ID
    try:
        me = await bot.get_me()
        bot_username = me.username or "LisansArenaBot"
        BOT_USER_ID = me.id
        logger.info(f"Bot dynamically resolved username: @{bot_username} | User ID: {BOT_USER_ID}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")

async def main():
    from telethon.errors import FloodWaitError
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            await get_bot_info()
            logger.info("LisansArena Sales Bot started successfully!")
            await bot.run_until_disconnected()
        except FloodWaitError as e:
            logger.warning(f"FloodWait: Telegram {e.seconds} saniye beklememizi istiyor. Bekleniyor...")
            await asyncio.sleep(e.seconds + 5)
            logger.info("FloodWait süresi bitti, tekrar deneniyor...")
        except Exception as e:
            logger.error(f"Bot başlatma hatası: {e}")
            await asyncio.sleep(30)

if __name__ == '__main__':
    import asyncio
    logger.info("Loading LisansArena products cache...")
    refresh_live_catalog()
    load_products_from_links_json()
    logger.info("Starting LisansArena Sales Bot...")
    
    bot.loop.run_until_complete(main())
