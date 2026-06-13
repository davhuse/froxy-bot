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
        logging.FileHandler("froxy_destek_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FroxyDestekBot")

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

BOT_TOKEN = config.get("froxy_bot_token", "")
ADMIN_ID = config.get("froxy_admin_id", config.get("admin_id", 0))

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("Invalid Froxy Bot Token in config (froxy_bot_token). Please set it via Web Panel.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient('froxy_destek_session', API_ID, API_HASH)

# ═══════════════════════════════════════════════════════════════
# Froxy AI Kredi Paketleri — froxyai.com
# ═══════════════════════════════════════════════════════════════

PRODUCTS_DATA = {
    "baslangic": {
        "title": "Başlangıç Paketi",
        "price": "₺129.99",
        "credits": "5.000",
        "desc": (
            "• **Kredi:** 5.000 kredi\n"
            "• **Modeller:** Tüm AI modellere erişim (ChatGPT, Claude, Gemini, DeepSeek, Llama)\n"
            "• **Günlük Limit:** 200 istek/gün\n"
            "• **Destek:** Topluluk desteği\n"
            "• **Garanti:** Anında kredi tanımlama, Shopier güvenli ödeme"
        ),
    },
    "populer": {
        "title": "Popüler Paket ⭐",
        "price": "₺249.99",
        "credits": "15.000",
        "desc": (
            "• **Kredi:** 15.000 kredi\n"
            "• **Modeller:** Tüm AI modellere erişim\n"
            "• **Günlük Limit:** 500 istek/gün\n"
            "• **Ekstra:** Görsel üretim dahil\n"
            "• **Garanti:** Anında kredi tanımlama, Shopier güvenli ödeme"
        ),
    },
    "profesyonel": {
        "title": "Profesyonel Paket",
        "price": "₺449.99",
        "credits": "50.000",
        "desc": (
            "• **Kredi:** 50.000 kredi\n"
            "• **Modeller:** Tüm AI modellere erişim\n"
            "• **Günlük Limit:** 1.500 istek/gün\n"
            "• **Ekstra:** Öncelikli destek\n"
            "• **Garanti:** Anında kredi tanımlama, Shopier güvenli ödeme"
        ),
    },
}

welcome_text = (
    "🤖 **Froxy AI Destek Paneline Hoş Geldiniz!**\n\n"
    "ChatGPT, Claude, Gemini ve 400+ AI modelini tek panelden kullanmanızı sağlayan "
    "kredi paketlerimiz en uygun fiyatlarla burada!\n\n"
    "🌐 **Web Sitemiz:** froxyai.com\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Kredi Paketleri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")],
        [Button.url("🌐 froxyai.com'u Ziyaret Et", "https://froxyai.com")]
    ]
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Kredi Paketleri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")],
        [Button.url("🌐 froxyai.com'u Ziyaret Et", "https://froxyai.com")]
    ]
    await event.edit(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    buttons = [
        [Button.inline("🚀 Başlangıç — 5K Kredi (₺129.99)", b"pkg_baslangic")],
        [Button.inline("⭐ Popüler — 15K Kredi (₺249.99)", b"pkg_populer")],
        [Button.inline("💼 Profesyonel — 50K Kredi (₺449.99)", b"pkg_profesyonel")],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    text = (
        "💳 **Froxy AI Kredi Paketleri**\n\n"
        "Tüm paketlerde ChatGPT, Claude, Gemini, DeepSeek ve 400+ AI modele erişim!\n"
        "Yeni üyeler 100 ücretsiz krediyle başlar.\n\n"
        "Detaylarını görmek istediğiniz paketi seçin:"
    )
    await event.edit(text, buttons=buttons)

# Package detail handler
@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    pkg_key = event.data.decode('utf-8').replace("pkg_", "")
    p_data = PRODUCTS_DATA.get(pkg_key)
    if not p_data:
        await event.answer("Paket bulunamadı!", alert=True)
        return

    # Get Shopier link from config
    config = load_config() or {}
    froxy_links = config.get("froxy_shopier_links", {})
    shopier_url = froxy_links.get(pkg_key, "https://www.shopier.com/froxyai")

    text = (
        f"🌟 **{p_data['title']}**\n\n"
        f"💰 **Fiyat:** {p_data['price']}\n"
        f"🎯 **Kredi:** {p_data['credits']}\n\n"
        f"📝 **Detaylar:**\n{p_data['desc']}\n\n"
        f"Satın almak için aşağıdaki butona tıklayın. Ödeme sonrası krediniz anında tanımlanır."
    )
    buttons = [
        [Button.url("💳 Shopier ile Güvenli Satın Al", shopier_url)],
        [Button.url("🌐 froxyai.com'dan Satın Al", "https://froxyai.com")],
        [Button.inline("↩️ Paketlere Dön", b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)


# Support Menu
@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"

    text = (
        "📞 **Froxy AI Destek Talebi**\n\n"
        "Kredi paketi, hesap sorunu veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\n"
        "Mesajınız doğrudan Froxy AI ekibimize iletilecektir. En kısa sürede yanıt alacaksınız."
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
        admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))

        if not admin_chat_id:
            await event.respond("⚠️ Üzgünüz, şu anda destek sistemi aktif değil. Lütfen daha sonra deneyin.")
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
            f"--------------------------------------\n\n"
            f"{event.text}\n\n"
            f"*(Bu mesajı yanıtlayarak (Reply) doğrudan kullanıcıya cevap gönderebilirsiniz.)*"
        )

        try:
            await bot.send_message(admin_chat_id, admin_msg)
            await event.respond("✅ Mesajınız Froxy AI ekibine iletildi. En kısa sürede yanıt alacaksınız.")
            save_ticket_to_file("Froxy AI", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond("⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.")

        user_states[user_id] = None
        return

    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))

    if event.sender_id == admin_chat_id and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.text:
            match = re.search(r"Kullanıcı ID:\*\* `(\d+)`", reply_msg.text)
            if not match:
                match = re.search(r"Kullanıcı ID: (\d+)", reply_msg.text)

            if match:
                target_user_id = int(match.group(1))
                try:
                    await bot.send_message(target_user_id, f"📨 **Froxy AI Destek Ekibinden Cevap:**\n\n{event.text}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")

if __name__ == '__main__':
    logger.info("Starting Froxy AI Support Bot (@FroxyDestekBOT)...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
