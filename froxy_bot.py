import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import user_lang_helper
import firestore_helper

# Async wrappers for firestore_helper to prevent event loop deadlocks/freezes
async def async_get_document(doc_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.get_document, doc_id)

async def async_set_document(doc_id, fields_dict):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, firestore_helper.set_document, doc_id, fields_dict)

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("froxy_bot_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KeyVadiBot")

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
CONFIG_FILE = "bot_config.json"

# Load config
def save_ticket_to_file(bot_type, user_id, first_name, last_name, username, message):
    import datetime
    file_path = "tickets.json"
    new_ticket = {
        "bot_type": bot_type,
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

BOT_TOKEN = config.get("bot_token", "")
ADMIN_ID = config.get("admin_id", 0)
BOT_USER_ID = None
SHOPIER_LINKS = config.get("shopier_links", {})

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("Invalid Bot Token in config. Please set it via Web Panel.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# ═══════════════════════════════════════════════════════════════
# KeyVadi Product Catalog - Shopier üzerinden satılan ürünler
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {}

# Products that are NOT in the Shopier showroom (hidden/delisted/paginated) but still active
# These are injected into the catalog alongside scraped products
INJECTED_PRODUCTS = [{"id": "47669105", "title": "YouTube Premium (3 Aylık Kod)", "price": "29.99 TL", "url": "https://www.shopier.com/keyvadi/47669105"},
    {"id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "49.99 TL", "url": "https://www.shopier.com/keyvadi/47669117"},
    {"id": "48114807", "title": "XBOX Game Pass Ultimate (3 Aylık Üyelik)", "price": "80.00 TL", "url": "https://www.shopier.com/keyvadi/48114807"},
    {"id": "48114802", "title": "Steam İstediğiniz Oyun (Ortak Hesap)", "price": "60.00 TL", "url": "https://www.shopier.com/keyvadi/48114802"},
    {"id": "48114795", "title": "Semrush Pro (14 Günlük Hesap)", "price": "150.00 TL", "url": "https://www.shopier.com/keyvadi/48114795"},
    {"id": "48114789", "title": "Microsoft Office 365 (1 Yıllık Hesap)", "price": "70.00 TL", "url": "https://www.shopier.com/keyvadi/48114789"},
    {"id": "48114785", "title": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": "70.00 TL", "url": "https://www.shopier.com/keyvadi/48114785"},
    {"id": "47669159", "title": "Gemini Pro (1 Yıllık Hesap)", "price": "299.99 TL", "url": "https://www.shopier.com/keyvadi/47669159"},
    {"id": "47669164", "title": "Gemini Pro (Davet Linki)", "price": "124.99 TL", "url": "https://www.shopier.com/keyvadi/47669164"},
    {"id": "47669192", "title": "Gemini Ultra (Davet Linki)", "price": "399.99 TL", "url": "https://www.shopier.com/keyvadi/47669192"},
    {"id": "47669222", "title": "Gemini Ultra (2.5k Kredili Hesap)", "price": "599.99 TL", "url": "https://www.shopier.com/keyvadi/47669222"},
    {"id": "47669248", "title": "Super Grok (1 Aylık Hesap)", "price": "449.99 TL", "url": "https://www.shopier.com/keyvadi/47669248"},
    {"id": "47669271", "title": "Super Grok (3 Aylık Hesap)", "price": "949.99 TL", "url": "https://www.shopier.com/keyvadi/47669271"},
    {"id": "47669295", "title": "Super Grok (6 Aylık Hesap)", "price": "1499.99 TL", "url": "https://www.shopier.com/keyvadi/47669295"},
    {"id": "47669305", "title": "Super Grok (12 Aylık Hesap)", "price": "2299.99 TL", "url": "https://www.shopier.com/keyvadi/47669305"},
    {"id": "47669310", "title": "Gamma Ultra (1 Aylık Hesap)", "price": "449.99 TL", "url": "https://www.shopier.com/keyvadi/47669310"},
    {"id": "47669316", "title": "Gamma Pro (1 Aylık Hesap)", "price": "299.99 TL", "url": "https://www.shopier.com/keyvadi/47669316"},
    {"id": "48943133", "title": "Eski Tarihli Telegram Hesabı (+1 No'lu)", "price": "149.90 TL", "url": "https://www.shopier.com/48943133"},
    {"id": "48943136", "title": "Perplexity Pro (1 Aylık Hesap)", "price": "119.90 TL", "url": "https://www.shopier.com/48943136"},
    {"id": "48943137", "title": "DeepL AI (1 Aylık) - Kişisel Hesap", "price": "59.90 TL", "url": "https://www.shopier.com/48943137"},
    {"id": "48943139", "title": "DeepL AI (1 Aylık) - Ortak Hesap", "price": "29.90 TL", "url": "https://www.shopier.com/48943139"},
    {"id": "48943141", "title": "Scribd (1 Aylık) - Kişisel Hesap", "price": "59.90 TL", "url": "https://www.shopier.com/48943141"},
    {"id": "48943143", "title": "Scribd (1 Aylık) - Ortak Hesap", "price": "29.90 TL", "url": "https://www.shopier.com/48943143"},
    {"id": "48943144", "title": "Magnific AI Ortak (1 Aylık Business Hesap)", "price": "49.90 TL", "url": "https://www.shopier.com/48943144"},
    {"id": "48943146", "title": "Crunchyroll Özel Profil (1 Aylık)", "price": "59.90 TL", "url": "https://www.shopier.com/48943146"},
    {"id": "48943148", "title": "Crunchyroll Ortak Hesap (1 Aylık)", "price": "39.90 TL", "url": "https://www.shopier.com/48943148"},
    {"id": "48943150", "title": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza", "price": "79.90 TL", "url": "https://www.shopier.com/48943150"},
    {"id": "48943151", "title": "Grammarly Pro (1 Aylık) - Ortak Hesap", "price": "49.90 TL", "url": "https://www.shopier.com/48943151"},
    {"id": "48901849", "title": "HBO Max 1 Aylık Profil", "price": "39.90 TL", "url": "https://www.shopier.com/48901849"},
    {"id": "48901864", "title": "Prime Video (1 Aylık) - Özel Profil", "price": "29.90 TL", "url": "https://www.shopier.com/48901864"},
    {"id": "48901866", "title": "Prime Video (1 Aylık) - Ortak Profil", "price": "29.90 TL", "url": "https://www.shopier.com/48901866"}
]

# Flat list of all products (rebuilt when products are loaded)
ALL_PRODUCTS_FLAT = []

# ═══════════════════════════════════════════════════════════════
# Smart Product Matching - Müşteri serbest metin yazınca ürün eşleştir
# ═══════════════════════════════════════════════════════════════

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
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot"
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

def scrape_shopier():
    logger.info("Scraping Shopier showroom at https://www.shopier.com/keyvadi ...")
    context = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request('https://www.shopier.com/keyvadi', headers=headers)
    
    try:
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
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

def rebuild_categories(products):
    global CATEGORIES
    
    temp_categories = {
        "firsatlar": {"title": "🔥 Kaçırılmayacak Fırsatlar", "products": {}},
        "ai": {"title": "🌟 Yapay Zeka (AI) Çözümleri", "products": {}},
        "streaming": {"title": "📺 Dizi & Film Platformları", "products": {}},
        "design": {"title": "🎨 Tasarım & Eğlence Üyelikleri", "products": {}},
        "license": {"title": "🔑 Lisans, Oyun & Diğer", "products": {}}
    }
    
    # Injected Hot Deals (Netflix, Adobe, Youtube Premium, Gemini Pro Davet)
    temp_categories["firsatlar"]["products"]["f1"] = {
        "title": "📺 Netflix 4K UHD Profil",
        "price": "49.99 TL",
        "url": "https://www.shopier.com/keyvadi/47669117"
    }
    temp_categories["firsatlar"]["products"]["f2"] = {
        "title": "🎨 Adobe Creative Cloud (1 Haftalık)",
        "price": "49.99 TL",
        "url": "https://www.shopier.com/keyvadi/47669341"
    }
    temp_categories["firsatlar"]["products"]["f3"] = {
        "title": "🎬 YouTube Premium (3 Aylık Kod)",
        "price": "29.99 TL",
        "url": "https://www.shopier.com/keyvadi/47669105"
    }
    temp_categories["firsatlar"]["products"]["f4"] = {
        "title": "🤖 Gemini Pro Davet Linki",
        "price": "69.99 TL",
        "url": "https://www.shopier.com/keyvadi/47669164"
    }
    
    for p in products:
        title = p["title"]
        pid = p["id"]
        price = p["price"]
        url = p["url"]
        
        t = title.lower()
        
        # 1. Yapay Zeka (AI) Çözümleri
        if any(k in t for k in ["gemini", "grok", "ai", "gamma", "kiro", "chatgpt", "openai", "copilot", "claude", "midjourney", "semrush", "deepl", "quill", "ideogram", "perplexity", "magnific"]):
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
            "url": url
        }
        
    CATEGORIES = temp_categories
    logger.info("In-memory categories rebuilt successfully.")

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
    
    # Merge injected products (hidden/delisted but still active)
    existing_ids = {p["id"] for p in products}
    for ip in INJECTED_PRODUCTS:
        if ip["id"] not in existing_ids:
            products.append(ip)
            logger.info(f"Injected hidden product: {ip['title']}")
    
    # Build flat product list for smart matching
    ALL_PRODUCTS_FLAT = list(products)
    logger.info(f"Total products available for matching: {len(ALL_PRODUCTS_FLAT)}")
                
    # Rebuild in-memory categories
    rebuild_categories(products)


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
            "firsatlar": "🔥 Kaçırılmayacak Fırsatlar",
            "ai": "🌟 Yapay Zeka (AI) Çözümleri",
            "streaming": "📺 Dizi & Film Platformları",
            "design": "🎨 Tasarım & Eğlence Üyelikleri",
            "license": "🔑 Lisans, Oyun & Diğer"
        },
        "select_product": "Detaylarını görmek ve satın almak istediğiniz ürünü seçin:",
        "price": "Fiyat",
        "product_footer": "✅ Anında teslim · 7/24 destek · Güvenli ödeme\n\nSatın almak için aşağıdaki butona tıklayın. Ödeme sonrası teslimat anında gerçekleştirilir.",
        "buy_btn": "💳 Shopier ile Güvenli Satın Al",
        "support_title": "📞 **Destek Talebi & Sipariş Verme**",
        "support_desc": "Satın almak istediğiniz ürün, sipariş sorunu veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\nMesajınız doğrudan admin ekibimize iletilecektir. En kısa sürede yanıt alacaksınız.",
        "cancel": "↩️ Vazgeç ve İptal Et",
        "support_success": "✅ Mesajınız ekibimize iletildi. En kısa sürede yanıt alacaksınız.",
        "support_fail": "⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.",
        "support_inactive": "⚠️ Üzgünüz, şu anda destek sistemi aktif değil (Admin ID tanımlanmamış). Lütfen daha sonra deneyin.",
        "reply_prefix": "📨 **KeyVadi Destek Ekibinden Cevap:**\n\n",
        "choose_lang": "Lütfen dilinizi seçin / Please choose your language:"
    },
    "en": {
        "welcome": (
            "⚡ **Welcome to KeyVadi Sales Panel!**\n\n"
            "Premium artificial intelligence accounts, licenses, verified mobile accounts, and special deals at the best prices!\n\n"
            "Please select the action you want to perform 👇"
        ),
        "support_btn": "📞 Live Support & Contact",
        "lang_btn": "🌐 Language / Dil",
        "main_menu": "↩️ Main Menu",
        "cat_title_mapping": {
            "firsatlar": "🔥 Kaçırılmayacak Fırsatlar / Super Deals",
            "ai": "🌟 Yapay Zeka (AI) Çözümleri / AI Solutions",
            "streaming": "📺 Dizi & Film Platformları / Streaming Platforms",
            "design": "🎨 Tasarım & Eğlence Üyelikleri / Design & Fun",
            "license": "🔑 Lisans, Oyun & Diğer / Licenses & Games"
        },
        "select_product": "Select the product you want to view details and purchase:",
        "price": "Price",
        "product_footer": "✅ Instant delivery · 24/7 support · Secure payment\n\nClick the button below to purchase. Delivery is made instantly after payment.",
        "buy_btn": "💳 Secure Purchase with Shopier",
        "support_title": "📞 **Support Request & Ordering**",
        "support_desc": "Please write the product you want to buy, order issue, or support request in detail and send it to this chat.\n\nYour message will be forwarded directly to our admin team. You will receive a response as soon as possible.",
        "cancel": "↩️ Cancel & Go Back",
        "support_success": "✅ Your message has been forwarded to our team. You will receive a response as soon as possible.",
        "support_fail": "⚠️ Your message could not be delivered. Please try again later.",
        "support_inactive": "⚠️ Sorry, the support system is currently offline (Admin ID not set). Please try again later.",
        "reply_prefix": "📨 **Reply from KeyVadi Support Team:**\n\n",
        "choose_lang": "Please choose your language / Lütfen dilinizi seçin:"
    }
}

# Language Selection Screen Helper
async def show_lang_selection(event, is_callback=False):
    text = "Lütfen dilinizi seçin / Please choose your language:"
    buttons = [
        [Button.inline("🇹🇷 Türkçe", b"lang_tr"), Button.inline("🇺🇸 English", b"lang_en")]
    ]
    if is_callback:
        await event.edit(text, buttons=buttons)
    else:
        await event.respond(text, buttons=buttons)

# Main Menu Helper
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
            
    buttons.append([Button.inline("💳 Ödememi Doğrula / Verify Payment", b"menu_verify_payment")])
    buttons.append([Button.inline("👥 Arkadaşını Davet Et / Invite Friends", b"menu_referral")])
    buttons.append([Button.inline(t["support_btn"], b"menu_support")])
    buttons.append([Button.inline(t["lang_btn"], b"menu_lang")])
    
    if is_callback:
        await event.edit(welcome, buttons=buttons)
    else:
        await event.respond(welcome, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))
