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
bot = TelegramClient(StringSession(), API_ID, API_HASH)

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
        if any(k in t for k in ["gemini", "grok", "ai", "gamma", "kiro", "chatgpt", "openai", "copilot", "claude", "midjourney", "semrush", "deepl", "quill", "ideogram", "envato", "freepik"]):
            cat_key = "ai"
        elif any(k in t for k in ["canva", "adobe", "creative cloud", "express", "capcut", "duolingo", "scribd", "design", "tasarım", "spotify", "netflix", "windows", "win ", "win10", "win11", "office", "key", "lisans", "autodesk", "figma", "wordpress", "grammarly", "vpn", "antivirüs", "antivirus", "xbox", "steam", "game pass"]):
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
    
    presence = firestore_helper.get_document("habil_presence") or {}
    is_online = presence.get("is_online", False)
    status_emoji = "🟢 **Habil Çevrimiçi / Online**" if is_online else "🔴 **Habil Çevrimdışı / Offline**"
    
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
    
    ban_data = firestore_helper.get_document(f"keyvadi_ban_{user_id}")
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
    user_data = firestore_helper.get_document(user_doc_id)
    is_new = False
    
    if not user_data:
        is_new = True
        user_data = {
            "referrals_count": 0,
            "referred_by": ref_id or "",
            "id": user_id
        }
        firestore_helper.set_document(user_doc_id, user_data)
        
        if ref_id:
            ref_doc_id = f"keyvadi_user_{ref_id}"
            ref_data = firestore_helper.get_document(ref_doc_id)
            if ref_data:
                ref_data["referrals_count"] = ref_data.get("referrals_count", 0) + 1
                firestore_helper.set_document(ref_doc_id, ref_data)
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
                firestore_helper.set_document(ref_doc_id, ref_data)

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
    user_data = firestore_helper.get_document(f"keyvadi_user_{user_id}") or {"referrals_count": 0}
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
    
    ban_data = firestore_helper.get_document(f"keyvadi_ban_{user_id}")
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
        firestore_helper.set_document(doc_id, orders_doc)
        
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
                if admin_chat_id:
                    await bot.send_message(
                        admin_chat_id, 
                        f"💰 **KeyVadi Otomatik Satış Bildirimi!**\n"
                        f"👤 **Kullanıcı:** `{user_id}`\n"
                        f"📦 **Ürün:** {unclaimed_order.get('product_name')}\n"
                        f"🔑 **Lisans Kodu:** `{license_key}` (Otomatik teslim edildi)\n"
                        f"💵 **Tutar:** {unclaimed_order.get('amount')} ₺\n"
                        f"📧 **E-posta/Telefon:** {input_val}"
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

        # Admin action buttons
        admin_buttons = [
            [
                Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"kv_adm_ban_{user_id}".encode())
            ]
        ]

        try:
            await bot.send_message(admin_chat_id, admin_msg, buttons=admin_buttons)
            await event.respond(t["support_success"])
            save_ticket_to_file("KeyVadi", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)

    if event.sender_id == admin_chat_id:
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
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
    firestore_helper.set_document(ban_doc_id, {"banned": True, "id": target_user_id})
    
    await event.answer("🚫 Kullanıcı engellendi.", alert=True)
    original_text = event.message.text
    await event.edit(f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

if __name__ == '__main__':
    logger.info("Loading KeyVadi products cache...")
    load_products_from_file_or_scrape()
    logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
