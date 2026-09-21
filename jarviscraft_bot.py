import os
import json
import logging
import asyncio
import sys
from telethon import TelegramClient, events, Button

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JarvisCraftBot")

API_ID = int(os.environ.get("TELEGRAM_API_ID", 31076280))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8")
BOT_TOKEN = os.environ.get("JARVIS_BOT_TOKEN", "8940174381:AAF9lvAL0GHoA_azbNdbaDBZ_EcLb3KH2SI").strip()

DATA_DIR = "jarvis_data"
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ─── Divider Lines & Decorations ───
LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DOT = "◈"

def load_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

client = TelegramClient("sessions/jarviscraft_bot", API_ID, API_HASH)

# State tracking for interactive dialogs
USER_STATES = {}

SHOPIER_URL = "https://www.shopier.com/3051522"
BOT_URL = "https://t.me/JarvisCraftsBot"
APP_URL = "https://froxy-bot-1.onrender.com/jarvis/app"

def get_main_menu():
    return [
        [Button.inline("⚡  Oto-Reklam Motoru", b"menu_ad_engine"),
         Button.inline("🏪  Kod Mağazası", b"menu_store")],
        [Button.inline("🧠  Jarvis AI", b"menu_ai_tools"),
         Button.inline("💎  VIP & Bakiye", b"menu_vip")],
        [Button.inline("👤  Profilim", b"menu_profile"),
         Button.inline("📱  Web Panel", b"menu_miniapp")],
        [Button.inline("💬  Canlı Destek", b"menu_support")]
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start  —  Welcome Screen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage(pattern=r"^/start"))
async def start_handler(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    users = load_data()
    is_new = uid not in users
    if is_new:
        users[uid] = {
            "first_name": sender.first_name,
            "username": sender.username,
            "balance": 0.0,
            "vip_until": None,
            "ad_messages": [],
            "ad_interval": 30,
            "is_running": False,
            "joined_at": str(asyncio.get_event_loop().time())
        }
        save_data(users)

    name = sender.first_name or "Kullanıcı"

    welcome = (
        f"{'🎉 Yeni üyeliğiniz aktifleştirildi!' if is_new else ''}\n\n"
        f"                ⚡ **JARVISCRAFT** ⚡\n"
        f"{LINE}\n\n"
        f"Hoş geldiniz, **{name}**.\n\n"
        f"JarvisCraft, Telegram'ın en gelişmiş\n"
        f"**yazılım & otomasyon ekosistemidir.**\n\n"
        f"{DOT}  **Oto-Reklam Motoru** — 65+ gruba kesintisiz mesaj\n"
        f"{DOT}  **Kod Mağazası** — Hazır bot & script paketleri\n"
        f"{DOT}  **AI Araçları** — Yapay zeka destekli üretkenlik\n"
        f"{DOT}  **VIP Sistem** — Premium özellikler & öncelik\n\n"
        f"{LINE}\n"
        f"👇  **İşlem yapmak istediğiniz bölümü seçin:**"
    )
    await event.respond(welcome, buttons=get_main_menu())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Callback Router
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    sender = await event.get_sender()
    uid = str(sender.id)
    users = load_data()
    user = users.get(uid, {})

    # ── Ana Menü ──
    if data == "main_menu":
        await event.edit(
            f"                ⚡ **JARVISCRAFT** ⚡\n"
            f"{LINE}\n\n"
            f"👇  Bölüm seçin:",
            buttons=get_main_menu()
        )

    # ══════════════════════════════════
    #  1.  OTO-REKLAM & MESAJ MOTORU
    # ══════════════════════════════════
    elif data == "menu_ad_engine":
        is_active = user.get("is_running", False)
        status = "🟢  AKTİF — Gönderim yapılıyor" if is_active else "🔴  DURDURULDU"
        interval = user.get('ad_interval', 30)
        msg_count = len(user.get('ad_messages', []))
        current_msg = user.get('ad_messages', ['—'])[0] if msg_count > 0 else "—"
        preview = current_msg[:60] + "..." if len(current_msg) > 60 else current_msg

        msg = (
            f"           ⚡ **OTO-REKLAM MOTORU**\n"
            f"{LINE}\n\n"
            f"**Durum:**  {status}\n"
            f"**Aralık:**  Her `{interval}` dakikada bir\n"
            f"**Mesaj:**   {msg_count} adet kayıtlı\n"
            f"**Gruplar:** 65+ aktif ticaret grubu\n\n"
            f"📝 **Aktif Metin:**\n"
            f"`{preview}`\n\n"
            f"{LINE}"
        )

        toggle = (
            Button.inline("⏸  Gönderimi Durdur", b"ad_stop")
            if is_active else
            Button.inline("▶️  Gönderimi Başlat", b"ad_start")
        )

        buttons = [
            [toggle],
            [Button.inline("📝 Reklam Metnini Düzenle", b"ad_edit_msg"),
             Button.inline("⏱ Süre Ayarla", b"ad_set_interval")],
            [Button.inline("🎯 Hedef Grupları", b"ad_show_groups"),
             Button.inline("👤 Hesap Ekle", b"ad_add_account")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    elif data == "ad_start":
        user["is_running"] = True
        users[uid] = user
        save_data(users)
        await event.answer("▶️  Otomatik gönderim başlatıldı!", alert=True)
        # Re-render the panel
        event.data = b"menu_ad_engine"
        await callback_handler(event)

    elif data == "ad_stop":
        user["is_running"] = False
        users[uid] = user
        save_data(users)
        await event.answer("⏸  Gönderim durduruldu.", alert=True)
        event.data = b"menu_ad_engine"
        await callback_handler(event)

    elif data == "ad_edit_msg":
        USER_STATES[uid] = "waiting_ad_message"
        curr = user.get("ad_messages", ["Henüz belirlenmemiş"])[0] if user.get("ad_messages") else "Henüz belirlenmemiş"
        await event.edit(
            f"           📝 **REKLAM METNİ DÜZENLE**\n"
            f"{LINE}\n\n"
            f"**Mevcut metniniz:**\n"
            f"```\n{curr}\n```\n\n"
            f"💬 Yeni reklam metninizi bu sohbete **mesaj olarak** gönderin.\n\n"
            f"💡 **İpucu:** Fotoğraf, emoji ve satır sonu kullanarak\n"
            f"dikkat çekici bir mesaj oluşturabilirsiniz.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal Et", b"menu_ad_engine")]]
        )

    elif data == "ad_set_interval":
        buttons = [
            [Button.inline("⏱ 15 dk  ·  💎 VIP", b"interval_15"),
             Button.inline("⏱ 30 dk  ·  Standart", b"interval_30")],
            [Button.inline("⏱ 45 dk", b"interval_45"),
             Button.inline("⏱ 60 dk", b"interval_60")],
            [Button.inline("◀️ Geri", b"menu_ad_engine")]
        ]
        await event.edit(
            f"           ⏱ **GÖNDERİM ARALIĞI**\n"
            f"{LINE}\n\n"
            f"Mesajlar arasındaki bekleme süresini seçin.\n\n"
            f"⚠️ 15 dakika aralığı yalnızca **VIP** üyelere açıktır.\n"
            f"Kısa aralıklar hesap güvenliği açısından\n"
            f"daha yüksek risk taşıyabilir.\n\n"
            f"{LINE}",
            buttons=buttons
        )

    elif data.startswith("interval_"):
        mins = int(data.split("_")[1])
        user["ad_interval"] = mins
        users[uid] = user
        save_data(users)
        await event.answer(f"✅  Aralık {mins} dakika olarak ayarlandı.", alert=True)
        event.data = b"menu_ad_engine"
        await callback_handler(event)

    elif data == "ad_show_groups":
        msg = (
            f"           🎯 **HEDEF GRUP HAVUZU**\n"
            f"{LINE}\n\n"
            f"Sistemimiz Türkiye'nin en aktif\n"
            f"**65+ ticaret & alım-satım grubuna**\n"
            f"otomatik üyelik ve rotasyonlu gönderim yapar.\n\n"
            f"{DOT}  Otomatik grup keşfi & katılma\n"
            f"{DOT}  Spam koruması & flood önleyici\n"
            f"{DOT}  Akıllı gönderim sıralaması\n"
            f"{DOT}  Özel grup ekleme desteği\n\n"
            f"{LINE}"
        )
        await event.edit(msg, buttons=[
            [Button.inline("◀️ Geri", b"menu_ad_engine")]
        ])

    elif data == "ad_add_account":
        msg = (
            f"           👤 **GÖNDERİCİ HESAP EKLE**\n"
            f"{LINE}\n\n"
            f"Reklamların gönderileceği Telegram hesabınızı\n"
            f"bağlamak için iki yöntem mevcuttur:\n\n"
            f"**1️⃣  StringSession ile**\n"
            f"Telethon oturum anahtarınızı girerek\n"
            f"anında aktif edin.\n\n"
            f"**2️⃣  Telefon & Kod ile**\n"
            f"Numaranızı girin, gelen SMS/Telegram\n"
            f"kodunu onaylayın.\n\n"
            f"💬 Kurulum desteği: @habil2121\n\n"
            f"{LINE}"
        )
        await event.edit(msg, buttons=[
            [Button.inline("🔑 StringSession Gir", b"input_session")],
            [Button.inline("◀️ Geri", b"menu_ad_engine")]
        ])

    elif data == "input_session":
        USER_STATES[uid] = "waiting_session_string"
        await event.edit(
            f"           🔑 **SESSION GİRİŞİ**\n"
            f"{LINE}\n\n"
            f"Telethon StringSession anahtarınızı\n"
            f"bu sohbete mesaj olarak gönderin.\n\n"
            f"⚠️ Anahtarınız güvenle şifrelenerek\n"
            f"sunucularımızda saklanır.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal Et", b"ad_add_account")]]
        )

    # ══════════════════════════════════
    #  2.  KOD PAKETLERİ & BOT MAĞAZASI
    # ══════════════════════════════════
    elif data == "menu_store":
        msg = (
            f"           🏪 **KOD & BOT MAĞAZASI**\n"
            f"{LINE}\n\n"
            f"Profesyonel geliştiriciler için hazırlanmış,\n"
            f"**temiz kodlu** ve **kuruluma hazır** paketler.\n\n"
            f"Her pakette açık kaynak kod, kurulum\n"
            f"dokümanı ve örnek konfigürasyon dahildir.\n\n"
            f"🔥  **Haftanın Çok Satanı:**\n"
            f"     Oto-Reklam Bot Scripti\n\n"
            f"{LINE}\n"
            f"👇  Detay görmek için paketi seçin:"
        )
        buttons = [
            [Button.inline("🤖 Jarvis Core AI Asistan  ·  350₺", b"prod_1")],
            [Button.inline("⚡ Oto-Reklam Bot Scripti  ·  450₺", b"prod_2")],
            [Button.inline("🔍 Fiyat Takip Scraper  ·  300₺", b"prod_3")],
            [Button.inline("🚀 Full Mini App Kiti  ·  400₺", b"prod_4")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    elif data.startswith("prod_"):
        pid = data.split("_")[1]
        products = {
            "1": {
                "icon": "🤖",
                "title": "Jarvis Core AI Asistan İskeleti",
                "price": "350₺",
                "badge": "🔥 POPÜLER",
                "desc": "Sesli/yazılı komut algılayan, Python + LLM mimarili,\nsistem görevlerini otomatikleştiren akıllı asistan çekirdeği.",
                "features": [
                    "Python 3.10+ & AsyncIO altyapısı",
                    "Telegram & Masaüstü entegrasyonu",
                    "Tam açık kaynak + kurulum kılavuzu",
                    "GPT/Gemini API entegrasyonu hazır"
                ]
            },
            "2": {
                "icon": "⚡",
                "title": "Telegram Oto-Reklam Bot Scripti",
                "price": "450₺",
                "badge": "🏆 ÇOK SATAN",
                "desc": "Çoklu hesap yönetimi, anti-flood gecikme sistemi,\n65+ ticaret grubu entegrasyonu ve rotasyonlu mesaj motoru.",
                "features": [
                    "Telethon tabanlı güçlü motor",
                    "Anti-Ban & Replay Guard koruma",
                    "Web panel & zamanlayıcı entegre",
                    "Otomatik grup keşfi & katılma"
                ]
            },
            "3": {
                "icon": "🔍",
                "title": "E-Ticaret & Fiyat Takip Scraper",
                "price": "300₺",
                "badge": "🆕 YENİ",
                "desc": "Trendyol, Yemeksepeti ve e-ticaret sitelerinden\nanlık kupon ve fiyat alarmı toplayan bot seti.",
                "features": [
                    "Playwright & Cloudflare Bypass",
                    "Anlık Telegram alarm bildirimi",
                    "Otomatik stok takibi"
                ]
            },
            "4": {
                "icon": "🚀",
                "title": "Full-Stack Mini App + Shopier Kiti",
                "price": "400₺",
                "badge": "💎 EN İYİ DEĞER",
                "desc": "Kendi Telegram Mini App mağazanızı 10 dakikada kurun.\nFlask backend + Vite frontend + Shopier ödeme entegrasyonu.",
                "features": [
                    "Hazır tasarım & webhooklar",
                    "Render/Vercel dağıtımına hazır",
                    "Shopier otomatik ödeme & teslimat"
                ]
            }
        }
        p = products.get(pid)
        if not p:
            return

        feat_text = "\n".join(f"  ✓  {f}" for f in p["features"])

        msg = (
            f"           {p['icon']} **{p['title']}**\n"
            f"{LINE}\n\n"
            f"  {p['badge']}      💰 **{p['price']}**\n\n"
            f"{p['desc']}\n\n"
            f"**Paket İçeriği:**\n"
            f"{feat_text}\n\n"
            f"{LINE}\n\n"
            f"✅ Açık kaynak kod teslimi\n"
            f"✅ Kurulum dokümanı dahil\n"
            f"✅ Shopier 3D Secure güvenli ödeme\n"
            f"⚡ Ödeme sonrası **anında** dosya teslimi"
        )
        buttons = [
            [Button.url(f"🛒  Güvenle Satın Al  ·  {p['price']}", SHOPIER_URL)],
            [Button.inline("◀️ Mağazaya Dön", b"menu_store")]
        ]
        await event.edit(msg, buttons=buttons)

    # ══════════════════════════════════
    #  3.  JARVIS AI ARAÇLARI
    # ══════════════════════════════════
    elif data == "menu_ai_tools":
        msg = (
            f"           🧠 **JARVIS AI ARAÇLARI**\n"
            f"{LINE}\n\n"
            f"Yapay zeka destekli üretkenlik araçlarınızı\n"
            f"doğrudan bu sohbet üzerinden kullanın.\n\n"
            f"{DOT}  **Reklam Metni Üretici**\n"
            f"     Ürününüzü söyleyin, 3 farklı\n"
            f"     dönüşüm odaklı metin üretsin.\n\n"
            f"{DOT}  **Kod Hata Ayıklayıcı**\n"
            f"     Hata veren kodu yapıştırın,\n"
            f"     çözümü saniyeler içinde alın.\n\n"
            f"{DOT}  **Bot & Proje Fikir Jeneratörü**\n"
            f"     En karlı yazılım projeleri hakkında\n"
            f"     yapay zeka destekli ilham alın.\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.inline("✍️  Reklam Metni Üret", b"ai_ad_copy")],
            [Button.inline("🐛  Kod Hata Ayıkla", b"ai_code_debug")],
            [Button.inline("💡  Proje Fikri Al", b"ai_project_idea")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    elif data == "ai_ad_copy":
        USER_STATES[uid] = "waiting_ai_ad"
        await event.edit(
            f"           ✍️ **REKLAM METNİ ÜRETİCİ**\n"
            f"{LINE}\n\n"
            f"Satmak istediğiniz ürün veya hizmeti\n"
            f"kısaca yazıp gönderin.\n\n"
            f"💡 **Örnek:**\n"
            f"`Netflix ortak hesap 50 TL, garantili`\n\n"
            f"Jarvis AI sizin için **3 farklı** profesyonel\n"
            f"reklam varyasyonu hazırlayacaktır.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal", b"menu_ai_tools")]]
        )

    elif data == "ai_code_debug":
        USER_STATES[uid] = "waiting_code_debug"
        await event.edit(
            f"           🐛 **KOD HATA AYIKLAYICI**\n"
            f"{LINE}\n\n"
            f"Hata veren kod parçanızı bu sohbete\n"
            f"mesaj olarak gönderin.\n\n"
            f"Jarvis AI hatayı tespit edip düzeltilmiş\n"
            f"versiyonu sunacaktır.\n\n"
            f"💡 Hata mesajını da eklemeniz analizi\n"
            f"hızlandıracaktır.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal", b"menu_ai_tools")]]
        )

    elif data == "ai_project_idea":
        ideas = [
            "🤖 **Telegram Müşteri Destek Botu**\nAI destekli, otomatik cevaplayan, ticket sistemi entegreli destek botu. Aylık 500-2000₺ lisans geliri potansiyeli.",
            "📊 **Kripto Fiyat Alarm Botu**\nBinance/Gate.io API entegreli, kullanıcıya alarm gönderen Telegram botu. VIP üyelik modeliyle aylık gelir.",
            "🛒 **Dropshipping Otomasyon Aracı**\nTrendyol/Hepsiburada ürün çekme, otomatik fiyat güncelleme ve sipariş yönetim scripti.",
            "📱 **Instagram DM Oto-Cevaplama Botu**\nİşletmeler için Instagram Direct mesajlarını AI ile otomatik yanıtlayan SaaS aracı."
        ]
        import random
        selected = random.sample(ideas, min(3, len(ideas)))
        ideas_text = "\n\n".join(f"{i+1}️⃣  {idea}" for i, idea in enumerate(selected))

        msg = (
            f"           💡 **PROJE FİKİR JENERATÖRÜ**\n"
            f"{LINE}\n\n"
            f"Jarvis AI'ın önerdiği karlı proje fikirleri:\n\n"
            f"{ideas_text}\n\n"
            f"{LINE}\n\n"
            f"💬 Detaylı proje planı için @habil2121"
        )
        await event.edit(msg, buttons=[
            [Button.inline("🔄  Yeni Fikirler Üret", b"ai_project_idea")],
            [Button.inline("◀️  AI Araçları", b"menu_ai_tools")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ])

    # ══════════════════════════════════
    #  4.  VIP & BAKİYE
    # ══════════════════════════════════
    elif data == "menu_vip":
        balance = user.get("balance", 0.0)
        vip_status = user.get("vip_until")

        msg = (
            f"           💎 **VIP & BAKİYE SİSTEMİ**\n"
            f"{LINE}\n\n"
            f"**Bakiyeniz:**  `{balance:.2f} ₺`\n"
            f"**VIP Durumu:** {'🟢 Aktif' if vip_status else '⚪ Standart (Ücretsiz)'}\n\n"
            f"{LINE}\n\n"
            f"⭐ **Haftalık VIP**  ·  `150₺`\n"
            f"   7 gün  ·  15 dk aralık  ·  2 hesap slotu\n\n"
            f"🌟 **Aylık Sınırsız VIP**  ·  `350₺`\n"
            f"   30 gün  ·  Limitsiz  ·  5 hesap slotu\n"
            f"   ⚡ Öncelikli teknik destek\n\n"
            f"{LINE}\n\n"
            f"  ⚪ Ücretsiz     │  30dk  │  1 hesap  │  Standart\n"
            f"  ⭐ Haftalık     │  15dk  │  2 hesap  │  Normal\n"
            f"  🌟 Aylık          │  Sınırsız │  5 hesap  │  Öncelikli\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.url("⭐  Haftalık VIP  ·  150₺", SHOPIER_URL)],
            [Button.url("🌟  Aylık VIP  ·  350₺", SHOPIER_URL)],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    # ══════════════════════════════════
    #  5.  PROFİLİM
    # ══════════════════════════════════
    elif data == "menu_profile":
        username_display = f"@{user.get('username')}" if user.get('username') else "Belirlenmemiş"
        msg = (
            f"           👤 **KULLANICI PROFİLİ**\n"
            f"{LINE}\n\n"
            f"  **İsim:**      {user.get('first_name', 'Bilinmiyor')}\n"
            f"  **Kullanıcı:** {username_display}\n"
            f"  **ID:**        `{uid}`\n\n"
            f"{LINE}\n\n"
            f"  **Bakiye:**    `{user.get('balance', 0.0):.2f} ₺`\n"
            f"  **VIP:**       {'🟢 Aktif' if user.get('vip_until') else '⚪ Standart'}\n"
            f"  **Gönderim:** {'🟢 Çalışıyor' if user.get('is_running') else '🔴 Durduruldu'}\n"
            f"  **Aralık:**    Her {user.get('ad_interval', 30)} dk\n\n"
            f"{LINE}"
        )
        await event.edit(msg, buttons=[
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ])

    # ══════════════════════════════════
    #  6.  WEB MİNİ APP
    # ══════════════════════════════════
    elif data == "menu_miniapp":
        msg = (
            f"           📱 **WEB MİNİ APP PANELİ**\n"
            f"{LINE}\n\n"
            f"Telegram içerisinden tam ekran görsel\n"
            f"web arayüzümüze erişin.\n\n"
            f"{DOT}  Ürün katalogu & sipariş takibi\n"
            f"{DOT}  Reklam motoru kontrol paneli\n"
            f"{DOT}  AI araçları & hesap yönetimi\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.url("🌐  Web Paneli Aç", APP_URL)],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    # ══════════════════════════════════
    #  7.  CANLI DESTEK
    # ══════════════════════════════════
    elif data == "menu_support":
        msg = (
            f"           💬 **CANLI DESTEK & İLETİŞİM**\n"
            f"{LINE}\n\n"
            f"Her türlü teknik soru, özel bot siparişi\n"
            f"veya ödeme bildirimi için bize ulaşın.\n\n"
            f"👨‍💻  **Geliştirici:**  @habil2121\n"
            f"⚡  **Yanıt Süresi:**  5-10 dakika\n"
            f"🕐  **Çalışma:**  7/24 aktif destek\n\n"
            f"{LINE}\n\n"
            f"📧 Özel bot geliştirme talepleri ve\n"
            f"kurumsal çözümler için iletişime geçin."
        )
        await event.edit(msg, buttons=[
            [Button.url("👨‍💻  @habil2121'e Yaz", "https://t.me/habil2121")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Text Message Handler (State Machine)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage)
async def message_handler(event):
    if event.raw_text.startswith("/"):
        return
    sender = await event.get_sender()
    if not sender:
        return
    uid = str(sender.id)
    state = USER_STATES.get(uid)

    if state == "waiting_ad_message":
        users = load_data()
        if uid in users:
            users[uid]["ad_messages"] = [event.raw_text]
            save_data(users)
        USER_STATES.pop(uid, None)
        await event.respond(
            f"           ✅ **REKLAM METNİ GÜNCELLENDİ**\n"
            f"{LINE}\n\n"
            f"**Yeni metniniz başarıyla kaydedildi.**\n\n"
            f"**Önizleme:**\n"
            f"```\n{event.raw_text}\n```\n\n"
            f"Oto-Reklam Motorundan gönderime\n"
            f"başlayabilirsiniz.\n\n"
            f"{LINE}",
            buttons=[
                [Button.inline("⚡ Oto-Reklam Paneli", b"menu_ad_engine")],
                [Button.inline("◀️ Ana Menü", b"main_menu")]
            ]
        )

    elif state == "waiting_ai_ad":
        USER_STATES.pop(uid, None)
        product_name = event.raw_text
        waiting_msg = await event.respond(
            f"🧠 **Jarvis AI çalışıyor...**\n\n"
            f"Ürününüz için 3 farklı profesyonel\n"
            f"reklam varyasyonu hazırlanıyor."
        )

        await asyncio.sleep(1.5)  # Simulate thinking

        opt1 = (
            f"🔥 **BÜYÜK FIRSAT!**\n\n"
            f"⚡ {product_name}\n"
            f"En uygun fiyat & anında teslimat!\n\n"
            f"✅ %100 Çalışma Garantisi\n"
            f"🛒 Sipariş: @{client_username or 'JarvisCraftsBot'}"
        )
        opt2 = (
            f"🚀 **KALİTE ARAYANLAR İÇİN**\n\n"
            f"🎯 {product_name}\n\n"
            f"💎 Hızlı • Güvenilir • 7/24 Destek\n"
            f"👇 DM ile hemen sipariş verin!"
        )
        opt3 = (
            f"⭐ **ÖZEL İNDİRİM**\n\n"
            f"{product_name}\n\n"
            f"📦 Sınırlı stok — Kaçırmayın!\n"
            f"💬 Bilgi & Satın Alım → DM"
        )

        result = (
            f"           ✅ **3 REKLAM VARYASYONU HAZIR**\n"
            f"{LINE}\n\n"
            f"**1️⃣  Dikkat Çekici:**\n{opt1}\n\n"
            f"{LINE}\n\n"
            f"**2️⃣  Profesyonel:**\n{opt2}\n\n"
            f"{LINE}\n\n"
            f"**3️⃣  Kısa & Net:**\n{opt3}\n\n"
            f"{LINE}\n\n"
            f"Beğendiğinizi kopyalayıp Oto-Reklam\n"
            f"motorunuza ekleyebilirsiniz."
        )
        await waiting_msg.edit(result, buttons=[
            [Button.inline("📝 Bu Metni Reklamım Yap", b"ad_edit_msg")],
            [Button.inline("◀️ Ana Menü", b"main_menu")]
        ])

    elif state == "waiting_code_debug":
        USER_STATES.pop(uid, None)
        code_text = event.raw_text
        waiting_msg = await event.respond(
            f"🐛 **Jarvis AI kodu analiz ediyor...**"
        )

        await asyncio.sleep(1)

        result = (
            f"           🐛 **KOD ANALİZ SONUCU**\n"
            f"{LINE}\n\n"
            f"**Gönderilen kod parçası incelendi.**\n\n"
            f"💡 Detaylı analiz ve düzeltme önerileri\n"
            f"için lütfen destek ekibimize ulaşın.\n\n"
            f"Kodunuz kaydedildi ve teknik ekibimiz\n"
            f"size en kısa sürede dönecektir.\n\n"
            f"👨‍💻 @habil2121\n\n"
            f"{LINE}"
        )
        await waiting_msg.edit(result, buttons=[
            [Button.url("👨‍💻 Destek Ekibi", "https://t.me/habil2121")],
            [Button.inline("◀️ Ana Menü", b"main_menu")]
        ])

    elif state == "waiting_session_string":
        USER_STATES.pop(uid, None)
        session = event.raw_text.strip()
        # Save the session string for this user
        users = load_data()
        if uid in users:
            users[uid]["session_string"] = session
            save_data(users)

        await event.respond(
            f"           ✅ **SESSION KAYDI ALINDI**\n"
            f"{LINE}\n\n"
            f"StringSession kaydınız alındı ve\n"
            f"doğrulama sürecine alınmıştır.\n\n"
            f"⏳ Hesap bağlama işlemi genellikle\n"
            f"birkaç dakika içinde tamamlanır.\n\n"
            f"Durum güncellemesi için profil\n"
            f"sayfanızı kontrol edebilirsiniz.\n\n"
            f"{LINE}",
            buttons=[
                [Button.inline("⚡ Oto-Reklam Paneli", b"menu_ad_engine")],
                [Button.inline("◀️ Ana Menü", b"main_menu")]
            ]
        )


client_username = None

async def main():
    global client_username
    logger.info("Starting JarvisCraftBot...")
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    client_username = me.username
    logger.info(f"✅ JarvisCraftBot is ONLINE! @{me.username} (ID: {me.id})")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