async def verify_payment_callback(event):
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
    await event.edit(text, buttons=buttons)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
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
async def lang_cmd_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    await show_lang_selection(event)

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

@bot.on(events.CallbackQuery(data=b'menu_referral'))
async def menu_referral_handler(event):
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
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_lang'))
async def menu_lang_callback(event):
    await show_lang_selection(event, is_callback=True)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    await show_main_menu(event, user_id, is_callback=True)

# Admin update handler
@bot.on(events.NewMessage(pattern='/guncelle'))
async def guncelle_handler(event):
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    
    if event.sender_id != admin_chat_id:
        return
        
    await event.respond("⏳ Shopier ürün listesi güncelleniyor, lütfen bekleyin...")
    
    loop = asyncio.get_event_loop()
    products = await loop.run_in_executor(None, scrape_shopier)
    
    if products:
        file_path = "parsed_keyvadi_products.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            rebuild_categories(products)
            
            # Count products per category
            summary = "\n".join([f"- {cat['title']}: {len(cat['products'])} ürün" for cat_key, cat in CATEGORIES.items() if cat['products']])
            await event.respond(f"✅ Ürünler başarıyla güncellendi ve hafızaya yüklendi!\n\nToplam {len(products)} ürün bulundu:\n{summary}")
        except Exception as e:
            logger.error(f"Error saving updated products: {e}")
            await event.respond(f"❌ Güncelleme yapıldı fakat dosyaya yazılamadı: {e}")
    else:
        await event.respond("❌ Ürün listesi güncellenemedi (Shopier sayfasından veri çekilemedi).")

