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

# 24 Products Catalog Data
PRODUCTS_DATA = {
    # YAPAY ZEKA
    "gemini_pro_1y": {
        "title": "Gemini Pro (1 Yıllık Hesap)",
        "price": "₺299.99",
        "desc": "• Google'ın gelişmiş yapay zeka asistanına kesintisiz erişim.\n• 1 Yıllık hazır kullanım hesabı.\n• **Garanti:** Giriş garantilidir.",
        "link_key": "gemini_pro_1y"
    },
    "gemini_pro_davet": {
        "title": "Gemini Pro (Davet Linki)",
        "price": "₺124.99",
        "desc": "• Davet linki ile kendi kişisel Google hesabınızı aktifleştirin.\n• **Garanti:** Giriş garantilidir.",
        "link_key": "gemini_pro_davet"
    },
    "gemini_ultra_davet": {
        "title": "Gemini Ultra (Davet Linki)",
        "price": "₺399.90",
        "desc": "• Google'ın en gelişmiş yapay zeka modeli.\n• Kendi kişisel hesabınıza davet linki.\n• **Garanti:** Full kullanım garantisi sağlanır.",
        "link_key": "gemini_ultra_davet"
    },
    "gemini_ultra_25k": {
        "title": "Gemini Ultra (2.5k Kredili Hesap)",
        "price": "₺599.99",
        "desc": "• Google Gemini Ultra 2500 kredili kullanım hesabı.\n• **Garanti:** Full kullanım garantisi sağlanır.",
        "link_key": "gemini_ultra_25k"
    },
    "grok_1m": {
        "title": "Super Grok (1 Aylık Hesap)",
        "price": "₺449.99",
        "desc": "• X (Twitter) entegrasyonlu yapay zeka modeli.\n• 1 Aylık kullanım hesabı.\n• **Garanti:** Giriş garantilidir.",
        "link_key": "grok_1m"
    },
    "grok_3m": {
        "title": "Super Grok (3 Aylık Hesap)",
        "price": "₺949.99",
        "desc": "• X (Twitter) entegrasyonlu yapay zeka modeli.\n• 3 Aylık kullanım hesabı.\n• **Garanti:** 15 gün kullanım garantisi sağlanır.",
        "link_key": "grok_3m"
    },
    "grok_6m": {
        "title": "Super Grok (6 Aylık Hesap)",
        "price": "₺1499.99",
        "desc": "• X (Twitter) entegrasyonlu yapay zeka modeli.\n• 6 Aylık kullanım hesabı.\n• **Garanti:** 3 hafta kullanım garantisi sağlanır.",
        "link_key": "grok_6m"
    },
    "grok_12m": {
        "title": "Super Grok (12 Aylık Hesap)",
        "price": "₺2299.99",
        "desc": "• X (Twitter) entegrasyonlu yapay zeka modeli.\n• 12 Aylık kullanım hesabı.\n• **Garanti:** 3 ay kullanım garantisi sağlanır.",
        "link_key": "grok_12m"
    },
    "gamma_ultra": {
        "title": "Gamma Ultra (1 Aylık Hesap)",
        "price": "₺449.99",
        "desc": "• Yapay zeka ile sunum, döküman ve web sayfası oluşturma.\n• 1 Aylık Ultra özellikli kullanım hesabı.",
        "link_key": "gamma_ultra"
    },
    "gamma_pro": {
        "title": "Gamma Pro (1 Aylık Hesap)",
        "price": "₺299.99",
        "desc": "• Yapay zeka ile sunum, döküman ve web sayfası oluşturma.\n• 1 Aylık Pro özellikli kullanım hesabı.",
        "link_key": "gamma_pro"
    },
    "kiro": {
        "title": "Kiro (10k Kredili Hesap)",
        "price": "₺499.99",
        "desc": "• Kiro 10.000 kredili görsel ve video üretim hesabı.\n• **Garanti:** Giriş garantilidir.",
        "link_key": "kiro"
    },
    
    # TASARIM & VİDEO
    "canva": {
        "title": "Canva Pro (1 Yıllık Yetki)",
        "price": "₺79.99",
        "desc": "• Canva Pro 1 Yıllık Yetkilendirme.\n• Kendi kişisel hesabınıza tanımlanır.",
        "link_key": "canva"
    },
    "adobe_express": {
        "title": "Adobe Express (3 Aylık)",
        "price": "₺99.99",
        "desc": "• Adobe Express 3 Aylık Pro Üyelik.\n• Kendi hesabınıza tanımlanır.\n• **Garanti:** 1 hafta garanti sağlanır.",
        "link_key": "adobe_express"
    },
    "adobe_cc_1w": {
        "title": "Adobe Creative Cloud (1 Haftalık)",
        "price": "₺69.99",
        "desc": "• Adobe Creative Cloud Tüm Uygulamalar 1 Haftalık Üyelik.\n• Kendi kişisel hesabınıza tanımlanır.\n• **Garanti:** 1 hafta garanti sağlanır.",
        "link_key": "adobe_cc_1w"
    },
    "adobe_cc_1m": {
        "title": "Adobe Creative Cloud (1 Aylık)",
        "price": "₺119.99",
        "desc": "• Adobe Creative Cloud Tüm Uygulamalar 1 Aylık Üyelik.\n• Kendi kişisel hesabınıza tanımlanır.\n• **Garanti:** 1 hafta garanti sağlanır.",
        "link_key": "adobe_cc_1m"
    },
    "adobe_cc_4m": {
        "title": "Adobe Creative Cloud (4 Aylık)",
        "price": "₺249.99",
        "desc": "• Adobe Creative Cloud Tüm Uygulamalar 4 Aylık Üyelik.\n• Kendi kişisel hesabınıza tanımlanır.\n• **Garanti:** 1 hafta garanti sağlanır.",
        "link_key": "adobe_cc_4m"
    },
    "capcut": {
        "title": "CapCut Pro (1 Haftalık Hesap)",
        "price": "₺99.99",
        "desc": "• CapCut Pro 1 Haftalık Kullanım Hesabı.\n• **Garanti:** 3 gün kullanım garantisi sağlanır.",
        "link_key": "capcut"
    },
    
    # ONAYLI NUMARA
    "whatsapp": {
        "title": "ABD / Kanada Karma WhatsApp Numarası",
        "price": "₺149.99",
        "desc": "• ABD veya Kanada onay kodlu karma WhatsApp onay numarası.",
        "link_key": "whatsapp"
    },
    "apple_id": {
        "title": "Türk Apple ID (iCloud Etkin)",
        "price": "₺149.99",
        "desc": "• Türk Apple ID iCloud etkinleştirilmiş hazır hesap.\n• **Garanti:** Giriş garantilidir.",
        "link_key": "apple_id"
    },
    
    # KUPONLAR
    "trendyol_yemek": {
        "title": "Trendyol Go Yemek İndirim Kuponu (700 TL'ye 250 TL)",
        "price": "₺49.99",
        "desc": "• Trendyol Go Yemek siparişinde 700 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon.",
        "link_key": "trendyol_yemek"
    },
    "trendyol_market": {
        "title": "Trendyol Go Market İndirim Kuponu (900 TL'ye 250 TL)",
        "price": "₺49.99",
        "desc": "• Trendyol Go Market siparişinde 900 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon.",
        "link_key": "trendyol_market"
    },
    "shell": {
        "title": "Shell 75 TL Akaryakıt Puanı",
        "price": "₺14.99",
        "desc": "• Shell istasyonlarında geçerli 75 TL değerinde akaryakıt puanı.",
        "link_key": "shell"
    },
    
    # EGITIM & YAZILIM
    "duolingo": {
        "title": "Duolingo Super Sınırsız",
        "price": "₺69.99",
        "desc": "• Sınırsız can ve reklamsız dil eğitimi özellikleri aktif Duolingo Super.",
        "link_key": "duolingo"
    },
    "scribd": {
        "title": "Scribd Premium (3 Aylık)",
        "price": "₺99.99",
        "desc": "• Scribd 3 Aylık Premium Üyelik ile sesli kitap, e-kitap ve dökümanlara sınırsız erişim.",
        "link_key": "scribd"
    }
}

