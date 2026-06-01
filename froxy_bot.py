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
    "En popüler dijital premium üyelikler, yapay zeka hesapları ve indirim kuponları en uygun fiyatlarla burada!\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

# Callbacks and command handlers
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None  # Clear state
    buttons = [
        [Button.inline("💳 Ürün Kategorileri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & Sipariş", b"menu_support")]
    ]
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_main'))
async def main_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
    buttons = [
        [Button.inline("💳 Ürün Kategorileri & Satın Al", b"menu_packages")],
        [Button.inline("📞 Canlı Destek & Sipariş", b"menu_support")]
    ]
    await event.edit(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    buttons = [
        [Button.inline("🤖 Yapay Zeka (AI) Araçları", b"cat_ai")],
        [Button.inline("🎬 Eğlence & Sinema & Müzik", b"cat_ent")],
        [Button.inline("🎨 Tasarım & Video Edit", b"cat_design")],
        [Button.inline("📱 Onaylı No & Mail", b"cat_accounts")],
        [Button.inline("🍔 Yemek & Akaryakıt Kuponları", b"cat_coupons")],
        [Button.inline("🎓 Eğitim & Yazılımlar", b"cat_learning")],
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await event.edit("💳 **Froxy Premium Ürün Kategorileri**\n\nDetaylarını incelemek ve satın almak istediğiniz kategoriye tıklayınız:", buttons=buttons)

# Direct package details helper
async def show_package_details(event, title, price, desc, link_key):
    config = load_config() or {}
    links = config.get("shopier_links", SHOPIER_LINKS)
    shopier_url = links.get(link_key, "https://www.shopier.com")
    
    text = (
        f"🌟 **{title}**\n\n"
        f"💰 **Fiyat:** {price}\n"
        f"📝 **Özellikler & Garanti:**\n{desc}\n\n"
        f"Satın almak için aşağıdaki butona tıklayabilirsiniz. Ödeme sonrasında teslimat anında gerçekleştirilir."
    )
    buttons = [
        [Button.url("💳 Shopier ile Güvenli Satın Al", shopier_url)],
        [Button.inline("↩️ Kategorilere Dön", b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r'cat_(\w+)'))
async def category_select_handler(event):
    cat_type = event.data.decode('utf-8').split('_')[1]
    
    if cat_type == "ai":
        text = (
            "🤖 **Yapay Zeka (AI) Araçları Fiyat Listesi**\n\n"
            "• **ChatGPT Plus:** ₺199.99 *(Giriş + 3 Gün Garanti)*\n"
            "• **Gemini Pro (1 Yıllık Hesap):** ₺299.99 *(Giriş Garantili)*\n"
            "• **Gemini Pro (Davet):** ₺124.99 *(Giriş Garantili)*\n"
            "• **Gemini Ultra (Davet):** ₺399.99 *(Full Garanti)*\n"
            "• **Gemini Ultra (2.5k Kredili):** ₺599.99 *(Full Garanti)*\n"
            "• **Super Grok (1 Aylık):** ₺449.99 *(Giriş Garantili)*\n"
            "• **Super Grok (3 Aylık):** ₺949.99 *(15 Gün Garanti)*\n"
            "• **Super Grok (6 Aylık):** ₺1499.99 *(3 Hafta Garanti)*\n"
            "• **Super Grok (12 Aylık):** ₺2299.99 *(3 Ay Garanti)*\n"
            "• **Gamma Ultra (1 Aylık):** ₺449.99\n"
            "• **Gamma Pro (1 Aylık):** ₺299.99\n\n"
            "Satın almak istediğiniz ürünü seçin 👇"
        )
        buttons = [
            [Button.inline("🤖 ChatGPT Plus (₺199.99)", b"pkg_baslangic")],
            [Button.inline("🤖 Gemini Pro Hesap (₺299.99)", b"pkg_populer")],
            [Button.inline("🤖 Grok 1 Aylık (₺449.99)", b"pkg_profesyonel")],
            [Button.inline("📞 Diğerleri İçin İletişime Geç", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "ent":
        text = (
            "🎬 **Eğlence, Sinema & Müzik Fiyat Listesi**\n\n"
            "• **Kişisel Netflix Profili:** ₺89.99 *(Full Garanti)*\n"
            "• **Spotify Premium (4 Aylık Kod):** ₺34.99 *(Kendi Hesabınıza)*\n"
            "• **YouTube Premium (3 Aylık Kod):** ₺44.99 *(Mevcut/Yeni Hesaba)*\n"
            "• **Exxen Reklamsız (3 Aylık):** ₺34.99\n\n"
            "Satın almak istediğiniz ürünü seçin 👇"
        )
        buttons = [
            [Button.inline("🎬 Netflix Profili (₺89.99)", b"pkg_gelistirici")],
            [Button.inline("🎵 Spotify Premium 4 Ay (₺34.99)", b"pkg_isletme")],
            [Button.inline("🔴 YouTube Premium 3 Ay (₺44.99)", b"pkg_kurumsal")],
            [Button.inline("📞 Diğerleri İçin İletişime Geç", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "design":
        text = (
            "🎨 **Tasarım & Video Edit Fiyat Listesi**\n\n"
            "• **Canva Pro (1 Yıllık):** ₺79.99\n"
            "• **Adobe Express (3 Aylık):** ₺99.99 *(1 Hafta Garanti)*\n"
            "• **Adobe Creative Cloud (Tüm Uygulamalar):**\n"
            "  - 1 Haftalık: ₺69.99 *(1 Hafta Garanti)*\n"
            "  - 1 Aylık: ₺119.99 *(1 Hafta Garanti)*\n"
            "  - 4 Aylık: ₺249.99 *(1 Hafta Garanti)*\n"
            "• **CapCut Pro (1 Haftalık Hesap):** ₺99.99 *(3 Gün Garanti)*\n"
            "• **Kiro (10k Kredili Hesap):** ₺499.99 *(Giriş Garantili)*\n\n"
            "Bu kategorideki ürünleri satın almak veya özel teklif almak için lütfen canlı desteğe yazınız 👇"
        )
        buttons = [
            [Button.inline("📞 Satın Al / Destek", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "accounts":
        text = (
            "📱 **Onaylı No & Mail Fiyat Listesi**\n\n"
            "• **ABD / Kanada Karma WhatsApp Numarası:** ₺149.99\n"
            "• **Türk Apple ID (iCloud Etkin):** ₺149.99 *(Giriş Garantili)*\n"
            "• **Eski Tarihli Gmail (2022-2024 Kurulu):** ₺59.99 *(Giriş Garantili)*\n\n"
            "Bu kategorideki ürünleri satın almak için lütfen canlı desteğe yazınız 👇"
        )
        buttons = [
            [Button.inline("📞 Satın Al / Destek", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "coupons":
        text = (
            "🍔 **Yemek & Akaryakıt Kuponları Fiyat Listesi**\n\n"
            "• **Trendyol Go Yemek (700 TL'ye 250 TL İndirim):** ₺14.99\n"
            "• **Trendyol Go Market (900 TL'ye 250 TL İndirim):** ₺14.99\n"
            "• **Uber Eats Yemek (700 TL'ye 250 TL İndirim):** ₺14.99\n"
            "• **Shell 75 TL Akaryakıt Puanı:** ₺14.99\n\n"
            "Bu kategorideki kuponları temin etmek için lütfen canlı desteğe yazınız 👇"
        )
        buttons = [
            [Button.inline("📞 Satın Al / Destek", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "learning":
        text = (
            "🎓 **Eğitim & Yazılımlar Fiyat Listesi**\n\n"
            "• **Duolingo Super Sınırsız:** ₺69.99\n"
            "• **Scribd Premium (3 Aylık):** ₺99.99\n"
            "• **Skillshare Premium (3 Aylık):** ₺99.99\n"
            "• **Coursera (3 Aylık):** ₺99.99\n"
            "• **Udemy (3 Aylık):** ₺99.99\n\n"
            "Eğitim hesaplarını ve yazılımları satın almak için lütfen canlı desteğe yazınız 👇"
        )
        buttons = [
            [Button.inline("📞 Satın Al / Destek", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    pkg_type = event.data.decode('utf-8').split('_')[1]
    
    if pkg_type == "baslangic":
        await show_package_details(
            event, "ChatGPT Plus", "₺199.99",
            "• Yapay zeka ile gelişmiş kod yazma, analiz ve görsel üretim.\n• Orijinal ChatGPT Plus özellikleri.\n• **Garanti:** Giriş garantisi ve 3 gün kullanım garantisi sağlanır.",
            "baslangic"
        )
    elif pkg_type == "populer":
        await show_package_details(
            event, "Gemini Pro Hesap", "₺299.99 / 1 Yıllık",
            "• Google'ın gelişmiş yapay zeka asistanı.\n• 1 Yıllık kullanım hesabı.\n• **Garanti:** Giriş garantilidir.",
            "populer"
        )
    elif pkg_type == "profesyonel":
        await show_package_details(
            event, "Super Grok (1 Aylık)", "₺449.99 / 1 Ay",
            "• X (Twitter) entegrasyonlu en güncel arama ve analiz yapay zekası.\n• **Garanti:** Giriş garantisi sağlanır.",
            "profesyonel"
        )
    elif pkg_type == "gelistirici":
        await show_package_details(
            event, "Kişisel Netflix Profili", "₺89.99",
            "• 4K Ultra HD çözünürlük desteği.\n• Ortak hesapta size ait özel profil ve şifreleme.\n• **Garanti:** Full kullanım garantilidir.",
            "gelistirici"
        )
    elif pkg_type == "isletme":
        await show_package_details(
            event, "Spotify Premium (4 Aylık Kod)", "₺34.99",
            "• Reklamsız ve yüksek kaliteli müzik keyfi.\n• Kendi kişisel hesabınıza tanımlanır.\n• **Garanti:** Giriş ve aktivasyon garantilidir.",
            "isletme"
        )
    elif pkg_type == "kurumsal":
        await show_package_details(
            event, "YouTube Premium (3 Aylık Kod)", "₺44.99",
            "• Arka planda oynatma ve reklamsız video keyfi.\n• YouTube Music Premium dahildir.\n• **Garanti:** Giriş ve aktivasyon garantilidir.",
            "kurumsal"
        )

@bot.on(events.CallbackQuery(data=b'menu_support'))
async def support_menu_handler(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_SUPPORT"
    
    text = (
        "📞 **Destek Talebi & Sipariş Verme**\n\n"
        "Lütfen satın almak istediğiniz diğer ürünü (Örn: Adobe CC, WhatsApp No, Yemek Kuponu, CapCut vb.) veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\n"
        "Mesajınız doğrudan admin ekibimize iletilecektir. En kısa sürede bu sohbet üzerinden yanıt alacaksınız."
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
            await event.respond("✅ Mesajınız ekibimize iletildi. En kısa sürede yanıt alacaksınız.")
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
