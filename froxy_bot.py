import os
import json
import logging
import re
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

CATEGORIES = {
    "ai": {
        "title": "🌟 Yapay Zeka (AI) Hesapları",
        "products": {
            "gemini_pro_1y": {"title": "Gemini Pro (1 Yıllık Hesap)", "price": "₺299.99"},
            "gemini_pro_davet": {"title": "Gemini Pro (Davet Linki)", "price": "₺124.99"},
            "gemini_ultra_davet": {"title": "Gemini Ultra (Davet Linki)", "price": "₺399.90"},
            "gemini_ultra_25k": {"title": "Gemini Ultra (2.5k Kredili)", "price": "₺599.99"},
            "grok_1m": {"title": "Super Grok — 1 Aylık", "price": "₺449.99"},
            "grok_3m": {"title": "Super Grok — 3 Aylık", "price": "₺949.99"},
            "grok_6m": {"title": "Super Grok — 6 Aylık", "price": "₺1499.99"},
            "grok_12m": {"title": "Super Grok — 12 Aylık", "price": "₺2299.99"},
            "gamma_ultra": {"title": "Gamma Ultra (1 Aylık)", "price": "₺449.99"},
            "gamma_pro": {"title": "Gamma Pro (1 Aylık)", "price": "₺299.99"},
            "kiro": {"title": "Kiro (10k Kredili Yapay Zeka)", "price": "₺499.99"},
        }
    },
    "design": {
        "title": "🎨 Tasarım & Lisans Hizmetleri",
        "products": {
            "canva": {"title": "Canva Pro (1 Yıllık Yetki)", "price": "₺79.99"},
            "adobe_express": {"title": "Adobe Express (3 Aylık Üyelik)", "price": "₺99.99"},
            "adobe_cc_1w": {"title": "Adobe Creative Cloud — 1 Haftalık", "price": "₺69.99"},
            "adobe_cc_1m": {"title": "Adobe Creative Cloud — 1 Aylık", "price": "₺119.99"},
            "adobe_cc_4m": {"title": "Adobe Creative Cloud — 4 Aylık", "price": "₺249.99"},
            "capcut": {"title": "CapCut Pro (1 Haftalık)", "price": "₺99.99"},
            "duolingo": {"title": "Duolingo Super Sınırsız", "price": "₺69.99"},
            "scribd": {"title": "Scribd Premium (3 Aylık)", "price": "₺99.99"},
        }
    },
    "mobile": {
        "title": "📱 Onaylı Mobil Hesaplar",
        "products": {
            "whatsapp": {"title": "ABD/Kanada Karma WhatsApp Numarası", "price": "₺149.99"},
            "apple_id": {"title": "Türk Apple ID (iCloud Etkin)", "price": "₺149.99"},
        }
    },
    "deals": {
        "title": "🍔 Yemek & Akaryakıt Fırsatları",
        "products": {
            "trendyol_yemek": {"title": "Trendyol Go Yemek (700₺'ye 250₺ İndirim)", "price": "₺49.99"},
            "trendyol_market": {"title": "Trendyol Go Market (900₺'ye 250₺ İndirim)", "price": "₺49.99"},
            "shell": {"title": "Shell 75 TL Akaryakıt Puanı", "price": "₺14.99"},
        }
    }
}

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
    buttons = [
        [Button.inline("🌟 Yapay Zeka (AI) Hesapları", b"cat_ai")],
        [Button.inline("🎨 Tasarım & Lisans Hizmetleri", b"cat_design")],
        [Button.inline("📱 Onaylı Mobil Hesaplar", b"cat_mobile")],
        [Button.inline("🍔 Yemek & Akaryakıt Fırsatları", b"cat_deals")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")]
    ]
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("🌟 Yapay Zeka (AI) Hesapları", b"cat_ai")],
        [Button.inline("🎨 Tasarım & Lisans Hizmetleri", b"cat_design")],
        [Button.inline("📱 Onaylı Mobil Hesaplar", b"cat_mobile")],
        [Button.inline("🍔 Yemek & Akaryakıt Fırsatları", b"cat_deals")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")]
    ]
    await event.edit(welcome_text, buttons=buttons)

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
    logger.info("Starting KeyVadi Sales Bot (@KeyVadiSatisBot)...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
