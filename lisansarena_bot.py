import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
from datetime import datetime
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
        logging.FileHandler("lisansarena_bot_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LisansArenaBot")

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
CONFIG_FILE = "bot_config.json"
LINKS_FILE = "lisansarena_shopier_links.json"

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
BOT_TOKEN = config.get("lisansarena_bot_token", "8272543860:AAGmIdyky47dOxFBmqCz-4mZGzvo1jknFDU")
ADMIN_ID = config.get("admin_id", 8797763469)
BOT_USER_ID = None

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("Invalid LisansArena Bot Token in config. Exiting.")
    exit(1)

# In-memory user state
user_states = {}
bot_username = "LisansArenaBot" # default, updated dynamically on start

# Initialize client
bot = TelegramClient(StringSession(), API_ID, API_HASH)

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
                    
                    price_val = item.get("priceData", {}).get("price", "0")
                    price_str = f"{float(price_val):.2f} TL"
                    
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

# ═══════════════════════════════════════════════════════════════
# Smart Product Matching - Müşteri serbest metin yazınca ürün eşleştir
# ═══════════════════════════════════════════════════════════════
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
        "product_footer": "✅ Güvenli İşlem · ⚡ Hızlı Teslimat · 🤝 Kesintisiz Destek\n\nÜrünü satın almak için aşağıdaki güvenli ödeme butonunu kullanabilirsiniz.",
        "buy_btn": "💳 Güvenle Ödeme Yap (Shopier)",
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
        "buy_btn": "💳 Pay Securely (Shopier)",
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
        await event.edit(text, buttons=buttons)
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

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
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
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_lang'))
async def menu_lang_callback(event):
    await show_lang_selection(event, is_callback=True)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    await show_main_menu(event, user_id, is_callback=True)

@bot.on(events.NewMessage(pattern='/guncelle'))
async def guncelle_handler(event):
    if event.sender_id != ADMIN_ID:
        return
        
    await event.respond("⏳ Ürün listesi güncelleniyor, lütfen bekleyin...")
    try:
        load_products_from_links_json()
        summary = "\n".join([f"- {cat['title']}: {len(cat['products'])} ürün" for cat_key, cat in CATEGORIES.items() if cat['products']])
        await event.respond(f"✅ Ürünler başarıyla güncellendi ve hafızaya yüklendi!\n\nToplam {len(ALL_PRODUCTS_FLAT)} ürün bulundu:\n{summary}")
    except Exception as e:
        await event.respond(f"❌ Güncelleme hatası: {e}")

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
    buttons = [[Button.inline(t["cancel"], b"menu_main")]]
    await event.edit(f"{t['support_title']}\n\n{t['support_desc']}", buttons=buttons)

@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    
    ban_data = await async_get_document(f"lisansarena_ban_{user_id}")
    if ban_data and ban_data.get("banned", False):
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
        matched_product, match_score = match_product_from_text(event.text)
        if matched_product:
            lang = user_lang_helper.get_user_lang(user_id) or "tr"
            t = TEXTS[lang]
            product_msg = (
                f"🔍 **{matched_product['title']}**\n"
                f"📝 {matched_product['desc']}\n\n"
                f"💰 **{t['price']}:** {matched_product['price']}\n\n"
                f"{t['product_footer']}"
            )
            buttons = [
                [Button.url(t["buy_btn"], matched_product.get('url', 'https://www.shopier.com/lisansarena'))],
                [Button.inline(t["support_btn"], b"menu_support")],
                [Button.inline("📋 Ana Menü / Main Menu", b"menu_main")]
            ]
            await event.respond(product_msg, buttons=buttons)
            return

    support_chat_id = config.get("support_chat_id", ADMIN_ID)
    if event.sender_id == ADMIN_ID or event.chat_id == support_chat_id:
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
    await event.edit(f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

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
    load_products_from_links_json()
    logger.info("Starting LisansArena Sales Bot...")
    
    bot.loop.run_until_complete(main())
