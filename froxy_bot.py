import os
import json
import logging
import re
import urllib.request
import ssl
import html
import asyncio
from telethon import TelegramClient, events, Button

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


welcome_text = (
    "⚡ **KeyVadi Satış Paneline Hoş Geldiniz!**\n\n"
    "Premium yapay zeka hesapları, lisanslar, onaylı mobil hesaplar ve özel fırsatlar en uygun fiyatlarla!\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = []
    for cat_key, cat in CATEGORIES.items():
        if cat["products"]:  # Only show categories with products
            buttons.append([Button.inline(cat["title"], f"cat_{cat_key}".encode())])
    buttons.append([Button.inline("📞 Canlı Destek & İletişim", b"menu_support")])
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = []
    for cat_key, cat in CATEGORIES.items():
        if cat["products"]:  # Only show categories with products
            buttons.append([Button.inline(cat["title"], f"cat_{cat_key}".encode())])
    buttons.append([Button.inline("📞 Canlı Destek & İletişim", b"menu_support")])
    await event.edit(welcome_text, buttons=buttons)


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
    cat_key = event.data.decode('utf-8').replace("cat_", "")
    cat = CATEGORIES.get(cat_key)
    if not cat:
        await event.answer("Kategori bulunamadı!", alert=True)
        return

    buttons = []
    for prod_key, prod in cat["products"].items():
        label = f"{prod['title']} — {prod['price']}"
        # Truncate label to 64 chars for Telegram button limit
        if len(label) > 64:
            label = label[:61] + "..."
        buttons.append([Button.inline(label, f"prod_{prod_key}".encode())])
    buttons.append([Button.inline("↩️ Ana Menü", b"menu_main")])

    await event.edit(f"{cat['title']}\n\nDetaylarını görmek ve satın almak istediğiniz ürünü seçin:", buttons=buttons)

# Product detail handler
@bot.on(events.CallbackQuery(pattern=r'prod_(\w+)'))
async def product_handler(event):
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
        await event.answer("Ürün bulunamadı!", alert=True)
        return

    config = load_config() or {}
    links = config.get("shopier_links", SHOPIER_LINKS)
    shopier_url = links.get(prod_key, "https://www.shopier.com/keyvadi")

    text = (
        f"🌟 **{product['title']}**\n\n"
        f"💰 **Fiyat:** {product['price']}\n\n"
        f"✅ Anında teslim · 7/24 destek · Güvenli ödeme\n\n"
        f"Satın almak için aşağıdaki butona tıklayın. Ödeme sonrası teslimat anında gerçekleştirilir."
    )
    buttons = [
        [Button.url("💳 Shopier ile Güvenli Satın Al", shopier_url)],
        [Button.inline(f"↩️ {CATEGORIES[cat_key_found]['title']}", f"cat_{cat_key_found}".encode())],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await event.edit(text, buttons=buttons)


# Support Menu
@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"

    text = (
        "📞 **Destek Talebi & Sipariş Verme**\n\n"
        "Satın almak istediğiniz ürün, sipariş sorunu veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\n"
        "Mesajınız doğrudan admin ekibimize iletilecektir. En kısa sürede yanıt alacaksınız."
    )
    buttons = [
        [Button.inline("↩️ Vazgeç ve İptal Et", b"menu_main")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id

    if user_states.get(user_id) == "AWAITING_SUPPORT":
        if event.text.startswith('/'):
            user_states[user_id] = None
            return

        config = load_config() or {}
        admin_chat_id = config.get("admin_id", ADMIN_ID)

        if not admin_chat_id:
            await event.respond("⚠️ Üzgünüz, şu anda destek sistemi aktif değil (Admin ID tanımlanmamış). Lütfen daha sonra deneyin.")
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
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        try:
            await bot.send_message(admin_chat_id, admin_msg)
            await event.respond("✅ Mesajınız ekibimize iletildi. En kısa sürede yanıt alacaksınız.")
            save_ticket_to_file("KeyVadi", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond("⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.")

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
                try:
                    await bot.send_message(target_user_id, f"📨 **KeyVadi Destek Ekibinden Cevap:**\n\n{event.text}")
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
