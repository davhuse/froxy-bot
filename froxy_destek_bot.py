import os
import json
import logging
import re
from telethon import TelegramClient, events, Button
import user_lang_helper

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

TEXTS = {
    "tr": {
        "welcome": (
            "🤖 **Froxy AI Destek Paneline Hoş Geldiniz!**\n\n"
            "ChatGPT, Claude, Gemini ve 400+ AI modelini tek panelden kullanmanızı sağlayan "
            "kredi paketlerimiz en uygun fiyatlarla burada!\n\n"
            "🌐 **Web Sitemiz:** froxyai.com\n\n"
            "Lütfen yapmak istediğiniz işlemi seçin 👇"
        ),
        "packages_btn": "💳 Kredi Paketleri & Satın Al",
        "support_btn": "📞 Canlı Destek & İletişim",
        "web_btn": "🌐 froxyai.com'u Ziyaret Et",
        "lang_btn": "🌐 Dil Seçimi / Language",
        "main_menu": "↩️ Ana Menü",
        "pkg_btn_list": [
            ("🚀 Başlangıç — 5K Kredi (₺129.99)", "pkg_baslangic"),
            ("⭐ Popüler — 15K Kredi (₺249.99)", "pkg_populer"),
            ("💼 Profesyonel — 50K Kredi (₺449.99)", "pkg_profesyonel")
        ],
        "pkg_menu_title": "💳 **Froxy AI Kredi Paketleri**\n\n"
                          "Tüm paketlerde ChatGPT, Claude, Gemini, DeepSeek ve 400+ AI modele erişim!\n"
                          "Yeni üyeler 100 ücretsiz krediyle başlar.\n\n"
                          "Detaylarını görmek istediğiniz paketi seçin:",
        "back_to_pkgs": "↩️ Paketlere Dön",
        "buy_shopier": "💳 Shopier ile Güvenli Satın Al",
        "buy_web": "🌐 froxyai.com'dan Satın Al",
        "product_header": "🌟 **{title}**\n\n💰 **Fiyat:** {price}\n🎯 **Kredi:** {credits}\n\n📝 **Detaylar:**\n{desc}\n\nSatın almak için aşağıdaki butona tıklayın. Ödeme sonrası krediniz anında tanımlanır.",
        "support_title": "📞 **Froxy AI Destek Talebi**",
        "support_desc": "Kredi paketi, hesap sorunu veya destek talebinizi detaylıca yazıp bu sohbete gönderin.\n\nMesajınız doğrudan Froxy AI ekibimize iletilecektir. En kısa sürede yanıt alacaksınız.",
        "cancel": "↩️ Vazgeç ve İptal Et",
        "support_success": "✅ Mesajınız Froxy AI ekibine iletildi. En kısa sürede yanıt alacaksınız.",
        "support_fail": "⚠️ Mesajınız iletilemedi. Lütfen daha sonra tekrar deneyiniz.",
        "support_inactive": "⚠️ Üzgünüz, şu anda destek sistemi aktif değil. Lütfen daha sonra deneyin.",
        "reply_prefix": "📨 **Froxy AI Destek Ekibinden Cevap:**\n\n",
        "choose_lang": "Lütfen dilinizi seçin / Please choose your language:",
        "products": {
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
            }
        }
    },
    "en": {
        "welcome": (
            "🤖 **Welcome to Froxy AI Support Panel!**\n\n"
            "Our credit packages that allow you to use ChatGPT, Claude, Gemini, and 400+ AI models from a single panel are here at the most affordable prices!\n\n"
            "🌐 **Our Website:** froxyai.com\n\n"
            "Please select the action you want to perform 👇"
        ),
        "packages_btn": "💳 Credit Packages & Purchase",
        "support_btn": "📞 Live Support & Contact",
        "web_btn": "🌐 Visit froxyai.com",
        "lang_btn": "🌐 Language / Dil",
        "main_menu": "↩️ Main Menu",
        "pkg_btn_list": [
            ("🚀 Starter — 5K Credits ($3.99)", "pkg_baslangic"),
            ("⭐ Popular — 15K Credits ($7.99)", "pkg_populer"),
            ("💼 Professional — 50K Credits ($13.99)", "pkg_profesyonel")
        ],
        "pkg_menu_title": "💳 **Froxy AI Credit Packages**\n\n"
                          "Access ChatGPT, Claude, Gemini, DeepSeek, and 400+ AI models in all packages!\n"
                          "New members start with 100 free credits.\n\n"
                          "Select the package you want to view details:",
        "back_to_pkgs": "↩️ Back to Packages",
        "buy_shopier": "💳 Secure Purchase with Shopier",
        "buy_web": "🌐 Purchase from froxyai.com",
        "product_header": "🌟 **{title}**\n\n💰 **Price:** {price}\n🎯 **Credits:** {credits}\n\n📝 **Details:**\n{desc}\n\nClick the button below to purchase. Your credits will be assigned instantly after payment.",
        "support_title": "📞 **Froxy AI Support Request**",
        "support_desc": "Please write the credit package, account issue, or support request in detail and send it to this chat.\n\nYour message will be forwarded directly to our Froxy AI team. You will receive a response as soon as possible.",
        "cancel": "↩️ Cancel & Go Back",
        "support_success": "✅ Your message has been forwarded to the Froxy AI team. You will receive a response as soon as possible.",
        "support_fail": "⚠️ Your message could not be delivered. Please try again later.",
        "support_inactive": "⚠️ Sorry, the support system is currently offline. Please try again later.",
        "reply_prefix": "📨 **Reply from Froxy AI Support Team:**\n\n",
        "choose_lang": "Please choose your language / Lütfen dilinizi seçin:",
        "products": {
            "baslangic": {
                "title": "Starter Package",
                "price": "$3.99",
                "credits": "5,000",
                "desc": (
                    "• **Credits:** 5,000 credits\n"
                    "• **Models:** Access to all AI models (ChatGPT, Claude, Gemini, DeepSeek, Llama)\n"
                    "• **Daily Limit:** 200 requests/day\n"
                    "• **Support:** Community support\n"
                    "• **Guarantee:** Instant credit assignment, Shopier secure payment"
                ),
            },
            "populer": {
                "title": "Popular Package ⭐",
                "price": "$7.99",
                "credits": "15,000",
                "desc": (
                    "• **Credits:** 15,000 credits\n"
                    "• **Models:** Access to all AI models\n"
                    "• **Daily Limit:** 500 requests/day\n"
                    "• **Extra:** Image generation included\n"
                    "• **Guarantee:** Instant credit assignment, Shopier secure payment"
                ),
            },
            "profesyonel": {
                "title": "Professional Package",
                "price": "$13.99",
                "credits": "50,000",
                "desc": (
                    "• **Credits:** 50,000 credits\n"
                    "• **Models:** Access to all AI models\n"
                    "• **Daily Limit:** 1,500 requests/day\n"
                    "• **Extra:** Priority support\n"
                    "• **Guarantee:** Instant credit assignment, Shopier secure payment"
                ),
            }
        }
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
    
    welcome_text = t["welcome"]
    buttons = [
        [Button.inline(t["packages_btn"], b"menu_packages")],
        [Button.inline(t["support_btn"], b"menu_support")],
        [Button.inline(t["lang_btn"], b"menu_lang")],
        [Button.url(t["web_btn"], "https://froxyai.com")]
    ]
    
    if is_callback:
        await event.edit(welcome_text, buttons=buttons)
    else:
        await event.respond(welcome_text, buttons=buttons)

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

@bot.on(events.CallbackQuery(data=b'menu_packages'))
async def packages_menu_handler(event):
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]

    buttons = []
    for label, pkg_key in t["pkg_btn_list"]:
        buttons.append([Button.inline(label, pkg_key.encode())])
    buttons.append([Button.inline(t["main_menu"], b"menu_main")])

    await event.edit(t["pkg_menu_title"], buttons=buttons)

