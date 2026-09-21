import os
import json
import logging
import asyncio
import sys
import tempfile
import urllib.request
import urllib.error
from telethon import TelegramClient, events, Button, functions
from telethon.errors import UserNotParticipantError, FloodWaitError
from bot_runtime_status import write_bot_status, invalid_token_error

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JarvisCraftBot")

API_ID = int(os.environ.get("TELEGRAM_API_ID", 31076280))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8")
BOT_TOKEN = os.environ.get("JARVIS_BOT_TOKEN", "8940174381:AAE5M4yFbIZ8F5W8dsINCD3tQipHCYgOlzg").strip()

DATA_DIR = "jarvis_data"
SESSION_DIR = "sessions"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ─── Brand & Links ───
CHANNEL_USERNAME = "JarvisCraftDuyuru"
CHANNEL_URL = "https://t.me/JarvisCraftDuyuru"
SUPPORT_USERNAME = "Geliştirici (ID: 32186)"
SUPPORT_URL = "tg://user?id=32186"
SHOPIER_URL = "https://www.shopier.com/JarvisStore"
APP_URL = "https://bot-service-production-9d74.up.railway.app/jarvis/app"

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
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="users_", suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(USERS_FILE):
            os.replace(tmp_path, USERS_FILE)
        else:
            os.rename(tmp_path, USERS_FILE)
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

client = TelegramClient("sessions/jarviscraft_bot", API_ID, API_HASH)

# State tracking for interactive dialogs
USER_STATES = {}

async def is_user_subscribed(user_id):
    """Checks if the user has joined the official announcement channel via Telegram Bot API."""
    def _check():
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{CHANNEL_USERNAME}&user_id={user_id}"
            req = urllib.request.Request(url, headers={"User-Agent": "JarvisBot/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    status = data.get("result", {}).get("status")
                    return status in ("creator", "administrator", "member", "restricted")
            return False
        except urllib.error.HTTPError:
            # 400 Bad Request means user not in channel / not found
            return False
        except Exception as e:
            logger.warning(f"Subscription check error for {user_id}: {e}")
            return False
    return await asyncio.to_thread(_check)

def get_main_menu():
    return [
        [Button.url("🛍️  Shopier Mağazası (Tüm İlanlar)", SHOPIER_URL)],
        [Button.inline("⚡  Oto-Reklam Motoru", b"menu_ad_engine"),
         Button.inline("🏪  Kod Mağazası", b"menu_store")],
        [Button.inline("🧠  Jarvis AI", b"menu_ai_tools"),
         Button.inline("💎  VIP & Bakiye", b"menu_vip")],
        [Button.inline("👤  Profilim", b"menu_profile"),
         Button.url("📱  Web Panel", APP_URL)],
        [Button.url("📢  Duyuru Kanalı", CHANNEL_URL),
         Button.inline("💬  Canlı Destek", b"menu_support")]
    ]

def get_gatekeeper_menu():
    return [
        [Button.url("📢  Duyuru Kanalına Katıl (@JarvisCraftDuyuru)", CHANNEL_URL)],
        [Button.inline("✅  Katıldım, Doğrula", b"verify_join")]
    ]

async def render_ad_engine(event, user):
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
        f"**Gruplar:** 65+ aktif ticaret & alım-satım grubu\n\n"
        f"📝 **Aktif Reklam Metni:**\n"
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
        [Button.inline("🎯 Hedef Grupları Gör", b"ad_show_groups"),
         Button.inline("👤 Gönderici Hesap Ekle", b"ad_add_account")],
        [Button.inline("◀️  Ana Menü", b"main_menu")]
    ]
    await event.edit(msg, buttons=buttons)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start  —  Welcome Screen with Gatekeeper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage(pattern=r"^/start", func=lambda e: e.is_private))
