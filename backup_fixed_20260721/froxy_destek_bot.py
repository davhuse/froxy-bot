import os
import json
import logging
import re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import user_lang_helper
import firestore_helper

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
BOT_USER_ID = None

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.error("Invalid Froxy Bot Token in config (froxy_bot_token). Please set it via Web Panel.")
    exit(1)

# In-memory user state
user_states = {}

# Initialize client
bot = TelegramClient("froxy_destek_bot_session", API_ID, API_HASH)

TEXTS = {
    "tr": {
        "welcome": (
            "🤖 **Froxy AI Destek Paneline Hoş Geldiniz!**\n\n"
            "ChatGPT, Claude, Gemini ve 1100+ AI modelini tek panelden kullanmanızı sağlayan "
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
                          "Tüm paketlerde ChatGPT, Claude, Gemini, DeepSeek ve 1100+ AI modele erişim!\n"
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
            "Our credit packages that allow you to use ChatGPT, Claude, Gemini, and 1100+ AI models from a single panel are here at the most affordable prices!\n\n"
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
                          "Access ChatGPT, Claude, Gemini, DeepSeek, and 1100+ AI models in all packages!\n"
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
    
    presence = firestore_helper.get_document("habil_presence") or {}
    is_online = presence.get("is_online", False)
    status_emoji = "🟢 **Destek Çevrimiçi / Support Online**" if is_online else "🔴 **Destek Çevrimdışı / Support Offline**"
    
    welcome_text = (
        f"{status_emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t['welcome']}"
    )
    
    buttons = [
        [Button.inline(t["packages_btn"], b"menu_packages")],
        [Button.inline("💳 Ödememi Doğrula / Verify Payment", b"menu_verify_payment")],
        [Button.inline("👥 Arkadaşını Davet Et / Invite Friends", b"menu_referral")],
        [Button.inline(t["support_btn"], b"menu_support")],
        [Button.inline(t["lang_btn"], b"menu_lang")],
        [Button.url(t["web_btn"], "https://froxyai.com")]
    ]
    
    if is_callback:
        await event.edit(welcome_text, buttons=buttons)
    else:
        await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_verify_payment'))
async def verify_payment_callback(event):
    user_id = event.sender_id
    user_states[user_id] = "AWAITING_VERIFY_PAYMENT_INFO"
    
    text = (
        "💳 **Shopier Ödeme Doğrulama**\n\n"
        "Ödeme yaparken kullandığınız **E-posta** adresini veya **Telefon** numarasını yazıp bu sohbete gönderin. "
        "Kredileriniz saniyeler içinde otomatik olarak hesabınıza tanımlanacaktır.\n\n"
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
    
    ban_data = firestore_helper.get_document(f"ban_{user_id}")
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
            
    user_doc_id = f"user_{user_id}"
    user_data = firestore_helper.get_document(user_doc_id)
    is_new = False
    
    if not user_data:
        is_new = True
        user_data = {
            "credits": 100,
            "referred_by": ref_id or "",
            "id": user_id
        }
        if ref_id:
            user_data["credits"] = 200
        firestore_helper.set_document(user_doc_id, user_data)
        
        if ref_id:
            ref_doc_id = f"user_{ref_id}"
            ref_data = firestore_helper.get_document(ref_doc_id)
            if ref_data:
                ref_data["credits"] = ref_data.get("credits", 100) + 500
                firestore_helper.set_document(ref_doc_id, ref_data)
                try:
                    await bot.send_message(int(ref_id), "🎉 **Tebrikler!** Davet ettiğiniz bir arkadaşınız bota katıldı. Hesabınıza **+500 Kredi** yüklendi!")
                except Exception:
                    pass
            else:
                ref_data = {
                    "credits": 600,
                    "referred_by": "",
                    "id": int(ref_id)
                }
                firestore_helper.set_document(ref_doc_id, ref_data)

    lang = user_lang_helper.get_user_lang(user_id)
    if not lang:
        await show_lang_selection(event)
    else:
        if is_new and ref_id:
            await event.respond("🎁 **Davet Bonusu:** Bota davet linkiyle katıldığınız için hesabınıza **+100 Hediye Kredi** tanımlandı! (Toplam 200 Kredi)")
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
    
    user_data = firestore_helper.get_document(f"user_{user_id}") or {"credits": 100}
    credits = user_data.get("credits", 100)

    buttons = []
    for label, pkg_key in t["pkg_btn_list"]:
        buttons.append([Button.inline(label, pkg_key.encode())])
    buttons.append([Button.inline(t["main_menu"], b"menu_main")])

    title_text = (
        f"💰 **Mevcut Krediniz:** `{credits} Kredi`\n\n"
        f"{t['pkg_menu_title']}"
    )
    await event.edit(title_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'menu_referral'))
async def menu_referral_handler(event):
    user_id = event.sender_id
    user_data = firestore_helper.get_document(f"user_{user_id}") or {"credits": 100}
    credits = user_data.get("credits", 100)
    
    text = (
        "👥 **Froxy AI Davet & Kazan Sistemi**\n\n"
        f"💰 **Mevcut Krediniz:** `{credits} Kredi`\n\n"
        "Arkadaşlarınızı davet ederek ücretsiz krediler kazanabilirsiniz! 🎁\n\n"
        "• Davet ettiğiniz her yeni üye için **+500 Kredi** kazanırsınız.\n"
        "• Davet linkinizle katılan arkadaşınız **100 Hediye Kredi** kazanır.\n\n"
        "🔗 **Sizin Davet Linkiniz:**\n"
        f"`https://t.me/FroxyDestekBOT?start=ref_{user_id}`\n\n"
        "*(Yukarıdaki linke tıklayarak kopyalayabilir ve arkadaşlarınıza gönderebilirsiniz.)*"
    )
    buttons = [
        [Button.inline("↩️ Ana Menü", b"menu_main")]
    ]
    await event.edit(text, buttons=buttons)

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
    
    # Ban check
    ban_data = firestore_helper.get_document(f"ban_{user_id}")
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
        credits_to_add = 0
        pkg_title = "Bilinmeyen Paket"
        
        if "baslangic" in prod_name or "5.000" in prod_name or "5k" in prod_name or "starter" in prod_name:
            credits_to_add = 5000
            pkg_title = "🚀 Başlangıç Paketi (5.000 Kredi)"
        elif "populer" in prod_name or "15.000" in prod_name or "15k" in prod_name or "popular" in prod_name:
            credits_to_add = 15000
            pkg_title = "⭐ Popüler Paket (15.000 Kredi)"
        elif "profesyonel" in prod_name or "50.000" in prod_name or "50k" in prod_name or "professional" in prod_name:
            credits_to_add = 50000
            pkg_title = "💼 Profesyonel Paket (50.000 Kredi)"
        else:
            credits_to_add = 5000
            pkg_title = f"Özel Paket ({unclaimed_order.get('product_name')})"
            
        user_doc_id = f"user_{user_id}"
        user_data = firestore_helper.get_document(user_doc_id) or {
            "credits": 100,
            "referred_by": "",
            "id": user_id
        }
        user_data["credits"] = user_data.get("credits", 100) + credits_to_add
        firestore_helper.set_document(user_doc_id, user_data)
        
        orders[unclaimed_idx]["claimed"] = True
        firestore_helper.set_document(doc_id, orders_doc)
        
        await event.respond(
            f"✅ **Ödemeniz Başarıyla Doğrulandı!**\n\n"
            f"📦 **Satın Alınan:** {pkg_title}\n"
            f"🎯 **Tanımlanan Kredi:** +{credits_to_add} Kredi\n"
            f"💰 **Yeni Kredi Bakiyeniz:** {user_data['credits']} Kredi\n\n"
            f"Froxy AI'ı keyifle kullanın! 🤖"
        )
        
        try:
            config = load_config() or {}
            support_chat_id = config.get("support_chat_id", config.get("admin_id", ADMIN_ID))
            if support_chat_id:
                await bot.send_message(
                    support_chat_id, 
                    f"🎉 **Shopier Otomatik Satış Bildirimi!**\n"
                    f"👤 **Kullanıcı:** `{user_id}`\n"
                    f"📦 **Ürün:** {pkg_title}\n"
                    f"💰 **Tutar:** {unclaimed_order.get('amount')} ₺\n"
                    f"🛍️ **Sipariş ID:** `{unclaimed_order.get('order_id')}`\n"
                    f"📧 **E-posta/Telefon:** {input_val}"
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

        # Admin action buttons
        admin_buttons = [
            [
                Button.inline("➕ 100 Kredi Ekle", f"adm_add_{user_id}_100".encode()),
                Button.inline("➕ 1.000 Kredi Ekle", f"adm_add_{user_id}_1000".encode())
            ],
            [
                Button.inline("➕ 5.000 Kredi Ekle", f"adm_add_{user_id}_5000".encode()),
                Button.inline("🚫 Kullanıcıyı Engelle (Ban)", f"adm_ban_{user_id}".encode())
            ]
        ]

        try:
            await bot.send_message(admin_chat_id, admin_msg, buttons=admin_buttons)
            await event.respond(t["support_success"])
            save_ticket_to_file("Froxy AI", user_id, first_name, last_name, username, event.text)
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await event.respond(t["support_fail"])

        user_states[user_id] = None
        return

    config = load_config() or {}
    support_chat_id = config.get("support_chat_id", admin_chat_id)

    if event.sender_id == admin_chat_id or event.chat_id == support_chat_id:
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                # Ensure the replied-to message was sent by this bot itself to prevent cross-talk
                if reply_msg.sender_id == BOT_USER_ID:
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

# Admin Action Callbacks
@bot.on(events.CallbackQuery(pattern=r'adm_add_(\d+)_(\d+)'))
async def admin_add_credits_callback(event):
    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
    if event.sender_id != admin_chat_id:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    target_user_id = int(event.pattern_match.group(1))
    amount = int(event.pattern_match.group(2))
    
    user_doc_id = f"user_{target_user_id}"
    user_data = firestore_helper.get_document(user_doc_id) or {
        "credits": 100,
        "referred_by": "",
        "id": target_user_id
    }
    user_data["credits"] = user_data.get("credits", 100) + amount
    firestore_helper.set_document(user_doc_id, user_data)
    
    try:
        await bot.send_message(target_user_id, f"🎁 **Yönetici Bonusu:** Hesabınıza **+{amount} Kredi** tanımlandı! Yeni bakiyeniz: `{user_data['credits']} Kredi`")
    except Exception:
        pass
        
    await event.answer(f"✅ Kullanıcıya {amount} kredi tanımlandı.", alert=True)
    original_text = event.message.text
    await event.edit(f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcıya {amount} kredi tanımlandı. (Yönetici: @{event.sender.username or event.sender_id})")

@bot.on(events.CallbackQuery(pattern=r'adm_ban_(\d+)'))
async def admin_ban_user_callback(event):
    config = load_config() or {}
    admin_chat_id = config.get("froxy_admin_id", config.get("admin_id", ADMIN_ID))
    if event.sender_id != admin_chat_id:
        await event.answer("⚠️ Bu işlem için yetkiniz yok!", alert=True)
        return
        
    target_user_id = int(event.pattern_match.group(1))
    
    ban_doc_id = f"ban_{target_user_id}"
    firestore_helper.set_document(ban_doc_id, {"banned": True, "id": target_user_id})
    
    await event.answer("🚫 Kullanıcı engellendi.", alert=True)
    original_text = event.message.text
    await event.edit(f"{original_text}\n\n⚙️ **Aksiyon:** Kullanıcı engellendi. (Yönetici: @{event.sender.username or event.sender_id})")

if __name__ == '__main__':
    import asyncio
    from telethon.errors import FloodWaitError
    
    async def start_with_retry():
        global BOT_USER_ID
        while True:
            try:
                logger.info("Starting Froxy AI Support Bot (@FroxyDestekBOT)...")
                await bot.start(bot_token=BOT_TOKEN)
                me = await bot.get_me()
                BOT_USER_ID = me.id
                logger.info(f"Froxy AI Support Bot started successfully! Bot User ID: {BOT_USER_ID}")
                await bot.run_until_disconnected()
            except FloodWaitError as e:
                logger.warning(f"FloodWait: Telegram {e.seconds} saniye beklememizi istiyor. Bekleniyor...")
                await asyncio.sleep(e.seconds + 5)
                logger.info("FloodWait süresi bitti, tekrar deneniyor...")
            except Exception as e:
                logger.error(f"Bot başlatma hatası: {e}")
                await asyncio.sleep(30)
    
    bot.loop.run_until_complete(start_with_retry())