welcome_text = (
    "🤖 **KeyVadi Müşteri Paneline Hoş Geldiniz!**\n\n"
    "En popüler dijital premium üyelikler, yapay zeka hesapları ve indirim kuponları en uygun fiyatlarla burada!\n\n"
    "Lütfen yapmak istediğiniz işlemi seçin 👇"
)

# Start Handler
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = None
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
    await event.edit("💳 **KeyVadi Ürün Kategorileri**\n\nDetaylarını incelemek ve satın almak istediğiniz kategoriye tıklayınız:", buttons=buttons)

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
        [Button.inline("↩️ Kategorilere Dön", b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)

# Categories List
@bot.on(events.CallbackQuery(pattern=r'cat_(\w+)'))
async def category_select_handler(event):
    cat_type = event.data.decode('utf-8').split('_')[1]
    
    if cat_type == "ai":
        text = "🤖 **Yapay Zeka (AI) Araçları Fiyat Listesi**\n\nSatın almak veya incelemek istediğiniz ürünü seçin 👇"
        buttons = [
            [Button.inline("🤖 Gemini Pro 1 Yıl (₺299.99)", b"pkg_gemini_pro_1y")],
            [Button.inline("🔗 Gemini Pro Davet (₺124.99)", b"pkg_gemini_pro_davet")],
            [Button.inline("🔗 Gemini Ultra Davet (₺399.90)", b"pkg_gemini_ultra_davet")],
            [Button.inline("💎 Gemini Ultra 2.5k (₺599.99)", b"pkg_gemini_ultra_25k")],
            [Button.inline("⚡ Grok 1 Ay (₺449.99)", b"pkg_grok_1m"), Button.inline("⚡ Grok 3 Ay (₺949.99)", b"pkg_grok_3m")],
            [Button.inline("⚡ Grok 6 Ay (₺1499.99)", b"pkg_grok_6m"), Button.inline("⚡ Grok 12 Ay (₺2299.99)", b"pkg_grok_12m")],
            [Button.inline("📊 Gamma Pro (₺299.99)", b"pkg_gamma_pro"), Button.inline("📊 Gamma Ultra (₺449.99)", b"pkg_gamma_ultra")],
            [Button.inline("🎨 Kiro 10k Kredi (₺499.99)", b"pkg_kiro")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "ent":
        text = (
            "🎬 **Eğlence, Sinema & Müzik Ürünleri**\n\n"
            "YouTube Premium, Spotify Premium, Netflix, Exxen ve Crunchyroll üyelikleri çok yakında stoklarımızda yer alacaktır.\n\n"
            "Özel sipariş vermek veya bilgi almak için lütfen canlı desteğimize yazınız 👇"
        )
        buttons = [
            [Button.inline("📞 Satın Al / Destek", b"menu_support")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "design":
        text = "🎨 **Tasarım & Video Edit Fiyat Listesi**\n\nSatın almak veya incelemek istediğiniz ürünü seçin 👇"
        buttons = [
            [Button.inline("🖌️ Canva Pro 1 Yıl (₺79.99)", b"pkg_canva")],
            [Button.inline("📽️ CapCut Pro 1 Hafta (₺99.99)", b"pkg_capcut")],
            [Button.inline("🎨 Adobe Express 3 Ay (₺99.99)", b"pkg_adobe_express")],
            [Button.inline("🎨 Adobe CC 1 Hafta (₺69.99)", b"pkg_adobe_cc_1w")],
            [Button.inline("🎨 Adobe CC 1 Ay (₺119.99)", b"pkg_adobe_cc_1m")],
            [Button.inline("🎨 Adobe CC 4 Ay (₺249.99)", b"pkg_adobe_cc_4m")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "accounts":
        text = "📱 **Onaylı No & Mail Fiyat Listesi**\n\nSatın almak veya incelemek istediğiniz ürünü seçin 👇"
        buttons = [
            [Button.inline("📞 WhatsApp Onaylı No (₺149.99)", b"pkg_whatsapp")],
            [Button.inline("🍏 Türk Apple ID (₺149.99)", b"pkg_apple_id")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "coupons":
        text = "🍔 **Yemek & Akaryakıt Kuponları Fiyat Listesi**\n\nSatın almak veya incelemek istediğiniz ürünü seçin 👇"
        buttons = [
            [Button.inline("🍔 Trendyol Yemek (₺49.99)", b"pkg_trendyol_yemek")],
            [Button.inline("🛒 Trendyol Market (₺49.99)", b"pkg_trendyol_market")],
            [Button.inline("⛽ Shell 75 TL Yakıt (₺14.99)", b"pkg_shell")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif cat_type == "learning":
        text = "🎓 **Eğitim & Yazılımlar Fiyat Listesi**\n\nSatın almak veya incelemek istediğiniz ürünü seçin 👇"
        buttons = [
            [Button.inline("🦉 Duolingo Super (₺69.99)", b"pkg_duolingo")],
            [Button.inline("📚 Scribd Premium 3 Ay (₺99.99)", b"pkg_scribd")],
            [Button.inline("↩️ Kategoriler", b"menu_packages")]
        ]
        await event.edit(text, buttons=buttons)

# Package detail Callback Handler
@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    pkg_type = event.data.decode('utf-8').split('_')[1]
    # Reconstruct keys like gemini_pro_1y or grok_1m if they match
    # Since pkg_type could contain underscores, let's parse the rest of the string
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
    logger.info("Starting KeyVadi Customer Bot...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