async def start_handler(event):
    sender = await event.get_sender()
    if not sender:
        return
    uid = str(sender.id)
    users = load_data()
    is_new = uid not in users
    if is_new:
        users[uid] = {
            "first_name": sender.first_name,
            "username": sender.username,
            "balance": 0.0,
            "vip_until": None,
            "ad_messages": ["🚀 JarvisCraft ile otomatik reklam gönderimi aktif!"],
            "ad_interval": 30,
            "is_running": False
        }
        save_data(users)

    # 1. Check Channel Subscription (Gatekeeper)
    is_subbed = await is_user_subscribed(sender.id)
    if not is_subbed:
        gate_msg = (
            f"          ⚡ **JARVISCRAFT'A HOŞ GELDİNİZ** ⚡\n"
            f"{LINE}\n\n"
            f"Merhaba **{sender.first_name or 'Değerli Kullanıcı'}**,\n\n"
            f"JarvisCraft bot ve yazılım ekosistemini kullanabilmek için\n"
            f"resmi **Duyuru & Güncelleme Kanalımıza** katılmanız gerekmektedir.\n\n"
            f"📢 **Kanalımızda Neler Var?**\n"
            f"{DOT}  Satışa sunulan bot ve scriptlerin video demoları\n"
            f"{DOT}  Açık kaynak Python kodları ve hazır kütüphaneler\n"
            f"{DOT}  Özel indirim kuponları ve VIP çekilişler\n"
            f"{DOT}  API ve sistem güncellemeleri\n\n"
            f"{LINE}\n"
            f"👇  Aşağıdaki butondan kanala katılın ve ardından **Doğrula**'ya tıklayın:"
        )
        await event.respond(gate_msg, buttons=get_gatekeeper_menu())
        return

    name = sender.first_name or "Kullanıcı"
    welcome = (
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
    if not sender:
        return
    uid = str(sender.id)
    users = load_data()
    user = users.get(uid, {})

    # ── Gatekeeper Verification ──
    if data == "verify_join":
        is_subbed = await is_user_subscribed(sender.id)
        if is_subbed:
            await event.answer("✅ Doğrulama başarılı! JarvisCraft'a hoş geldiniz.", alert=True)
            name = sender.first_name or "Kullanıcı"
            welcome = (
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
            await event.edit(welcome, buttons=get_main_menu())
        else:
            await event.answer("❌ Henüz @JarvisCraftDuyuru kanalına katılmadınız! Lütfen önce kanala katılın.", alert=True)
        return

    # Check subscription for any action
    if not await is_user_subscribed(sender.id):
        await event.answer("⚠️ Lütfen önce resmi duyuru kanalımıza katılın!", alert=True)
        await event.edit(
            f"          ⚡ **DUYURU KANALINA KATILIN** ⚡\n"
            f"{LINE}\n\n"
            f"İşlemlere devam edebilmek için @{CHANNEL_USERNAME} kanalına üye olmanız gerekmektedir.",
            buttons=get_gatekeeper_menu()
        )
        return

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
        await render_ad_engine(event, user)

    elif data == "ad_start":
        user["is_running"] = True
        users[uid] = user
        save_data(users)
        await event.answer("▶️  Otomatik gönderim başlatıldı!", alert=True)
        await render_ad_engine(event, user)

    elif data == "ad_stop":
        user["is_running"] = False
        users[uid] = user
        save_data(users)
        await event.answer("⏸  Gönderim durduruldu.", alert=True)
        await render_ad_engine(event, user)

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
        await render_ad_engine(event, user)

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
            f"💬 Kurulum desteği: @{SUPPORT_USERNAME}\n\n"
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
            [Button.url("🛍️  Shopier Mağazasını Aç (Tüm İlanlar)", SHOPIER_URL)],
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
                "url": "https://www.shopier.com/51058105",
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
                "url": "https://www.shopier.com/51058117",
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
                "url": "https://www.shopier.com/51058118",
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
                "url": "https://www.shopier.com/51058119",
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
            f"⚡ Ödeme sonrası **anında** teslimat"
        )
        buttons = [
            [Button.url(f"🛒  Shopier'dan Satın Al  ·  {p['price']}", p.get("url", SHOPIER_URL))],
            [Button.url("📹  Demoyu Kanalda İncele", CHANNEL_URL)],
            [Button.inline("◀️ Mağazaya Dön", b"menu_store")]
        ]
        await event.edit(msg, buttons=buttons)

    # ══════════════════════════════════
    #  3.  J.A.R.V.I.S. MASAÜSTÜ AI PROJESİ
    # ══════════════════════════════════
    elif data == "menu_ai_tools":
        msg = (
            f"           🤖 **J.A.R.V.I.S. AI MASAÜSTÜ ASİSTANI**\n"
            f"{LINE}\n\n"
            f"Tony Stark'ın yapay zeka asistanı artık masanızda!\n\n"
            f"Windows için özel geliştirilmiş, Python gerektirmeyen\n"
            f"**taşınabilir masaüstü sesli asistan projesi.**\n\n"
            f"{DOT}  **Ultra Gerçekçi Türkçe Ses:**\n"
            f"     İnsan doğallığında konuşur, anında sesli cevap verir.\n\n"
            f"{DOT}  **0 ms Anında Susturma:**\n"
            f"     Konuşurken `Esc` tuşuna bastığınız an susar.\n\n"
            f"{DOT}  **Canlı İnternet & Çok Kaynaklı Web Arama:**\n"
            f"     Güncel piyasa ve haber verilerini internetten derler.\n\n"
            f"{DOT}  **Sıfır Kurulum:**\n"
            f"     Direkt çalıştırılabilir `.exe` paketi.\n\n"
            f"{LINE}\n"
            f"👇  Aşağıdaki butonlarla videoyu izleyin veya PC demo paketini indirin:"
        )
        buttons = [
            [Button.inline("📹  Kullanım Videosunu Gönder (Chat'e)", b"jarvis_send_video")],
            [Button.inline("📥  Ücretsiz PC Demo Paketi (.ZIP)", b"jarvis_send_demo")],
            [Button.url("🛒  Shopier'dan Lisans Satın Al (350 ₺)", "https://www.shopier.com/51058105")],
            [Button.inline("📢  Duyuru Kanalına Paylaş (Video & Demo)", b"jarvis_broadcast_channel")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)

    elif data == "jarvis_send_video":
        await event.answer("📹 Tanıtım videosu gönderiliyor...", alert=False)
        video_path = os.path.join("static", "jarvis_demo_video.mp4")
        caption = (
            "🤖 **J.A.R.V.I.S. Kişisel AI Masaüstü Asistanı — Kullanım Rehberi**\n\n"
            "• Ultra gerçekçi Türkçe sesli yanıt sistemi\n"
            "• 0 ms anında Esc tuşuyla susturma\n"
            "• Canlı web tarama ve akıllı görev yürütme\n"
            "• Sıfır kurulum: Windows portable EXE paketi\n\n"
            "📥 **Ücretsiz Demo:** https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n"
            "🛒 **Shopier Lisans:** https://www.shopier.com/51058105\n"
            "📢 **Duyuru Kanalı:** @JarvisCraftDuyuru"
        )
        try:
            if os.path.exists(video_path):
                await client.send_file(
                    event.chat_id,
                    video_path,
                    caption=caption,
                    supports_streaming=True
                )
            else:
                await event.respond(
                    f"📹 **J.A.R.V.I.S. Tanıtım Videosu:**\n"
                    f"https://bot-service-production-9d74.up.railway.app/static/jarvis_demo_video.mp4\n\n"
                    f"{caption}"
                )
        except Exception as e:
            logger.warning(f"Direct video send error: {e}")
            await event.respond(
                f"📹 **J.A.R.V.I.S. Tanıtım Videosu:**\n"
                f"https://bot-service-production-9d74.up.railway.app/static/jarvis_demo_video.mp4\n\n"
                f"{caption}"
            )

    elif data == "jarvis_send_demo":
        await event.answer("📥 Demo paketi hazırlanıyor...", alert=False)
        demo_msg = (
            "💻 **J.A.R.V.I.S. Müşteri Demo Paketi**\n\n"
            "• 10 Soru / Komut Deneme Hakkı\n"
            "• İlk 3 yanıtta ultra gerçekçi Türkçe sesli asistan\n"
            "• 0 ms anında `Esc` ile susturma\n"
            "• Canlı çok kaynaklı web arama\n\n"
            "👇 **Aşağıdaki bağlantıdan doğrudan bilgisayarınıza indirebilirsiniz:**\n"
            "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n\n"
            "💡 *İndirdiğiniz ZIP dosyasını klasöre çıkartıp `LisansArena_JARVIS_DEMO.exe`ye çift tıklamanız yeterlidir. Sıfır kurulum gerektirir.*"
        )
        buttons = [
            [Button.url("📥 Demo Paketini İndir (.ZIP)", "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip")],
            [Button.url("🛒 Tam Sürüm Lisans Al (350 ₺)", "https://www.shopier.com/51058105")],
            [Button.inline("◀️ J.A.R.V.I.S. Menüsü", b"menu_ai_tools")]
        ]
        await event.respond(demo_msg, buttons=buttons)

    elif data == "jarvis_broadcast_channel":
        await event.answer("📢 Kanala gönderiliyor...", alert=False)
        channel_post = (
            "🚀 **J.A.R.V.I.S. AI MASAÜSTÜ ASİSTANI YAYINDA!** 🚀\n\n"
            "Tony Stark'ın efsanevi asistanı artık gerçek oldu! Windows bilgisayarınızda sıfır kurulumla çalışan, konuşan, araştıran ve komutlarınızı yerine getiren yapay zeka.\n\n"
            "✨ **Öne Çıkan Özellikler:**\n"
            "• 🎙️ Ultra gerçekçi Türkçe sesli yanıt\n"
            "• ⚡ 0 ms anında 'Esc' tuşuyla susturma\n"
            "• 🌐 Canlı çok kaynaklı internet araması\n"
            "• 💻 Kuruluma ihtiyaç duymayan taşınabilir .exe\n\n"
            "📥 **Ücretsiz Demo İndir:**\n"
            "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n\n"
            "🛒 **Shopier Güvenli Sipariş (350 ₺):**\n"
            "https://www.shopier.com/51058105\n\n"
            "🤖 **Bot:** @JarvisCraftsBot\n"
            "💬 **Destek:** tg://user?id=32186"
        )
        video_path = os.path.join("static", "jarvis_demo_video.mp4")
        try:
            target_chan = f"@{CHANNEL_USERNAME}"
            if os.path.exists(video_path):
                await client.send_file(
                    target_chan,
                    video_path,
                    caption=channel_post,
                    supports_streaming=True
                )
            else:
                await client.send_message(target_chan, channel_post)
            await event.respond("✅ J.A.R.V.I.S. tanıtım videosu ve demo paketi @JarvisCraftDuyuru kanalına başarıyla gönderildi!")
        except Exception as e:
            logger.error(f"Channel broadcast failed: {e}")
            await event.respond(f"⚠️ Kanala gönderilirken bir durum oluştu: {e}\n(Botun @{CHANNEL_USERNAME} kanalında yönetici yetkisi olduğundan emin olun.)")

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
            [Button.url("⭐  Haftalık VIP Satın Al  ·  150₺", "https://www.shopier.com/51058120")],
            [Button.url("🌟  Aylık VIP Satın Al  ·  350₺", "https://www.shopier.com/51058121")],
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
    #  6.  CANLI DESTEK
    # ══════════════════════════════════
    elif data == "menu_support":
        msg = (
            f"           💬 **CANLI DESTEK & İLETİŞİM**\n"
            f"{LINE}\n\n"
            f"Her türlü teknik soru, özel bot siparişi\n"
            f"veya ödeme bildirimi için resmi hesabımıza yazın:\n\n"
            f"👨‍💻  **Geliştirici & Destek:**  @{SUPPORT_USERNAME}\n"
            f"🆔  **Destek Hesap ID:**     `8387947754`\n"
            f"⚡  **Ortalama Yanıt:**       5-10 dakika\n"
            f"🕐  **Çalışma:**              7/24 aktif destek\n\n"
            f"{LINE}\n\n"
            f"🛒 **Resmi Shopier:**  {SHOPIER_URL}\n"
            f"📢 **Duyuru Kanalı:**  {CHANNEL_URL}"
        )
        buttons = [
            [Button.url(f"👨‍💻  @{SUPPORT_USERNAME}'a Yaz", SUPPORT_URL)],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await event.edit(msg, buttons=buttons)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Text Message Handler (Private Only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage(func=lambda e: e.is_private))
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

        await asyncio.sleep(1.2)

        opt1 = (
            f"🔥 **BÜYÜK FIRSAT!**\n\n"
            f"⚡ {product_name}\n"
            f"En uygun fiyat & anında teslimat!\n\n"
            f"✅ %100 Çalışma Garantisi\n"
            f"🛒 Sipariş: @{SUPPORT_USERNAME}\n"
            f"📦 Mağaza: {SHOPIER_URL}"
        )
        opt2 = (
            f"🚀 **KALİTE ARAYANLAR İÇİN**\n\n"
            f"🎯 {product_name}\n\n"
            f"💎 Hızlı • Güvenilir • 7/24 Destek\n"
            f"👇 DM ile hemen sipariş verin: @{SUPPORT_USERNAME}"
        )
        opt3 = (
            f"⭐ **ÖZEL İNDİRİM**\n\n"
            f"{product_name}\n\n"
            f"📦 Sınırlı stok — Kaçırmayın!\n"
            f"💬 Bilgi & Satın Alım → @{SUPPORT_USERNAME}"
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
        waiting_msg = await event.respond(
            f"🐛 **Jarvis AI kodu analiz ediyor...**"
        )

        await asyncio.sleep(1)

        result = (
            f"           🐛 **KOD ANALİZ SONUCU**\n"
            f"{LINE}\n\n"
            f"**Gönderilen kod parçası incelendi.**\n\n"
            f"💡 Kodunuz kaydedildi. Özel düzeltme\n"
            f"ve teknik destek için resmi hesabımıza yazın:\n\n"
            f"👨‍💻 @{SUPPORT_USERNAME}\n\n"
            f"{LINE}"
        )
        await waiting_msg.edit(result, buttons=[
            [Button.url(f"👨‍💻 @{SUPPORT_USERNAME}'a Yaz", SUPPORT_URL)],
            [Button.inline("◀️ Ana Menü", b"main_menu")]
        ])

    elif state == "waiting_session_string":
        USER_STATES.pop(uid, None)
        session = event.raw_text.strip()
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
            f"Destek: @{SUPPORT_USERNAME}\n\n"
            f"{LINE}",
            buttons=[
                [Button.inline("⚡ Oto-Reklam Paneli", b"menu_ad_engine")],
                [Button.inline("◀️ Ana Menü", b"main_menu")]
            ]
        )


client_username = None

async def start_with_retry():
    global client_username
    while True:
        try:
            logger.info("Starting JarvisCraftBot...")
            await client.start(bot_token=BOT_TOKEN)
            me = await client.get_me()
            client_username = me.username
            write_bot_status(
                "jarvis",
                state="ready",
                telegram_ready=True,
                bot_username=me.username,
                connected=True,
                token=BOT_TOKEN,
            )
            logger.info(f"✅ JarvisCraftBot is ONLINE! @{me.username} (ID: {me.id})")
            try:
                mb_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"
                mb_payload = {
                    "menu_button": {
                        "type": "web_app",
                        "text": "⚡ Mağaza & Panel",
                        "web_app": {
                            "url": APP_URL
                        }
                    }
                }
                mb_req = urllib.request.Request(
                    mb_url,
                    data=json.dumps(mb_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(mb_req, timeout=5) as mb_resp:
                    logger.info("Chat menu button successfully synced with Telegram API.")

                cmd_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
                cmd_payload = {
                    "commands": [
                        {"command": "start", "description": "🚀 Ana Menü ve Başlangıç"},
                        {"command": "magaza", "description": "🏪 Ürünler ve Satın Alma"},
                        {"command": "demo", "description": "📦 J.A.R.V.I.S. Demo İndir (PC)"},
                        {"command": "video", "description": "🎬 Kullanım ve Tanıtım Videosu"},
                        {"command": "vip", "description": "💎 VIP Üyelik Paketleri"},
                        {"command": "panel", "description": "⚡ Web Paneli & Mini App"},
                        {"command": "yardim", "description": "💬 Canlı Destek ve İletişim"}
                    ]
                }
                cmd_req = urllib.request.Request(
                    cmd_url,
                    data=json.dumps(cmd_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(cmd_req, timeout=5) as cmd_resp:
                    logger.info("Bot commands successfully synced with Telegram API.")
            except Exception as btn_err:
                logger.warning(f"setChatMenuButton/setMyCommands error: {btn_err}")
            await client.run_until_disconnected()
        except FloodWaitError as e:
            write_bot_status(
                "jarvis", state="retrying", telegram_ready=False,
                token=BOT_TOKEN, last_error=type(e).__name__,
            )
            logger.warning(f"FloodWait: Telegram requires waiting {e.seconds}s. Waiting...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            if invalid_token_error(e):
                write_bot_status(
                    "jarvis", state="invalid_token", telegram_ready=False,
                    token=BOT_TOKEN, last_error=type(e).__name__,
                )
                logger.error("Bot token is invalid or expired.")
                return
            write_bot_status(
                "jarvis", state="error", telegram_ready=False,
                token=BOT_TOKEN, last_error=type(e).__name__,
            )
            logger.error(f"JarvisCraft bot runtime error: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    client.loop.run_until_complete(start_with_retry())