# Package detail handler
@bot.on(events.CallbackQuery(pattern=r'pkg_(\w+)'))
async def pkg_select_handler(event):
    user_id = event.sender_id
    lang = user_lang_helper.get_user_lang(user_id) or "tr"
    t = TEXTS[lang]

    pkg_key = event.data.decode('utf-8').replace("pkg_", "")
    p_data = t["products"].get(pkg_key)
    if not p_data:
        err_msg = "Paket bulunamadı!" if lang == "tr" else "Package not found!"
        await event.answer(err_msg, alert=True)
        return

    # Get Shopier link from config
    config = load_config() or {}
    froxy_links = config.get("froxy_shopier_links", {})
    shopier_url = froxy_links.get(pkg_key, "https://www.shopier.com/froxyai")

    text = t["product_header"].format(
        title=p_data['title'],
        price=p_data['price'],
        credits=p_data['credits'],
        desc=p_data['desc']
    )
    
    buttons = [
        [Button.url(t["buy_shopier"], shopier_url)],
        [Button.url(t["buy_web"], "https://froxyai.com")],
        [Button.inline(t["back_to_pkgs"], b"menu_packages")]
    ]
    await event.edit(text, buttons=buttons)

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
        admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
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
            f"📩 **Yeni Froxy AI Destek Talebi!**\n"
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
            save_ticket_to_file("Froxy AI", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

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
                target_lang = user_lang_helper.get_user_lang(target_user_id) or "tr"
                prefix = TEXTS[target_lang]["reply_prefix"]
                try:
                    await bot.send_message(target_user_id, f"{prefix}{event.text}")
                    await event.reply("✅ Cevabınız kullanıcıya iletildi.")
                except Exception as e:
                    logger.error(f"Failed to reply to user {target_user_id}: {e}")
                    await event.reply(f"❌ Cevap iletilemedi. Hata: {e}")

if __name__ == '__main__':
    logger.info("Starting Froxy AI Support Bot (@FroxyDestekBOT)...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
