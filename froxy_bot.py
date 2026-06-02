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
logger = logging.getLogger("FroxyAIBot")

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

# 6 Products Catalog Data (Froxy AI Credit Packages)
PRODUCTS_DATA = {
    "baslangic": {
        "title": "Başlangıç Paketi",
        "price": "₺129.99",
        "desc": "• **Kredi/Kullanım:** 100,000 Kelime veya Görsel Üretim Kredisi.\n• **Özellikler:** Temel yapay zeka modellerine (GPT-3.5, Gemini Flash vb.) erişim.\n• **Garanti:** Anında aktivasyon, 7/24 kullanım.",
        "link_key": "baslangic"
    },
    "populer": {
        "title": "Popüler Paket",
        "price": "₺249.99",
        "desc": "• **Kredi/Kullanım:** 250,000 Kelime veya Görsel Üretim Kredisi.\n• **Özellikler:** Gelişmiş yapay zeka modellerine (GPT-4o, Claude 3.5, Gemini Ultra, Grok) erişim.\n• **Garanti:** Hızlı ve kesintisiz kullanım, öncelikli API erişimi.",
        "link_key": "populer"
    },
    "profesyonel": {
        "title": "Profesyonel Paket",
        "price": "₺449.99",
        "desc": "• **Kredi/Kullanım:** 600,000 Kredi.\n• **Özellikler:** Tüm gelişmiş AI modelleri, dosya analizi ve web arama özellikleri aktif.\n• **Garanti:** 7/24 kesintisiz destek ve kullanım.",
        "link_key": "profesyonel"
    },
    "gelistirici": {
        "title": "Geliştirici Paketi",
        "price": "₺599.99",
        "desc": "• **Kredi/Kullanım:** 1,000,000 Kredi.\n• **Özellikler:** API erişim anahtarı (v1 API), tüm modellerde sınırsız sorgulama imkanı.\n• **Garanti:** API entegrasyon desteği ve yüksek limitler.",
        "link_key": "gelistirici"
    },
    "isletme": {
        "title": "İşletme Paketi",
        "price": "₺799.99",
        "desc": "• **Kredi/Kullanım:** 2,000,000 Kredi.\n• **Özellikler:** Çoklu kullanıcı desteği, ortak çalışma alanı paneli, API entegrasyonu ve kurumsal kontrol.\n• **Garanti:** Özel müşteri temsilcisi ve kesintisiz kurumsal destek.",
        "link_key": "isletme"
    },
    "kurumsal": {
        "title": "Kurumsal Paket",
        "price": "₺1499.99",
        "desc": "• **Kredi/Kullanım:** 5,000,000 Kredi.\n• **Özellikler:** Özel modeller ince ayar (fine-tuning) desteği, sınırsız API kullanımı, en yüksek hız ve kota limitleri.\n• **Garanti:** SLA garantili destek ve özel kurumsal altyapı.",
        "link_key": "kurumsal"
    }
}

welcome_text = (
    "🤖 **Froxy AI Müşteri Paneline Hoş Geldiniz!**\n\n"
    "En popüler yapay zeka modellerini tek bir panelden kullanmanızı sağlayan paketlerimiz ve API erişimlerimiz en uygun fiyatlarla burada!\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Paket Seçenekleri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")]
    ]
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Paket Seçenekleri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & İletişim", b"menu_support")]
    ]
    await event.edit(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    buttons = [
        [Button.inline("🤖 Başlangıç Paketi (₺129.99)", b"pkg_baslangic")],
        [Button.inline("🔥 Popüler Paket (₺249.99)", b"pkg_populer")],
        [Button.inline("💼 Profesyonel Paket (₺449.99)", b"pkg_profesyonel")],
        [Button.inline("💻 Geliştirici Paketi (₺599.99)", b"pkg_gelistirici")],
        [Button.inline("🏢 İşletme Paketi (₺799.99)", b"pkg_isletme")],
        [Button.inline("👑 Kurumsal Paket (₺1499.99)", b"pkg_kurumsal")],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await event.edit("💳 **Froxy AI Paket Seçenekleri**\n\nDetaylarını incelemek ve satın almak istediğiniz paketi seçiniz:", buttons=buttons)

# Direct package details helper
async def show_package_details(event, key):
    p_data = PRODUCTS_DATA.get(key)
    if not p_data:
        await event.answer("Ürün bulunamadı!", alert=True)
        return
        
    config = load_config() or {}
    links = config.get("shopier_links", SHOPIER_LINKS)
    shopier_url = links.get(p_data["link_key"], "https://www.shopier.com/keyvadi")
    
    text = (
        f"🌟 **{p_data['title']}**\n\n"
        f"💰 **Fiyat:** {p_data['price']}\n\n"
        f"📝 **Özellikler & Garanti Detayları:**\n{p_data['desc']}\n\n"
        f"Satın almak için aşağıdaki butona tıklayabilirsiniz. Ödeme sonrasında teslimat anında gerçekleştirilir."
    )
    buttons = [
        [Button.url("💳 Shopier ile Güvenli Satın Al", shopier_url)],
        [Button.inline("↩️ Paketlere Dön", b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)

# Package detail Callback Handler
@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    full_pkg_data = event.data.decode('utf-8')
    pkg_key = full_pkg_data.replace("pkg_", "")
    await show_package_details(event, pkg_key)


# Support Menu
@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"
    
    text = (
        "📞 **Destek Talebi & Sipariş Verme**\n\n"
        "Lütfen satın almak istediğiniz diğer ürünü (Örn: Eski Gmail, YouTube Premium vb.) veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\n"
        "Mesajınız doğrudan admin ekibimize iletilecektir. En kısa sürede bu sohbet üzerinden yanıt alacaksınız."
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
                    await bot.send_message(target_user_id, f"📨 **Destek Ekibinden Cevap:**\n\n{event.text}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")

if __name__ == '__main__':
    logger.info("Starting Froxy AI Customer Bot...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