# Category handler
@bot.on(events.CallbackQuery(pattern=r'cat_(\w+)'))
async def category_handler(event):
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
    await event.edit(f"**{cat_title}**\n\n{t['select_product']}", buttons=buttons)

# Product detail handler
@bot.on(events.CallbackQuery(pattern=r'prod_(\w+)'))
async def product_handler(event):
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
    await event.edit(desc_text, buttons=buttons)

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
    await event.edit(f"{t['support_title']}\n\n{t['support_desc']}", buttons=buttons)

@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    logger.info(f"New message from user {user_id}: '{event.text}'")
    
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
        
        # Check license category
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
                print(f"Error reading/updating licenses.json: {e}")
                
        # Mark order as claimed
        orders[unclaimed_idx]["claimed"] = True
        await async_set_document(doc_id, orders_doc)
        
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
        matched_product, match_score = match_product_from_text(event.text)
        if matched_product:
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            price = matched_product['price']
            if lang == "en":
                price = user_lang_helper.convert_price_to_usd(price)
            
            product_msg = (
                f"🔍 **{matched_product['title']}**\n\n"
                f"💰 **{t['price']}:** {price}\n\n"
                f"{t['product_footer']}"
            )
            buttons = [
                [Button.url(t["buy_btn"], matched_product.get('url', 'https://www.shopier.com/keyvadi'))],
                [Button.inline(t["support_btn"], b"menu_support")],
                [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
            ]
            await event.respond(product_msg, buttons=buttons)
            logger.info(f"Smart match for user {user_id}: '{event.text}' → {matched_product['title']} (score={match_score})")
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
                if reply_msg.sender_id == BOT_USER_ID:
                    match = re.search(r"Kullanıcı ID:\*\* `(\d+)`", reply_msg.text)
                if not match:
                    match = re.search(r"Kullanıcı ID: (\d+)", reply_msg.text)

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
    await event.edit(f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

if __name__ == '__main__':
    import asyncio
    from telethon.errors import FloodWaitError
    
    logger.info("Loading KeyVadi products cache...")
    load_products_from_file_or_scrape()
    
    async def start_with_retry():
        global BOT_USER_ID
        while True:
            try:
                logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
                await bot.start(bot_token=BOT_TOKEN)
                me = await bot.get_me()
                BOT_USER_ID = me.id
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
