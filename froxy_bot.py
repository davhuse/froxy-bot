import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
from telethon import TelegramClient, events, Button
import user_lang_helper

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
SHOPIER_LINKS = config.get("shopier_links", {})

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("Invalid Bot Token in config. Please set it via Web Panel.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient('froxy_bot_session', API_ID, API_HASH)

# ═══════════════════════════════════════════════════════════════
# KeyVadi Product Catalog - Shopier üzerinden satılan ürünler
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {}

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
        "ai": {"title": "🌟 Yapay Zeka (AI) Hesapları", "products": {}},
        "design": {"title": "🎨 Tasarım & Lisans Hizmetleri", "products": {}},
        "mobile": {"title": "📱 Onaylı Mobil Hesaplar", "products": {}},
        "deals": {"title": "🍔 Yemek & Akaryakıt Fırsatları", "products": {}},
        "other": {"title": "📦 Diğer Ürün & Hizmetler", "products": {}}
    }
    
    for p in products:
        title = p["title"]
        pid = p["id"]
        price = p["price"]
        url = p["url"]
        
        t = title.lower()
        if any(k in t for k in ["gemini", "grok", "ai", "gamma", "kiro", "chatgpt", "openai", "copilot", "claude", "midjourney"]):
            cat_key = "ai"
        elif any(k in t for k in ["canva", "adobe", "creative cloud", "express", "capcut", "duolingo", "scribd", "design", "tasarım", "spotify", "netflix"]):
            cat_key = "design"
        elif any(k in t for k in ["whatsapp", "apple id", "apple", "icloud", "numara", "mobil", "sms", "onay"]):
            cat_key = "mobile"
        elif any(k in t for k in ["trendyol", "yemek", "market", "shell", "akaryakıt", "indirim", "fırsat", "kampanya", "kod"]):
            cat_key = "deals"
        else:
            cat_key = "other"
            
        temp_categories[cat_key]["products"][pid] = {
            "title": title,
            "price": price,
            "url": url
        }
        
    CATEGORIES = temp_categories
    logger.info("In-memory categories rebuilt successfully.")

def load_products_from_file_or_scrape():
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
            "ai": "🌟 Yapay Zeka (AI) Hesapları",
            "design": "🎨 Tasarım & Lisans Hizmetleri",
            "mobile": "📱 Onaylı Mobil Hesaplar",
            "deals": "🍔 Yemek & Akaryakıt Fırsatları",
            "other": "📦 Diğer Ürün & Hizmetler"
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
            "ai": "🌟 Artificial Intelligence (AI) Accounts",
            "design": "🎨 Design & License Services",
            "mobile": "📱 Verified Mobile Accounts",
            "deals": "🍔 Food & Fuel Deals",
            "other": "📦 Other Products & Services"
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
    
    welcome = t["welcome"]
    buttons = []
    for cat_key, cat in CATEGORIES.items():
        if cat["products"]:
            title = t["cat_title_mapping"].get(cat_key, cat["title"])
            buttons.append([Button.inline(title, f"cat_{cat_key}".encode())])
            
    buttons.append([Button.inline(t["support_btn"], b"menu_support")])
    buttons.append([Button.inline(t["lang_btn"], b"menu_lang")])
    
    if is_callback:
        await event.edit(welcome, buttons=buttons)
    else:
        await event.respond(welcome, buttons=buttons)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
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
    shopier_url = links.get(prod_key, "https://www.shopier.com/keyvadi")

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

    if user_states.get(user_id) == "AWAITING_SUPPORT":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        config = load_config() or {}
        admin_chat_id = config.get("admin_id", ADMIN_ID)
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
            f"📩 **Yeni Destek Talebi!**\n"
            f"👤 **Kullanıcı ID:** `{user_id}`\n"
            f"👤 **Adı Soyadı:** {first_name} {last_name}\n"
            f"💬 **Kullanıcı Adı:** {username}\n"
            f"🌐 **Dil/Lang:** {lang.upper()}\n"
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        try:
            await bot.send_message(admin_chat_id, admin_msg)
            await event.respond(t["support_success"])
            save_ticket_to_file("KeyVadi", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)

    if event.sender_id == admin_chat_id and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.text:
            match = re.search(r"Kullanıcı ID:\*\* `(\d+)`", reply_msg.text)
            if not match:
                match = re.search(r"Kullanıcı ID: (\d+)", reply_msg.text)

            if match:
                target_user_id = int(match.group(1))
                target_lang = user_lang_helper.get_user_lang(target_user_id) or "tr"
                prefix = TEXTS[target_lang]["reply_prefix"]
                try:
                    await bot.send_message(target_user_id, f"{prefix}{event.text}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")

if __name__ == '__main__':
    logger.info("Loading KeyVadi products cache...")
    load_products_from_file_or_scrape()
    logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
