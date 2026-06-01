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
logger = logging.getLogger("FroxyBot")

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
CONFIG_FILE = "bot_config.json"

# Load config
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

welcome_text = (
    "🤖 **Froxy Premium Müşteri Paneline Hoş Geldiniz!**\n\n"
    "Yapay zeka, eğlence, eğitim paketleri ve özel indirim kuponları için tek adresiniz!\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

packages_text = (
    "💳 **Froxy Premium Paket Listesi**\n\n"
    "Aşağıda yer alan paketlerden dilediğinizi seçerek özelliklerini inceleyebilir ve güvenle satın alabilirsiniz:"
)

# Callbacks and command handlers
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None  # Clear state
    buttons = [
        [Button.inline("💳 Paketler & Satın Al", b"menu_packages")],
        [Button.inline("📞 Destek Talebi Aç", b"menu_support")]
    ]
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Paketler & Satın Al", b"menu_packages")],
        [Button.inline("📞 Destek Talebi Aç", b"menu_support")]
    ]
    await event.edit(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    buttons = [
        [Button.inline("🤖 AI Pack (₺399.00/3 Ay)", b"pkg_baslangic")],
        [Button.inline("🎬 Entertainment Pack (₺399.00/3 Ay)", b"pkg_populer")],
        [Button.inline("🎓 Learning Pack (₺399.00/3 Ay)", b"pkg_profesyonel")],
        [Button.inline("📈 TradingView Premium (₺399.00/3 Ay)", b"pkg_gelistirici")],
        [Button.inline("🍔 Yemek & Market İndirimi (₺129.00)", b"pkg_isletme")],
        [Button.inline("🔥 Combo Paket (₺1899.00/12 Ay)", b"pkg_kurumsal")],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await event.edit(packages_text, buttons=buttons)

# Package details handler
async def show_package_details(event, name, title, price, desc, link_key):
    config = load_config() or {}
    links = config.get("shopier_links", SHOPIER_LINKS)
    shopier_url = links.get(link_key, "https://www.shopier.com")
    
    text = (
        f"🌟 **{title}**\n\n"
        f"💰 **Fiyat:** {price}\n"
        f"📝 **Özellikler:**\n{desc}\n\n"
        f"Satın almak için aşağıdaki butona tıklayabilirsiniz. Ödeme sonrasında teslimat anında gerçekleştirilir."
    )
    buttons = [
        [Button.url("💳 Shopier ile Güvenli Satın Al", shopier_url)],
        [Button.inline("↩️ Paket Listesi", b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    pkg_type = event.data.decode('utf-8').split('_')[1]
    
    if pkg_type == "baslangic":
        await show_package_details(
            event, "baslangic", "AI Pack (3 Aylık)", "₺399.00 / 3 Ay",
            "• CG-AI (OpenAI ChatGPT)\n• Cloudyee (Claude AI)\n• Ghaspher AI (Jasper AI)\n• Gryok (Grok AI)\n• Kaanvah Pro (Canva Pro)\n\n*Tek hesapla en popüler 5 yapay zeka aracına kesintisiz erişim!*",
            "baslangic"
        )
    elif pkg_type == "populer":
        await show_package_details(
            event, "populer", "Entertainment Pack (3 Aylık)", "₺399.00 / 3 Ay",
            "• Netflix 4K Ultra HD\n• Crunchyroll Premium\n• YouTube Premium\n• Tidal Music\n• Prime Video\n• Apple Music & TV\n\n*Dizi, film, müzik ve eğlence platformlarının tamamı tek pakette!*",
            "populer"
        )
    elif pkg_type == "profesyonel":
        await show_package_details(
            event, "profesyonel", "Learning Pack (3 Aylık)", "₺399.00 / 3 Ay",
            "• Scribd Premium\n• Skillshare Premium\n• Coursera\n• Super Duolingo\n• Adobe Creative\n• Udemy\n\n*Kendini geliştirmek isteyenler için harika bir öğrenme kütüphanesi!*",
            "profesyonel"
        )
    elif pkg_type == "gelistirici":
        await show_package_details(
            event, "gelistirici", "TradingView Premium (3 Aylık)", "₺399.00 / 3 Ay",
            "• TradingView Premium Özellikleri\n• Profesyonel İndikatörler & Grafikler\n• Cookie Tabanlı Hızlı Erişim Desteği",
            "gelistirici"
        )
    elif pkg_type == "isletme":
        await show_package_details(
            event, "isletme", "Yemek & Market İndirim Paketi", "₺129.00",
            "• Trendyol Go / Uber Eats Yemek Siparişlerinde 700 TL'ye 250 TL İndirim\n• Trendyol Go / Uber Eats Market Siparişlerinde 900 TL'ye 250 TL İndirim\n• 3 Aylık YouTube Premium & 4 Aylık Spotify Premium Kodları\n• Shell 75 TL Değerinde Akaryakıt Puanı\n• 3 Aylık Exxen Reklamsız Üyelik",
            "isletme"
        )
    elif pkg_type == "kurumsal":
        await show_package_details(
            event, "kurumsal", "Combo Paket (12 Aylık)", "₺1899.00 / 12 Ay",
            "• Tüm 22 Servis ve Paketin Tamamı Dahil!\n• 12 Ay Boyunca Kesintisiz Garanti ve Erişim\n• AI Pack + Entertainment Pack + Learning Pack + TradingView Premium + İndirim Paketleri\n\n*En popüler ve en avantajlı kombine paketimizdir!*",
            "kurumsal"
        )

@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"
    
    text = (
        "📞 **Destek Talebi Oluşturma**\n\n"
        "Lütfen destek ekibimize iletmek istediğiniz mesajı detaylıca yazıp bu sohbete gönderin.\n\n"
        "Mesajınızı gönderdikten sonra ekibimiz en kısa sürede size bu sohbet üzerinden yanıt verecektir."
    )
    buttons = [
        [Button.inline("↩️ Vazgeç ve İptal Et", b"menu_main")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    
    # Check if the user is a normal user sending a support ticket
    if user_states.get(user_id) == "AWAITING_SUPPORT":
        # Check if the user clicked cancel or sent a command
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
        
        # Forward message details to admin
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
            await event.respond("✅ Destek talebiniz ekibimize iletildi. En kısa sürede yanıt alacaksınız.")
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond("⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.")
            
        user_states[user_id] = None
        return

    # Check if this is an admin replying to a ticket
    config = load_config() or {}
    admin_chat_id = config.get("admin_id", ADMIN_ID)
    
    if event.sender_id == admin_chat_id and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.text:
            # Parse user_id from the original notification message
            match = re.search(r"Kullanıcı ID:\*\* `(\d+)`", reply_msg.text)
            if not match:
                match = re.search(r"Kullanıcı ID: (\d+)", reply_msg.text)
                
            if match:
                target_user_id = int(match.group(1))
                try:
                    await bot.send_message(target_user_id, f"📨 **Destek Ekibinden Cevap:**\n\n{event.text}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")

if __name__ == '__main__':
    logger.info("Starting Froxy Customer Bot...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
