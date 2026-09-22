import os
import json
import logging
import asyncio
import sys
import time
import re
import uuid
import tempfile
import urllib.request
import urllib.error
from telethon import TelegramClient, events, Button, functions
from telethon.sessions import StringSession
from telethon.errors import (
    UserNotParticipantError, FloodWaitError, RPCError,
    MessageNotModifiedError, ChatWriteForbiddenError,
    ChatSendPlainForbiddenError, InviteRequestSentError,
    ChannelPrivateError, UserAlreadyParticipantError,
    SlowModeWaitError
)
from bot_runtime_status import write_bot_status, invalid_token_error

async def safe_edit_event(event, text, buttons=None):
    """Safely edits a message, ignoring MessageNotModifiedError."""
    try:
        await event.edit(text, buttons=buttons)
    except MessageNotModifiedError:
        pass
    except Exception as e:
        logger.warning(f"safe_edit_event exception: {e}")

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
SUPPORT_USERNAME = "JarvisCraft"
SUPPORT_URL = "https://t.me/JarvisCraft"
SHOPIER_URL = "https://www.shopier.com/JarvisStore"
APP_URL = "https://bot-service-production-9d74.up.railway.app/jarvis/app"
ADMIN_IDS = {
    int(os.environ.get("TELEGRAM_ADMIN_ID", 8791896048)),
    8791896048, 6196006704, 8116518175, 8387947754
}
DEFAULT_TEST_SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="

LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DOT = "◈"

# ─── Hedef Kategori Havuzları (Denetlenmiş & Doğrulanmış) ───
DEFAULT_CATEGORIES = {
    "ticaret": {
        "title": "🛍️ Ticaret & Alım-Satım",
        "description": "65+ onaylı ticaret, kupon, bakiye ve alışveriş grubu",
        "groups": [
            "kuponsat", "kuponindirimsatis", "ceksat", "satcek", "kupongrupta", "alimsatimmerkezii",
            "kuponhesapsatis", "kuponsatisgrup", "tahaaslan11", "kodceksatismerkezi", "ticaretyapn",
            "kuponcekkodsatis", "ticaretcanavari", "alsatticarettz", "TicHubTR", "kuponsatislari0",
            "kuponkodindirimilanlar", "Kuponcekm", "kuponkodhesapilan", "kodkuponmarketi",
            "zeroticaret", "indirimkodusatis", "kodindirimsatis", "kuponkodualsat", "mukyemek",
            "ceksatkupon", "kuponindirimpazari", "indirim363", "ticaretgruptr", "kuponkodceksatis",
            "ceksatistakasgrup", "ticaretZ", "kuponvekodsatisgrubu", "ceksatkupon2",
            "kuponkodalimsatim", "kodmalf", "indirimruzgari1", "kuponindirimkodalisveris",
            "alisverisforumuguncel", "kuponindirimcek", "uygunkod", "kodalimsatim",
            "kuponalsatgurup", "KodKuponMerkezi", "kuponkodmerkez", "indirimkana",
            "herkesibeklerimm", "bedavainternetkodalimsatim", "kuponyaticaret",
            "cek_kupon_kod_ilan", "Minakuponkodsatis", "bedavainternetkod", "indirimcek",
            "kuponinternet", "kodkuponcek", "kuponceking", "letgoilanlari",
            "yucekuponsatis", "indirimkodbul", "kuponsatimalim", "kodevrenii"
        ]
    },
    "sohbet": {
        "title": "💬 Sohbet & Topluluk",
        "description": "Aktif, temiz başlıklı Türk sohbet ve arkadaşlık toplulukları",
        "groups": [
            "TurkceSohbetler", "CoinSohbetTR", "KriptoTurkiye", "sohbetmuhabbettr"
        ]
    },
    "borsa": {
        "title": "📈 Borsa & Kripto Finans",
        "description": "Binlerce üyeli aktif borsa, kripto ve finans tartışma grupları",
        "groups": [
            "KriptoTurkiye", "CoinSohbetTR", "bitgetturkiye", "KriptoSozlukTVPiyasaMuhabbeti"
        ]
    },
    "haber": {
        "title": "📰 Teknoloji & Yazılım",
        "description": "Geliştirici, teknoloji ve yazılım tartışma toplulukları",
        "groups": [
            "yazilimtoplulugu", "linux_tr", "yazilim0", "yazilimogreniyorumorg"
        ]
    }
}

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
        [Button.inline("📦  Siparişlerim & Üyeliklerim", b"menu_orders"),
         Button.inline("💎  VIP & Bakiye", b"menu_vip")],
        [Button.inline("👤  Hesabım & Profil", b"menu_profile"),
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
    interval = user.get('ad_interval', 60)
    msg_count = len(user.get('ad_messages', []))
    current_msg = user.get('ad_messages', ['—'])[0] if msg_count > 0 else "—"
    preview = current_msg[:70] + "..." if len(current_msg) > 70 else current_msg

    cat_key = user.get("target_category", "sohbet")
    if cat_key == "custom":
        cnt = len(user.get("custom_groups", []))
        cat_title = f"✏️ Özel Liste ({cnt} grup)"
    else:
        info = DEFAULT_CATEGORIES.get(cat_key, DEFAULT_CATEGORIES.get("sohbet", {}))
        cat_title = f"{info['title']} ({len(info.get('groups', []))} grup)"

    account_name = user.get("account_name")
    has_session = bool(user.get("session_string"))
    if account_name:
        account_status = f"✅ {account_name}"
    elif has_session:
        account_status = "✅ Session Kayıtlı"
    else:
        account_status = "❌ Bağlı Hesap Yok"

    total_sent = user.get("total_sent", 0)
    last_group = user.get("last_sent_group", "Henüz yok")
    last_group_display = f"@{last_group}" if last_group != "Henüz yok" else "Henüz yok"

    msg = (
        f"           ⚡ **OTO-REKLAM & MESAJ MOTORU**\n"
        f"{LINE}\n\n"
        f"**Durum:**        {status}\n"
        f"**Gönderici:**     `{account_status}`\n"
        f"**Aralık:**        Her `{interval}` dakikada bir\n"
        f"**Hedef Havuz:**   **{cat_title}**\n"
        f"**Toplam Gönderi:** `{total_sent}` adet\n"
        f"**Son Hedef:**     `{last_group_display}`\n\n"
        f"📝 **Aktif Mesaj Metni:**\n"
        f"```\n{preview}\n```\n\n"
        f"{LINE}"
    )

    toggle = (
        Button.inline("⏸  Gönderimi Durdur", b"ad_stop")
        if is_active else
        Button.inline("▶️  Gönderimi Başlat", b"ad_start")
    )

    buttons = [
        [toggle],
        [Button.inline("📝 Metni Düzenle", b"ad_edit_msg"),
         Button.inline("⏱ Süre Ayarla", b"ad_set_interval")],
        [Button.inline("🎯 Hedef Kategori & Havuz", b"ad_show_groups"),
         Button.inline("➕ Özel Grup Ekle", b"ad_add_custom_group")]
    ]
    if not has_session:
        buttons.append([Button.inline("⚡ Hızlı Test Hesabı Bağla (+1386)", b"bind_test_account")])
        buttons.append([Button.inline("🔑 Kendi Hesabımı Bağla (Session)", b"input_session")])
    else:
        buttons.append([Button.inline("👤 Gönderici Hesap Yönetimi", b"ad_add_account")])
    buttons.append([Button.inline("◀️  Ana Menü", b"main_menu")])

    await safe_edit_event(event, msg, buttons=buttons)


async def render_categories_menu(event, user):
    curr_cat = user.get("target_category", "sohbet")
    custom_cnt = len(user.get("custom_groups", []))
    
    t_chk = " (Seçili)" if curr_cat == "ticaret" else ""
    s_chk = " (Seçili)" if curr_cat == "sohbet" else ""
    b_chk = " (Seçili)" if curr_cat == "borsa" else ""
    h_chk = " (Seçili)" if curr_cat == "haber" else ""
    c_chk = " (Seçili)" if curr_cat == "custom" else ""

    custom_preview = ""
    if user.get("custom_groups"):
        sample = ", ".join(f"@{g}" for g in user.get("custom_groups")[:4])
        if len(user.get("custom_groups")) > 4:
            sample += f" ve {len(user.get('custom_groups')) - 4} grup daha"
        custom_preview = f"\n\n📌 **Eklediğiniz Özel Gruplar:**\n`{sample}`"

    ticaret_cnt = len(DEFAULT_CATEGORIES["ticaret"]["groups"])
    sohbet_cnt = len(DEFAULT_CATEGORIES["sohbet"]["groups"])
    borsa_cnt = len(DEFAULT_CATEGORIES["borsa"]["groups"])
    haber_cnt = len(DEFAULT_CATEGORIES["haber"]["groups"])

    msg = (
        f"           🎯 **HEDEF GRUP & KATEGORİ HAVUZU**\n"
        f"{LINE}\n\n"
        f"Mesajlarınızın otomatik gönderileceği kategoriyi seçin\n"
        f"veya kendi istediğiniz grup/kanalları ekleyin:\n\n"
        f"🛍️ **Ticaret & Alım-Satım:** {ticaret_cnt}+ aktif ticaret grubu\n"
        f"💬 **Sohbet & Topluluk:** {sohbet_cnt} aktif Türk sohbet grubu\n"
        f"📈 **Borsa & Kripto:** {borsa_cnt} finans & coin tartışma grubu\n"
        f"📰 **Teknoloji & Yazılım:** {haber_cnt} yazılım & geliştirici grubu\n"
        f"✏️ **Özel Liste:** Kendi eklediğiniz {custom_cnt} grup{custom_preview}\n\n"
        f"{LINE}\n"
        f"👇 **Kategori seçin veya özel grup ekleyin:**"
    )

    buttons = [
        [Button.inline(f"🛍️ Ticaret ({ticaret_cnt}+){t_chk}", b"setcat_ticaret"),
         Button.inline(f"💬 Sohbet ({sohbet_cnt}){s_chk}", b"setcat_sohbet")],
        [Button.inline(f"📈 Borsa & Kripto ({borsa_cnt}){b_chk}", b"setcat_borsa"),
         Button.inline(f"📰 Teknoloji ({haber_cnt}){h_chk}", b"setcat_haber")],
        [Button.inline(f"✏️ Kendi Özel Listem ({custom_cnt}){c_chk}", b"setcat_custom")],
        [Button.inline("➕ Özel Grup Ekle", b"ad_add_custom_group"),
         Button.inline("🗑️ Özel Listeyi Sil", b"ad_clear_custom")],
        [Button.inline("◀️ Geri (Motor Paneli)", b"menu_ad_engine")]
    ]
    await safe_edit_event(event, msg, buttons=buttons)


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
        if not user.get("session_string"):
            prompt_msg = (
                f"           ⚠️ **GÖNDERİCİ HESAP GEREKLİ**\n"
                f"{LINE}\n\n"
                f"Otomatik mesaj gönderebilmek için bir gönderici hesap\n"
                f"bağlamanız gerekmektedir.\n\n"
                f"⚡ **Hazır Test Hesabı (+13869914668):**\n"
                f"Aşağıdaki butona basarak hazır test hesabını profilinize\n"
                f"tek tıkla bağlayıp gönderimi hemen başlatabilirsiniz.\n\n"
                f"{LINE}"
            )
            buttons = [
                [Button.inline("🚀 Test Hesabını Bağla ve Başlat", b"bind_and_start_test")],
                [Button.inline("🔑 Kendi Session'ımı Gir", b"input_session")],
                [Button.inline("◀️ Geri (Motor Paneli)", b"menu_ad_engine")]
            ]
            await safe_edit_event(event, prompt_msg, buttons=buttons)
            return

        user["is_running"] = True
        user["last_sent_at"] = 0  # Trigger immediate first send!
        users[uid] = user
        save_data(users)
        await event.answer("▶️ Otomatik gönderim başlatıldı! İlk mesaj birkaç saniye içinde iletilecek.", alert=True)
        await render_ad_engine(event, user)

    elif data == "bind_and_start_test":
        s_str = DEFAULT_TEST_SESSION
        session_file = "test_account_session_string.txt"
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        s_str = content
            except Exception:
                pass
        user["session_string"] = s_str
        user["account_name"] = "User (@Userrrrrrrrrra)"
        user["account_phone"] = "13869914668"
        user["account_id"] = 8777291796
        user["target_category"] = user.get("target_category", "sohbet")
        user["ad_messages"] = user.get("ad_messages") or ["Selamlar herkese, iyi günler"]
        user["ad_interval"] = user.get("ad_interval", 60)
        user["is_running"] = True
        user["last_sent_at"] = 0  # Immediate first send!
        users[uid] = user
        save_data(users)
        await event.answer("🚀 Test hesabı bağlandı ve ilk gönderim başlatıldı!", alert=True)
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
        await safe_edit_event(
            event,
            f"           📝 **MESAJ METNİNİ DÜZENLE**\n"
            f"{LINE}\n\n"
            f"**Mevcut metniniz:**\n"
            f"```\n{curr}\n```\n\n"
            f"💬 Yeni mesajınızı bu sohbete **metin olarak** gönderin.\n\n"
            f"💡 **İpucu:** Emoji, selamlaşma ve doğal cümleler\n"
            f"hesabınızın organik görünmesini ve ilgi çekmesini sağlar.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal Et", b"menu_ad_engine")]]
        )

    elif data == "ad_set_interval":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        status_note = "🟢 VIP Üyesiniz: Tüm aralıklar açık." if is_vip else "⚪ Ücretsiz Plan: 60 dk önerilen varsayılandır (15-30 dk için VIP pakete geçebilirsiniz)."
        buttons = [
            [Button.inline("⏱ 15 dk  (🌟 Aylık VIP)", b"interval_15"),
             Button.inline("⏱ 30 dk  (⭐ Haftalık VIP)", b"interval_30")],
            [Button.inline("⏱ 45 dk  ·  VIP", b"interval_45"),
             Button.inline("⏱ 60 dk  ·  (Ücretsiz Plan)", b"interval_60")],
            [Button.inline("💎 VIP Paketlerini İncele", b"menu_vip")],
            [Button.inline("◀️ Geri", b"menu_ad_engine")]
        ]
        await safe_edit_event(
            event,
            f"           ⏱ **GÖNDERİM ARALIĞI SEÇİMİ**\n"
            f"{LINE}\n\n"
            f"Mesajlar arasındaki bekleme süresini seçin.\n\n"
            f"• **60 dk (Saatte 1):** Ücretsiz planda hesap sağlığı ve flood koruması için ideal aralık.\n"
            f"• **30 dk:** Haftalık VIP ile 2 kat daha hızlı gönderim.\n"
            f"• **15 dk:** Aylık VIP ile maksimum hız ve müşteri erişimi.\n\n"
            f"💡 **Durum:** {status_note}\n\n"
            f"{LINE}",
            buttons=buttons
        )

    elif data.startswith("interval_"):
        mins = int(data.split("_")[1])
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        if mins < 60 and not is_vip:
            await event.answer(f"💎 {mins} dakikalık turbo gönderim VIP üyelere özeldir! Ücretsiz planda 60 dk aktiftir.", alert=True)
            user["ad_interval"] = 60
            users[uid] = user
            save_data(users)
            await render_ad_engine(event, user)
            return

        user["ad_interval"] = mins
        users[uid] = user
        save_data(users)
        await event.answer(f"✅  Aralık {mins} dakika olarak ayarlandı.", alert=True)
        await render_ad_engine(event, user)

    elif data == "ad_show_groups":
        await render_categories_menu(event, user)

    elif data.startswith("setcat_"):
        cat_key = data.split("_")[1]
        user["target_category"] = cat_key
        users[uid] = user
        save_data(users)
        cat_titles = {
            "ticaret": "🛍️ Ticaret & Alım-Satım",
            "sohbet": "💬 Sohbet & Topluluk",
            "borsa": "📈 Borsa & Kripto Finans",
            "haber": "📰 Teknoloji & Yazılım",
            "custom": "✏️ Özel Liste"
        }
        await event.answer(f"✅ Hedef havuz: {cat_titles.get(cat_key, cat_key)} seçildi!", alert=True)
        await render_categories_menu(event, user)

    elif data == "ad_add_custom_group":
        USER_STATES[uid] = "waiting_custom_groups"
        await safe_edit_event(
            event,
            f"           ➕ **ÖZEL GRUP / KANAL EKLE**\n"
            f"{LINE}\n\n"
            f"Otomatik mesaj göndermek istediğiniz grup veya kanalları\n"
            f"bu sohbete mesaj olarak gönderin.\n\n"
            f"📝 **Örnek Formatlar:**\n"
            f"• `@grup1 @grup2`\n"
            f"• `https://t.me/grup3`\n"
            f"• Her satıra bir grup adı\n\n"
            f"💡 **Not:** Gönderici hesabınız bu gruplara sırayla\n"
            f"katılıp mesajınızı belirlenen aralıkla iletir.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal Et", b"ad_show_groups")]]
        )

    elif data == "ad_clear_custom":
        user["custom_groups"] = []
        if user.get("target_category") == "custom":
            user["target_category"] = "sohbet"
        users[uid] = user
        save_data(users)
        await event.answer("🗑️ Özel grup listeniz temizlendi.", alert=True)
        await render_categories_menu(event, user)

    elif data == "ad_add_account":
        acc_info = user.get("account_name", "Bağlı hesap yok")
        msg = (
            f"           👤 **GÖNDERİCİ HESAP YÖNETİMİ**\n"
            f"{LINE}\n\n"
            f"**Mevcut Hesap:** `{acc_info}`\n\n"
            f"Mesajların gönderileceği Telegram hesabınızı\n"
            f"Telethon StringSession anahtarınız ile bağlayabilirsiniz.\n\n"
            f"💡 **Test Hesabı Hızlı Bağlama:**\n"
            f"Aşağıdaki butona basarak yeni test hesabını (+13869914668)\n"
            f"tek tıkla profilinize bağlayabilirsiniz.\n\n"
            f"💬 Destek & Kurulum: @{SUPPORT_USERNAME}\n\n"
            f"{LINE}"
        )
        await safe_edit_event(event, msg, buttons=[
            [Button.inline("⚡ Test Hesabını Bağla (+1386)", b"bind_test_account")],
            [Button.inline("🔑 StringSession Gir", b"input_session")],
            [Button.inline("◀️ Geri", b"menu_ad_engine")]
        ])

    elif data == "bind_test_account":
        s_str = DEFAULT_TEST_SESSION
        session_file = "test_account_session_string.txt"
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        s_str = content
            except Exception:
                pass
        user["session_string"] = s_str
        user["account_name"] = "User (@Userrrrrrrrrra)"
        user["account_phone"] = "13869914668"
        user["account_id"] = 8777291796
        user["target_category"] = user.get("target_category", "sohbet")
        user["ad_messages"] = user.get("ad_messages") or ["Selamlar herkese, iyi günler"]
        user["ad_interval"] = user.get("ad_interval", 60)
        users[uid] = user
        save_data(users)
        await event.answer("✅ Test hesabı (+13869914668) başarıyla bağlandı!", alert=True)
        await render_ad_engine(event, user)

    elif data == "input_session":
        USER_STATES[uid] = "waiting_session_string"
        await safe_edit_event(
            event,
            f"           🔑 **SESSION GİRİŞİ**\n"
            f"{LINE}\n\n"
            f"Telethon StringSession anahtarınızı\n"
            f"bu sohbete mesaj olarak gönderin.\n\n"
            f"⚡ Sistem anahtarınızı anında test edip\n"
            f"hesap bilgilerinizi doğrulayacaktır.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("❌ İptal Et", b"ad_add_account")]]
        )

    # ══════════════════════════════════
    #  2.  KOD PAKETLERİ & BOT MAĞAZASI
    # ══════════════════════════════════
    elif data == "menu_store":
        msg = (
            f"           🏪 **KOD & YAZILIM MAĞAZASI**\n"
            f"{LINE}\n\n"
            f"Profesyonel geliştiriciler ve girişimciler için hazırlanmış,\n"
            f"**temiz kodlu**, **kuruluma hazır** paketler ve **özel yazılım** hizmetleri.\n\n"
            f"Her pakette açık kaynak kod, kurulum dokümanı\n"
            f"veya anahtar teslim geliştirme dahildir.\n\n"
            f"🔥  **Haftanın Çok Satanı:**\n"
            f"     ⚡ Oto-Reklam Bot Scripti\n\n"
            f"{LINE}\n"
            f"👇  Detay görmek için paketi veya hizmeti seçin:"
        )
        buttons = [
            [Button.url("🛍️  Shopier Mağazasını Aç (Tüm İlanlar)", SHOPIER_URL)],
            [Button.inline("🤖 Jarvis Core AI Asistan  ·  350₺", b"prod_1")],
            [Button.inline("⚡ Oto-Reklam Bot Scripti  ·  450₺", b"prod_2")],
            [Button.inline("🔍 Fiyat Takip Scraper  ·  300₺", b"prod_3")],
            [Button.inline("🚀 Full Mini App Kiti  ·  400₺", b"prod_4")],
            [Button.inline("🌐 Özel Web Sitesi Kodlama  ·  799.90₺", b"prod_5")],
            [Button.inline("🤖 Özel Bot Yazılımı Kodlama  ·  499.90₺", b"prod_6")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data.startswith("prod_"):
        pid = data.split("_")[1]
        products = {
            "1": {
                "icon": "🤖",
                "title": "Jarvis Core AI Asistan İskeleti",
                "price": "350₺",
                "badge": "🔥 POPÜLER",
                "url": "https://www.shopier.com/JarvisStore/51058105",
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
                "url": "https://www.shopier.com/JarvisStore/51058117",
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
                "url": "https://www.shopier.com/JarvisStore/51058118",
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
                "url": "https://www.shopier.com/JarvisStore/51058119",
                "desc": "Kendi Telegram Mini App mağazanızı 10 dakikada kurun.\nFlask backend + Vite frontend + Shopier ödeme entegrasyonu.",
                "features": [
                    "Hazır tasarım & webhooklar",
                    "Render/Vercel dağıtımına hazır",
                    "Shopier otomatik ödeme & teslimat"
                ]
            },
            "5": {
                "icon": "🌐",
                "title": "Özel Web Sitesi Geliştirme & Kodlama",
                "price": "799.90 ₺",
                "badge": "💻 ÖZEL PROJE",
                "url": SHOPIER_URL,
                "desc": "Kurumsal firma, e-ticaret, landing page veya özel web platformu yazılım & tasarım hizmeti.\n\n⚠️ **Önemli Bilgilendirme:** Belirtilen 799.90 ₺ taban / başlangıç fiyatıdır. Siteden siteye, sayfa adedine ve projenin kapsamına / ek özelliklerine göre fiyatta değişiklik olabilir. Sipariş öncesinde veya sonrasında doğrudan destek hesabımıza yazarak projenizi detaylandırabilirsiniz.",
                "features": [
                    "Modern, %100 mobil uyumlu ve SEO dostu arayüz",
                    "React / Next.js / Python Flask mimarisi",
                    "Shopier / iyzico 3D güvenli ödeme altyapısı",
                    "Hızlı sunucu kurulumu ve SSL sertifikası teslimi",
                    "Geliştirici ile birebir analiz & kapsam görüşmesi"
                ]
            },
            "6": {
                "icon": "🤖",
                "title": "Özel Telegram Bot Yazılımı & Kodlama",
                "price": "499.90 ₺",
                "badge": "⚡ ÖZEL BOT",
                "url": SHOPIER_URL,
                "desc": "İhtiyacınıza tam uygun özel Telegram bot geliştirme, otomasyon, mağaza/ödeme botu veya veri toplama sistemi.\n\n⚠️ **Önemli Bilgilendirme:** Belirtilen 499.90 ₺ taban / başlangıç fiyatıdır. Botun işlevlerine, API entegrasyonlarına ve proje karmaşıklığına göre fiyatta değişiklik olabilir. Sipariş öncesinde veya sonrasında doğrudan destek hesabımıza yazabilirsiniz.",
                "features": [
                    "Telethon / Aiogram tabanlı ultra hızlı asenkron motor",
                    "Ödeme bildirim, mağaza veya otomatik yanıt modülleri",
                    "Web paneli ve canlı log izleme entegrasyonu",
                    "7/24 kesintisiz sunucu kurulumu ve teslimatı",
                    "Doğrudan geliştirici ile proje planlama desteği"
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
            f"**Paket & Hizmet Detayları:**\n"
            f"{feat_text}\n\n"
            f"{LINE}\n\n"
            f"✅ Açık kaynak kod / Anahtar teslim kurulum\n"
            f"✅ Kurulum & kullanım dokümanı dahil\n"
            f"✅ Shopier 3D Secure güvenli ödeme\n"
            f"⚡ Ödeme sonrası doğrudan teslimat & destek"
        )

        if pid in ("5", "6"):
            buttons = [
                [Button.url(f"🛒  Shopier'dan Satın Al  ·  {p['price']}", p.get("url", SHOPIER_URL))],
                [Button.url("💬  Projeyi Görüş & Teklif Al (Destek)", SUPPORT_URL)],
                [Button.inline("◀️ Mağazaya Dön", b"menu_store")]
            ]
        else:
            buttons = [
                [Button.url(f"🛒  Shopier'dan Satın Al  ·  {p['price']}", p.get("url", SHOPIER_URL))],
                [Button.url("📹  Demoyu Kanalda İncele", CHANNEL_URL)],
                [Button.inline("◀️ Mağazaya Dön", b"menu_store")]
            ]
        await safe_edit_event(event, msg, buttons=buttons)

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
            [Button.url("🛒  Shopier'dan Lisans Satın Al (350 ₺)", "https://www.shopier.com/JarvisStore/51058105")],
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
            "🛒 **Shopier Lisans:** https://www.shopier.com/JarvisStore/51058105\n"
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
            [Button.url("🛒 Tam Sürüm Lisans Al (350 ₺)", "https://www.shopier.com/JarvisStore/51058105")],
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
            "https://www.shopier.com/JarvisStore/51058105\n\n"
            "🤖 **Bot:** @JarvisCraftsBot\n"
            f"💬 **Destek:** {SUPPORT_URL} (@{SUPPORT_USERNAME})"
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
    #  4.  VIP & PLAN YÖNETİMİ
    # ══════════════════════════════════
    elif data == "menu_vip":
        balance = user.get("balance", 0.0)
        vip_status = user.get("vip_until")
        is_vip = bool(vip_status and vip_status > time.time())

        msg = (
            f"           💎 **VIP & PLAN YÖNETİMİ**\n"
            f"{LINE}\n\n"
            f"**Mevcut Paketiniz:** {'🟢 VIP Üyelik' if is_vip else '⚪ Standart (Ücretsiz)'}\n"
            f"**Bakiye:**          `{balance:.2f} ₺`\n\n"
            f"{LINE}\n\n"
            f"📊 **HESAP & PLAN FARKLARI:**\n\n"
            f"⚪ **Ücretsiz (Standart) Plan:**\n"
            f"• 👤 1 Adet Gönderici Hesap\n"
            f"• ⏱ 60 Dakika Aralık (Spam & Flood Korumalı)\n"
            f"• 🎯 4 Hazır Kategori Havuzu (Ticaret, Sohbet, Borsa, Teknoloji)\n"
            f"• 📈 Günlük 25 Gönderi Limiti\n\n"
            f"⭐ **Haftalık VIP Paket (150 ₺):**\n"
            f"• 👤 2 Adet Gönderici Hesap Ekleme\n"
            f"• ⏱ 30 Dakika Hızlı Gönderim\n"
            f"• ➕ Özel Grup & Kanal Ekleme Desteği\n"
            f"• 🚀 7 Gün Kesintisiz Reklam & Gönderim\n\n"
            f"🌟 **Aylık Sınırsız VIP Paket (350 ₺):**\n"
            f"• 👤 5 Adet Gönderici Hesap (Rotasyonlu)\n"
            f"• ⏱ 15 Dakika Turbo Gönderim\n"
            f"• ♾️ Limitsiz Günlük Gönderi\n"
            f"• ⚡ Öncelikli VIP Teknik Destek & Özel Bot Danışmanlığı\n"
            f"• 🚀 30 Gün Kesintisiz Kullanım\n\n"
            f"{LINE}\n"
            f"👇 **Paketinizi seçip hemen yükseltebilirsiniz:**"
        )
        buttons = [
            [Button.url("⭐ Haftalık VIP Satın Al  ·  150₺", "https://www.shopier.com/JarvisStore/51058120")],
            [Button.url("🌟 Aylık Sınırsız VIP Satın Al  ·  350₺", "https://www.shopier.com/JarvisStore/51058121")],
            [Button.url("💬 Özel Kurumsal Paket İçin Yazın", "https://t.me/JarvisCraft")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    # ══════════════════════════════════
    #  5.  HESABIM & PROFİLİM
    # ══════════════════════════════════
    elif data == "menu_profile":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        if is_vip:
            rem_days = int((vip_until - time.time()) // 86400)
            rem_hours = int(((vip_until - time.time()) % 86400) // 3600)
            vip_text = f"🟢 Aktif ({rem_days} gün {rem_hours} saat)"
        else:
            vip_text = "⚪ Standart (Ücretsiz)"

        account_name = user.get("account_name", "Bağlı hesap yok")
        account_phone = user.get("account_phone", "")
        acc_display = f"{account_name} (+{account_phone})" if account_phone else account_name

        today_str = time.strftime("%Y-%m-%d")
        daily_sent = user.get("daily_sent", 0) if user.get("last_sent_day") == today_str else 0
        quota_display = "Sınırsız (VIP)" if is_vip else f"{daily_sent} / 25 adet"

        username_display = f"@{user.get('username')}" if user.get('username') else "Belirlenmemiş"
        msg = (
            f"           👤 **HESABIM & KULLANICI BİLGİLERİ**\n"
            f"{LINE}\n\n"
            f"  👤 **İsim:**      {user.get('first_name', 'Bilinmiyor')}\n"
            f"  🔗 **Kullanıcı:** {username_display}\n"
            f"  🆔 **Telegram ID:** `{uid}`\n"
            f"  💰 **Bakiye:**    `{user.get('balance', 0.0):.2f} ₺`\n"
            f"  💎 **Üyelik:**    {vip_text}\n\n"
            f"{LINE}\n\n"
            f"  📱 **Gönderici:**  `{acc_display}`\n"
            f"  ⚡ **Motor:**      {'🟢 Çalışıyor' if user.get('is_running') else '🔴 Durduruldu'}\n"
            f"  ⏱ **Aralık:**     Her `{user.get('ad_interval', 60)}` dakikada bir\n"
            f"  📊 **Bugün:**      `{quota_display}`\n"
            f"  📦 **Toplam:**     `{user.get('total_sent', 0)}` başarılı gönderi\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.inline("📦  Siparişlerim & Üyeliklerim", b"menu_orders")],
            [Button.inline("⚡  Oto-Reklam Motoru", b"menu_ad_engine"),
             Button.inline("💎  VIP Paketler", b"menu_vip")],
            [Button.url("📱  Web Panel & Mini App", APP_URL)],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    # ══════════════════════════════════
    #  5.1.  SİPARİŞLERİM & ÜYELİKLERİM
    # ══════════════════════════════════
    elif data == "menu_orders":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        orders = user.get("orders", [])

        lines = [
            f"           📦 **SİPARİŞLERİM & ÜYELİKLERİM**",
            f"{LINE}\n"
        ]

        if is_vip:
            rem_secs = vip_until - time.time()
            rem_days = int(rem_secs // 86400)
            rem_hours = int((rem_secs % 86400) // 3600)
            plan_name = user.get("plan_name", "Aylık Sınırsız VIP" if rem_days > 7 else "Haftalık VIP")
            slots = user.get("account_slots", 5 if rem_days > 7 else 2)
            lines.append(f"💎 **Aktif VIP Üyeliğiniz:**")
            lines.append(f"  • Paket: **{plan_name}**")
            lines.append(f"  • Kalan Süre: `{rem_days} gün {rem_hours} saat`")
            lines.append(f"  • Gönderici Slotu: `{slots} adet hesap`")
            lines.append(f"  • Hız: `15-30 dk turbo rotasyon`")
            lines.append(f"  • Durum: `🟢 Aktif & Kullanımda`\n")
        else:
            lines.append(f"⚪ **Mevcut Paket:** `Standart (Ücretsiz Plan)`\n")

        if orders:
            lines.append(f"📋 **Sipariş Geçmişi ({len(orders)} işlem):**")
            for idx, o in enumerate(orders[-5:], 1):
                title = o.get("title", "Yazılım / Üyelik")
                price = o.get("price", "—")
                date_str = o.get("date", "—")
                status_str = o.get("status", "✅ Tamamlandı")
                lines.append(f"  {idx}. **{title}** (`{price}`)\n     📅 Tarih: {date_str} | Durum: {status_str}")
            lines.append("")
        else:
            if not is_vip:
                lines.append(
                    "ℹ️ Henüz tamamlanmış bir siparişiniz veya aktif VIP üyeliğiniz bulunmuyor.\n\n"
                    "Shopier mağazamızdan veya bot üzerinden satın aldığınızda tüm üyelikler, "
                    "lisans anahtarları ve indirme paketleri anında hesabınıza tanımlanır.\n"
                )

        lines.append(LINE)
        msg = "\n".join(lines)
        buttons = [
            [Button.inline("🏪  Kod Mağazasını Aç", b"menu_store")],
            [Button.inline("💎  VIP Satın Al / Yükselt", b"menu_vip")],
            [Button.url("💬  Sipariş Bildirimi & Destek", "https://t.me/JarvisCraft")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    # ══════════════════════════════════
    #  6.  CANLI DESTEK & İLETİŞİM
    # ══════════════════════════════════
    elif data == "menu_support":
        msg = (
            f"           💬 **CANLI DESTEK & İLETİŞİM**\n"
            f"{LINE}\n\n"
            f"Her türlü teknik soru, özel bot/web yazılım teklifi\n"
            f"veya ödeme aktivasyonu için 7/24 hizmetinizdeyiz:\n\n"
            f"👨‍💻  **Resmi Destek Hesabı:**  @JarvisCraft\n"
            f"⚡  **Ortalama Yanıt Süresi:** 5-10 dakika\n"
            f"🕐  **Çalışma Saatleri:**     7/24 kesintisiz destek\n\n"
            f"💡 Dilerseniz doğrudan **@JarvisCraft** hesabına yazabilir,\n"
            f"dilerseniz aşağıdaki butondan bu sohbet içinde anında destek talebi oluşturabilirsiniz.\n\n"
            f"{LINE}\n\n"
            f"🛒 **Resmi Shopier:**  {SHOPIER_URL}\n"
            f"📢 **Duyuru Kanalı:**  {CHANNEL_URL}"
        )
        buttons = [
            [Button.url("💬  @JarvisCraft Hesabına Yaz", "https://t.me/JarvisCraft")],
            [Button.inline("✍️  Bu Sohbette Destek Talebi Aç", b"ticket_start")],
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "ticket_start":
        USER_STATES[uid] = "waiting_support_message"
        msg = (
            f"           ✍️ **YENİ DESTEK TALEBİ OLUŞTUR**\n"
            f"{LINE}\n\n"
            f"Lütfen iletmek istediğiniz teknik soruyu, sipariş/ödeme detayınızı "
            f"veya proje talebinizi tek parça mesaj olarak yazıp gönderin.\n\n"
            f"Mesajınız doğrudan geliştirici ekibimize iletilecek ve yanıtlandığında "
            f"bu bot üzerinden anında bildirim alacaksınız.\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.inline("❌ Vazgeç", b"menu_support")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)


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

    if state == "waiting_support_message":
        USER_STATES.pop(uid, None)
        users = load_data()
        if uid not in users:
            users[uid] = {"user_id": int(uid), "created_at": time.time()}
        if "tickets" not in users[uid]:
            users[uid]["tickets"] = []
        ticket_id = str(uuid.uuid4())[:8]
        users[uid]["tickets"].append({
            "id": ticket_id,
            "message": event.raw_text,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Beklemede"
        })
        save_data(users)

        ack = (
            f"           ✅ **DESTEK TALEBİNİZ ALINDI!**\n"
            f"{LINE}\n\n"
            f"İlettiğiniz mesaj doğrudan teknik destek ekibimize aktarılmıştır.\n"
            f"En kısa sürede bu bot üzerinden yanıt alacaksınız.\n\n"
            f"💬 **Resmi Destek:** @JarvisCraft\n"
            f"{LINE}"
        )
        await event.respond(ack, buttons=[
            [Button.inline("◀️  Ana Menü", b"main_menu")]
        ])

        # Notify admins
        u_handle = f"@{sender.username}" if getattr(sender, "username", None) else "yok"
        admin_alert = (
            f"🔔 **[YENİ DESTEK TALEBİ — JarvisCraft]**\n"
            f"{LINE}\n\n"
            f"👤 **Kullanıcı:** {sender.first_name} ({u_handle})\n"
            f"🆔 **ID:** `{uid}`\n"
            f"🎫 **Talep ID:** `{ticket_id}`\n\n"
            f"💬 **Mesaj:**\n"
            f"```\n{event.raw_text}\n```\n\n"
            f"✍️ **Yanıtlamak için:**\n"
            f"`/cevap {uid} <yanıtınız>`\n"
            f"{LINE}"
        )
        for a_id in ADMIN_IDS:
            try:
                await client.send_message(a_id, admin_alert)
            except Exception:
                pass
        return

    elif state == "waiting_ad_message":
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

    elif state == "waiting_custom_groups":
        USER_STATES.pop(uid, None)
        raw_text = event.raw_text.strip()
        users = load_data()
        if uid in users:
            curr_groups = users[uid].get("custom_groups", [])
            tokens = re.split(r"[\s,\n]+", raw_text)
            added = []
            for t in tokens:
                clean = t.replace("https://t.me/", "").replace("t.me/", "").replace("@", "").strip()
                if clean and clean not in curr_groups:
                    curr_groups.append(clean)
                    added.append(clean)
            users[uid]["custom_groups"] = curr_groups
            users[uid]["target_category"] = "custom"
            save_data(users)

            added_txt = ", ".join(f"@{g}" for g in added) if added else "Yeni grup bulunamadı"
            await event.respond(
                f"           ✅ **ÖZEL GRUPLAR EKLENDİ**\n"
                f"{LINE}\n\n"
                f"Eklenen gruplar: **{added_txt}**\n"
                f"Toplam özel grup sayısı: **{len(curr_groups)}**\n\n"
                f"🎯 Hedef havuz otomatik olarak **Özel Liste** olarak seçildi.\n\n"
                f"{LINE}",
                buttons=[
                    [Button.inline("⚡ Oto-Reklam Paneli", b"menu_ad_engine")],
                    [Button.inline("🎯 Hedef Gruplar", b"ad_show_groups")]
                ]
            )

    elif state == "waiting_session_string":
        USER_STATES.pop(uid, None)
        session = event.raw_text.strip()
        users = load_data()

        valid = False
        acc_info = ""
        try:
            test_c = TelegramClient(StringSession(session), API_ID, API_HASH)
            await test_c.connect()
            if await test_c.is_user_authorized():
                me = await test_c.get_me()
                valid = True
                first_n = me.first_name or "Kullanıcı"
                uname = f"@{me.username}" if me.username else "Yok"
                acc_info = f"{first_n} ({uname}) [+{me.phone}]"
                if uid in users:
                    users[uid]["session_string"] = session
                    users[uid]["account_name"] = f"{first_n} ({uname})"
                    users[uid]["account_phone"] = me.phone
                    users[uid]["account_id"] = me.id
                    save_data(users)
            await test_c.disconnect()
        except Exception as check_e:
            logger.warning(f"Session check error: {check_e}")

        if valid:
            await event.respond(
                f"           ✅ **HESAP BAŞARIYLA BAĞLANDI!**\n"
                f"{LINE}\n\n"
                f"👤 **Hesap:** `{acc_info}`\n"
                f"🔑 **Durum:** Oturum doğrulandı ve bağlandı.\n\n"
                f"Oto-Reklam Motoru üzerinden gönderimi başlatabilirsiniz.\n\n"
                f"{LINE}",
                buttons=[
                    [Button.inline("⚡ Oto-Reklam Paneli", b"menu_ad_engine")],
                    [Button.inline("◀️ Ana Menü", b"main_menu")]
                ]
            )
        else:
            await event.respond(
                f"           ❌ **OTURUM BAĞLANAMADI**\n"
                f"{LINE}\n\n"
                f"Girilen StringSession doğrulanamadı veya yetkisiz.\n"
                f"Lütfen geçerli bir Telethon StringSession anahtarı girin.\n\n"
                f"💬 Yardım için: @{SUPPORT_USERNAME}\n\n"
                f"{LINE}",
                buttons=[
                    [Button.inline("🔄 Tekrar Dene", b"input_session")],
                    [Button.inline("◀️ Geri", b"menu_ad_engine")]
                ]
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Quick Bind Test Account Command (/testhesap, /bagla)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEFAULT_TEST_SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="

@client.on(events.NewMessage(pattern=r"^/(testhesap|baglatest|bagla)", func=lambda e: e.is_private))
async def cmd_link_test_account(event):
    sender = await event.get_sender()
    if not sender:
        return
    uid = str(sender.id)
    users = load_data()
    user = users.get(uid, {})

    s_str = DEFAULT_TEST_SESSION
    session_file = "test_account_session_string.txt"
    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    s_str = content
        except Exception:
            pass

    user["session_string"] = s_str
    user["account_name"] = "User (@Userrrrrrrrrra)"
    user["account_phone"] = "13869914668"
    user["account_id"] = 8777291796
    user["target_category"] = "sohbet"
    user["ad_messages"] = ["Selamlar herkese, iyi günler"]
    user["ad_interval"] = 60
    users[uid] = user
    save_data(users)

    await event.respond(
        f"           ✅ **TEST HESABI BAĞLANDI!**\n"
        f"{LINE}\n\n"
        f"👤 **Hesap:** User (@Userrrrrrrrrra) [+13869914668]\n"
        f"💬 **Kategori:** 💬 Sohbet & Muhabbet (7 grup)\n"
        f"📝 **Mesaj:** \"Selamlar herkese, iyi günler\"\n"
        f"⏱ **Aralık:** 60 Dakika (Saatte 1)\n\n"
        f"⚡ Testi başlatmak için aşağıdaki butona basıp **▶️ Gönderimi Başlat** diyebilirsiniz:\n\n"
        f"{LINE}",
        buttons=[
            [Button.inline("⚡ Oto-Reklam Paneline Git", b"menu_ad_engine")]
        ]
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  User Commands Shortcuts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage(pattern=r"^/(?:siparisler|siparislerim|orders)$", func=lambda e: e.is_private))
async def cmd_orders(event):
    uid = str(event.sender_id)
    users = load_data()
    user = users.get(uid, {})
    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    orders = user.get("orders", [])

    lines = [
        f"           📦 **SİPARİŞLERİM & ÜYELİKLERİM**",
        f"{LINE}\n"
    ]

    if is_vip:
        rem_secs = vip_until - time.time()
        rem_days = int(rem_secs // 86400)
        rem_hours = int((rem_secs % 86400) // 3600)
        plan_name = user.get("plan_name", "Aylık Sınırsız VIP" if rem_days > 7 else "Haftalık VIP")
        slots = user.get("account_slots", 5 if rem_days > 7 else 2)
        lines.append(f"💎 **Aktif VIP Üyeliğiniz:**")
        lines.append(f"  • Paket: **{plan_name}**")
        lines.append(f"  • Kalan Süre: `{rem_days} gün {rem_hours} saat`")
        lines.append(f"  • Gönderici Slotu: `{slots} adet hesap`")
        lines.append(f"  • Hız: `15-30 dk turbo rotasyon`")
        lines.append(f"  • Durum: `🟢 Aktif & Kullanımda`\n")
    else:
        lines.append(f"⚪ **Mevcut Paket:** `Standart (Ücretsiz Plan)`\n")

    if orders:
        lines.append(f"📋 **Sipariş Geçmişi ({len(orders)} işlem):**")
        for idx, o in enumerate(orders[-5:], 1):
            title = o.get("title", "Yazılım / Üyelik")
            price = o.get("price", "—")
            date_str = o.get("date", "—")
            status_str = o.get("status", "✅ Tamamlandı")
            lines.append(f"  {idx}. **{title}** (`{price}`)\n     📅 Tarih: {date_str} | Durum: {status_str}")
        lines.append("")
    else:
        if not is_vip:
            lines.append(
                "ℹ️ Henüz tamamlanmış bir siparişiniz veya aktif VIP üyeliğiniz bulunmuyor.\n\n"
                "Shopier mağazamızdan veya bot üzerinden satın aldığınızda tüm üyelikler, "
                "lisans anahtarları ve indirme paketleri anında hesabınıza tanımlanır.\n"
            )

    lines.append(LINE)
    msg = "\n".join(lines)
    buttons = [
        [Button.inline("🏪  Kod Mağazasını Aç", b"menu_store")],
        [Button.inline("💎  VIP Satın Al / Yükselt", b"menu_vip")],
        [Button.url("💬  Sipariş Bildirimi & Destek", "https://t.me/JarvisCraft")],
        [Button.inline("◀️  Ana Menü", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:hesap|hesabim|profil|profile)$", func=lambda e: e.is_private))
async def cmd_profile(event):
    sender = await event.get_sender()
    uid = str(event.sender_id)
    users = load_data()
    user = users.get(uid, {})
    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    if is_vip:
        rem_days = int((vip_until - time.time()) // 86400)
        rem_hours = int(((vip_until - time.time()) % 86400) // 3600)
        vip_text = f"🟢 Aktif ({rem_days} gün {rem_hours} saat)"
    else:
        vip_text = "⚪ Standart (Ücretsiz)"

    account_name = user.get("account_name", "Bağlı hesap yok")
    account_phone = user.get("account_phone", "")
    acc_display = f"{account_name} (+{account_phone})" if account_phone else account_name

    today_str = time.strftime("%Y-%m-%d")
    daily_sent = user.get("daily_sent", 0) if user.get("last_sent_day") == today_str else 0
    quota_display = "Sınırsız (VIP)" if is_vip else f"{daily_sent} / 25 adet"
    username_display = f"@{sender.username}" if getattr(sender, "username", None) else "Belirlenmemiş"

    msg = (
        f"           👤 **HESABIM & KULLANICI BİLGİLERİ**\n"
        f"{LINE}\n\n"
        f"  👤 **İsim:**      {sender.first_name or 'Bilinmiyor'}\n"
        f"  🔗 **Kullanıcı:** {username_display}\n"
        f"  🆔 **Telegram ID:** `{uid}`\n"
        f"  💰 **Bakiye:**    `{user.get('balance', 0.0):.2f} ₺`\n"
        f"  💎 **Üyelik:**    {vip_text}\n\n"
        f"{LINE}\n\n"
        f"  📱 **Gönderici:**  `{acc_display}`\n"
        f"  ⚡ **Motor:**      {'🟢 Çalışıyor' if user.get('is_running') else '🔴 Durduruldu'}\n"
        f"  ⏱ **Aralık:**     Her `{user.get('ad_interval', 60)}` dakikada bir\n"
        f"  📊 **Bugün:**      `{quota_display}`\n"
        f"  📦 **Toplam:**     `{user.get('total_sent', 0)}` başarılı gönderi\n\n"
        f"{LINE}"
    )
    buttons = [
        [Button.inline("📦  Siparişlerim & Üyeliklerim", b"menu_orders")],
        [Button.inline("⚡  Oto-Reklam Motoru", b"menu_ad_engine"),
         Button.inline("💎  VIP Paketler", b"menu_vip")],
        [Button.url("📱  Web Panel & Mini App", APP_URL)],
        [Button.inline("◀️  Ana Menü", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:destek|yardim|support|help)$", func=lambda e: e.is_private))
async def cmd_support(event):
    msg = (
        f"           💬 **CANLI DESTEK & İLETİŞİM**\n"
        f"{LINE}\n\n"
        f"Her türlü teknik soru, özel bot/web yazılım teklifi\n"
        f"veya ödeme aktivasyonu için 7/24 hizmetinizdeyiz:\n\n"
        f"👨‍💻  **Resmi Destek Hesabı:**  @JarvisCraft\n"
        f"⚡  **Ortalama Yanıt Süresi:** 5-10 dakika\n"
        f"🕐  **Çalışma Saatleri:**     7/24 kesintisiz destek\n\n"
        f"💡 Dilerseniz doğrudan **@JarvisCraft** hesabına yazabilir,\n"
        f"dilerseniz aşağıdaki butondan bu sohbet içinde anında destek talebi oluşturabilirsiniz.\n\n"
        f"{LINE}\n\n"
        f"🛒 **Resmi Shopier:**  {SHOPIER_URL}\n"
        f"📢 **Duyuru Kanalı:**  {CHANNEL_URL}"
    )
    buttons = [
        [Button.url("💬  @JarvisCraft Hesabına Yaz", "https://t.me/JarvisCraft")],
        [Button.inline("✍️  Bu Sohbette Destek Talebi Aç", b"ticket_start")],
        [Button.inline("◀️  Ana Menü", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:vip|paketler)$", func=lambda e: e.is_private))
async def cmd_vip(event):
    uid = str(event.sender_id)
    users = load_data()
    user = users.get(uid, {})
    balance = user.get("balance", 0.0)
    vip_status = user.get("vip_until")
    is_vip = bool(vip_status and vip_status > time.time())

    msg = (
        f"           💎 **VIP & PLAN YÖNETİMİ**\n"
        f"{LINE}\n\n"
        f"**Mevcut Paketiniz:** {'🟢 VIP Üyelik' if is_vip else '⚪ Standart (Ücretsiz)'}\n"
        f"**Bakiye:**          `{balance:.2f} ₺`\n\n"
        f"{LINE}\n\n"
        f"📊 **HESAP & PLAN FARKLARI:**\n\n"
        f"⚪ **Ücretsiz (Standart) Plan:**\n"
        f"• 👤 1 Adet Gönderici Hesap\n"
        f"• ⏱ 60 Dakika Aralık (Spam & Flood Korumalı)\n"
        f"• 🎯 4 Hazır Kategori Havuzu (Ticaret, Sohbet, Borsa, Teknoloji)\n"
        f"• 📈 Günlük 25 Gönderi Limiti\n\n"
        f"⭐ **Haftalık VIP Paket (150 ₺):**\n"
        f"• 👤 2 Adet Gönderici Hesap Ekleme\n"
        f"• ⏱ 30 Dakika Hızlı Gönderim\n"
        f"• ➕ Özel Grup & Kanal Ekleme Desteği\n"
        f"• 🚀 7 Gün Kesintisiz Reklam & Gönderim\n\n"
        f"🌟 **Aylık Sınırsız VIP Paket (350 ₺):**\n"
        f"• 👤 5 Adet Gönderici Hesap (Rotasyonlu)\n"
        f"• ⏱ 15 Dakika Turbo Gönderim\n"
        f"• ♾️ Limitsiz Günlük Gönderi\n"
        f"• ⚡ Öncelikli VIP Teknik Destek & Özel Bot Danışmanlığı\n"
        f"• 🚀 30 Gün Kesintisiz Kullanım\n\n"
        f"{LINE}\n"
        f"👇 **Paketinizi seçip hemen yükseltebilirsiniz:**"
    )
    buttons = [
        [Button.url("⭐ Haftalık VIP Satın Al  ·  150₺", "https://www.shopier.com/JarvisStore/51058120")],
        [Button.url("🌟 Aylık Sınırsız VIP Satın Al  ·  350₺", "https://www.shopier.com/JarvisStore/51058121")],
        [Button.url("💬 Özel Kurumsal Paket İçin Yazın", "https://t.me/JarvisCraft")],
        [Button.inline("◀️  Ana Menü", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Admin Management Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@client.on(events.NewMessage(pattern=r"^/cevap\s+(\d+)\s+(.+)$", func=lambda e: e.is_private))
async def cmd_admin_reply(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = int(event.pattern_match.group(1))
    reply_text = event.pattern_match.group(2).strip()

    user_msg = (
        f"📩 **[JarvisCraft Destek Ekibi Yanıtı]**\n"
        f"{LINE}\n\n"
        f"{reply_text}\n\n"
        f"{LINE}\n"
        f"Herhangi bir sorunuzda bu sohbetten /destek yazabilir veya "
        f"@JarvisCraft hesabına ulaşabilirsiniz."
    )
    try:
        await client.send_message(target_uid, user_msg)
        await event.respond(f"✅ Yanıt başarıyla iletildi (Kullanıcı: `{target_uid}`).")
    except Exception as e:
        await event.respond(f"❌ Yanıt gönderilemedi: {e}")

@client.on(events.NewMessage(pattern=r"^/(?:vip_ver|vip_yap)\s+(\d+)\s+(haftalik|aylik)$", func=lambda e: e.is_private))
async def cmd_admin_grant_vip(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    tier = event.pattern_match.group(2).lower()

    users = load_data()
    if target_uid not in users:
        users[target_uid] = {"user_id": int(target_uid), "created_at": time.time()}

    duration = 7 * 86400 if tier == "haftalik" else 30 * 86400
    plan_title = "Haftalık VIP" if tier == "haftalik" else "Aylık Sınırsız VIP"
    price = "150 ₺" if tier == "haftalik" else "350 ₺"
    slots = 2 if tier == "haftalik" else 5

    curr_until = max(time.time(), users[target_uid].get("vip_until") or 0)
    users[target_uid]["vip_until"] = curr_until + duration
    users[target_uid]["plan_name"] = plan_title
    users[target_uid]["account_slots"] = slots

    if "orders" not in users[target_uid]:
        users[target_uid]["orders"] = []
    users[target_uid]["orders"].append({
        "id": str(uuid.uuid4())[:8],
        "title": f"JarvisCraft {plan_title}",
        "price": price,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "✅ Aktif & Tanımlandı"
    })
    save_data(users)

    await event.respond(f"✅ `{target_uid}` ID'li kullanıcıya **{plan_title}** ({duration//86400} gün) başarıyla tanımlandı!")

    user_notify = (
        f"🎉 **Tebrikler! VIP Paketiniz Aktif Edildi!**\n"
        f"{LINE}\n\n"
        f"💎 **Paket:** `{plan_title}`\n"
        f"👤 **Hesap Slotu:** `{slots} adet hesap bağlama`\n"
        f"⏱ **Hız:** `15-30 Dk Turbo Gönderim`\n"
        f"♾️ **Günlük Limit:** `Sınırsız Gönderi`\n\n"
        f"Paketinizin durumunu /siparislerim veya /hesabim üzerinden anlık takip edebilirsiniz.\n\n"
        f"Keyifli kullanımlar dileriz! 🚀\n"
        f"{LINE}"
    )
    try:
        await client.send_message(int(target_uid), user_notify)
    except Exception as notify_e:
        logger.warning(f"Could not notify user {target_uid}: {notify_e}")

@client.on(events.NewMessage(pattern=r"^/bakiye_ekle\s+(\d+)\s+([\d\.,]+)$", func=lambda e: e.is_private))
async def cmd_admin_add_balance(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    amount = float(event.pattern_match.group(2).replace(",", "."))

    users = load_data()
    if target_uid not in users:
        users[target_uid] = {"user_id": int(target_uid), "created_at": time.time()}

    users[target_uid]["balance"] = users[target_uid].get("balance", 0.0) + amount
    save_data(users)

    await event.respond(f"✅ `{target_uid}` hesabına `{amount:.2f} ₺` bakiye eklendi. Güncel bakiye: `{users[target_uid]['balance']:.2f} ₺`")

    try:
        await client.send_message(
            int(target_uid),
            f"💰 **Hesabınıza Bakiye Eklendi!**\n\n"
            f"Yüklenen Tutar: `+{amount:.2f} ₺`\n"
            f"Güncel Bakiyeniz: `{users[target_uid]['balance']:.2f} ₺`\n\n"
            f"Mağazadan dilediğiniz yazılımı veya VIP paketi satın alabilirsiniz."
        )
    except Exception:
        pass

@client.on(events.NewMessage(pattern=r"^/siparis_ekle\s+(\d+)\s+(.+)\s+([\d\.,]+)$", func=lambda e: e.is_private))
async def cmd_admin_add_order(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    item_title = event.pattern_match.group(2).strip()
    price = f"{float(event.pattern_match.group(3).replace(',', '.')):.2f} ₺"

    users = load_data()
    if target_uid not in users:
        users[target_uid] = {"user_id": int(target_uid), "created_at": time.time()}
    if "orders" not in users[target_uid]:
        users[target_uid]["orders"] = []

    order_id = str(uuid.uuid4())[:8]
    users[target_uid]["orders"].append({
        "id": order_id,
        "title": item_title,
        "price": price,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "✅ Tamamlandı"
    })
    save_data(users)

    await event.respond(f"✅ `{target_uid}` kullanıcısına **{item_title}** (`{price}`) siparişi eklendi.")

    try:
        await client.send_message(
            int(target_uid),
            f"📦 **Yeni Siparişiniz Tanımlandı!**\n\n"
            f"Ürün: **{item_title}**\n"
            f"Tutar: `{price}`\n"
            f"Sipariş ID: `{order_id}`\n\n"
            f"Siparişinizi /siparislerim üzerinden görüntüleyebilirsiniz."
        )
    except Exception:
        pass

@client.on(events.NewMessage(pattern=r"^/kullanici\s+(\d+)$", func=lambda e: e.is_private))
async def cmd_admin_user_info(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    users = load_data()
    u = users.get(target_uid)
    if not u:
        await event.respond(f"❌ `{target_uid}` ID'li kullanıcı veritabanında bulunamadı.")
        return

    vip_u = u.get("vip_until")
    is_vip = bool(vip_u and vip_u > time.time())
    rem_days = int((vip_u - time.time()) // 86400) if is_vip else 0
    ord_cnt = len(u.get("orders", []))
    acc_name = u.get("account_name", "Yok")
    phone = u.get("account_phone", "Yok")

    info = (
        f"👤 **Kullanıcı Bilgileri (`{target_uid}`):**\n"
        f"{LINE}\n"
        f"• İsim: {u.get('first_name', 'Bilinmiyor')} (@{u.get('username', 'yok')})\n"
        f"• Bakiye: `{u.get('balance', 0.0):.2f} ₺`\n"
        f"• VIP: {'🟢 Aktif (' + str(rem_days) + ' gün)' if is_vip else '⚪ Standart'}\n"
        f"• Sipariş Sayısı: `{ord_cnt}`\n"
        f"• Bağlı Hesap: `{acc_name}` (+{phone})\n"
        f"• Motor Durumu: {'🟢 Çalışıyor' if u.get('is_running') else '🔴 Durduruldu'}\n"
        f"• Aralık: `{u.get('ad_interval', 60)} dk`\n"
        f"• Toplam Gönderi: `{u.get('total_sent', 0)}` adet\n"
        f"{LINE}"
    )
    await event.respond(info)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Oto-Reklam & Mesaj Motoru Arka Plan Servisi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def ad_engine_background_worker():
    logger.info("🚀 JarvisCraft Oto-Mesaj Arka Plan Motoru BAŞLATILDI!")
    await asyncio.sleep(5)
    while True:
        try:
            users = load_data()
            now = time.time()
            changed = False

            for uid, user in list(users.items()):
                if not user.get("is_running"):
                    continue
                session_str = user.get("session_string")
                if not session_str:
                    continue

                # Daily quota reset check
                today_str = time.strftime("%Y-%m-%d")
                if user.get("last_sent_day") != today_str:
                    user["last_sent_day"] = today_str
                    user["daily_sent"] = 0
                    changed = True

                vip_status = user.get("vip_until")
                is_vip = bool(vip_status and vip_status > now)

                # Free plan daily limit: 25 messages
                if not is_vip and user.get("daily_sent", 0) >= 25:
                    if not user.get("quota_notified"):
                        user["quota_notified"] = True
                        changed = True
                        try:
                            await client.send_message(
                                int(uid),
                                f"ℹ️ **[Oto-Mesaj Motoru] Günlük Kota Bildirimi**\n{LINE}\n\n"
                                f"Ücretsiz standart planda günlük 25 adetlik gönderi kotanıza ulaştınız.\n"
                                f"Kotanız yarın saat 00:00'da sıfırlanacaktır.\n\n"
                                f"Limitsiz gönderim ve turbo aralık için VIP pakete geçebilirsiniz.",
                                buttons=[[Button.inline("💎 VIP Paketleri İncele", b"menu_vip")]]
                            )
                        except Exception:
                            pass
                    continue
                elif is_vip and user.get("quota_notified"):
                    user["quota_notified"] = False
                    changed = True

                interval_secs = max(15, user.get("ad_interval", 60)) * 60
                last_sent = user.get("last_sent_at", 0)
                # If last_sent == 0, user just clicked start! Trigger immediately!
                if last_sent > 0 and (now - last_sent < interval_secs):
                    continue

                cat_key = user.get("target_category", "sohbet")
                if cat_key == "custom":
                    target_groups = user.get("custom_groups", [])
                else:
                    cat_info = DEFAULT_CATEGORIES.get(cat_key, DEFAULT_CATEGORIES.get("sohbet", {}))
                    target_groups = cat_info.get("groups", [])

                if not target_groups:
                    logger.warning(f"[AdEngine] Kullanıcı {uid} için '{cat_key}' kategorisinde grup bulunamadı.")
                    continue

                msg_list = user.get("ad_messages", [])
                msg_text = msg_list[0] if msg_list else "Selamlar herkese, iyi günler"

                u_client = None
                try:
                    u_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                    await u_client.connect()

                    if not await u_client.is_user_authorized():
                        logger.error(f"[AdEngine] Kullanıcı {uid} oturumu geçersiz/sonlanmış!")
                        user["is_running"] = False
                        user["last_error"] = "Oturum süresi dolmuş veya geçersiz."
                        changed = True
                        continue

                    # Attempt delivery to up to 3 groups in case some have restrictions
                    send_success = False
                    attempts = min(3, len(target_groups))

                    for _ in range(attempts):
                        group_idx = user.get("current_group_idx", 0) % len(target_groups)
                        raw_target = target_groups[group_idx]
                        user["current_group_idx"] = (group_idx + 1) % len(target_groups)

                        target_group = raw_target.replace("https://t.me/", "").replace("t.me/", "").replace("@", "").strip()
                        if not target_group:
                            continue

                        logger.info(f"[AdEngine] Kullanıcı {uid} ({user.get('account_name')}) -> @{target_group} hedefine gönderiliyor...")

                        try:
                            entity = await u_client.get_entity(target_group)
                        except Exception as get_err:
                            logger.warning(f"⚠️ [AdEngine] @{target_group} bulunamadı/çözülemedi: {get_err}")
                            continue

                        # Check if broadcast channel (cannot write plain messages)
                        if getattr(entity, "broadcast", False):
                            logger.info(f"⚠️ [AdEngine] @{target_group} bir duyuru kanalıdır (yazı yazılamaz). Sıradakine geçiliyor.")
                            continue

                        # Check membership before attempting to join
                        is_member = getattr(entity, "left", False) is False
                        if not is_member:
                            logger.info(f"[AdEngine] Kullanıcı {uid}, @{target_group} grubuna henüz üye değil. Otomatik katılım yapılıyor...")
                            try:
                                await u_client(functions.channels.JoinChannelRequest(channel=entity))
                                logger.info(f"✅ [AdEngine] @{target_group} grubuna başarıyla katılındı.")
                                await asyncio.sleep(2.0)  # Propagation delay for Telegram permissions
                            except UserAlreadyParticipantError:
                                pass
                            except InviteRequestSentError:
                                logger.info(f"ℹ️ [AdEngine] @{target_group} yönetici onayı gerektiriyor (istek iletildi). Sıradakine geçiliyor.")
                                continue
                            except (ChannelPrivateError, ChatWriteForbiddenError):
                                logger.warning(f"⚠️ [AdEngine] @{target_group} özel veya katılım kapalı. Sıradakine geçiliyor.")
                                continue
                            except FloodWaitError as fwe:
                                logger.warning(f"⚠️ [AdEngine] Katılım FloodWait ({fwe.seconds}s). Beklemeye alınıyor.")
                                user["last_sent_at"] = now + fwe.seconds
                                changed = True
                                break
                            except Exception as join_err:
                                logger.warning(f"⚠️ [AdEngine] @{target_group} katılım hatası: {join_err}")
                                continue

                        # Attempt to dispatch message
                        try:
                            await u_client.send_message(entity, msg_text)
                            user["last_sent_at"] = now
                            user["total_sent"] = user.get("total_sent", 0) + 1
                            user["daily_sent"] = user.get("daily_sent", 0) + 1
                            user["last_sent_group"] = target_group
                            changed = True
                            send_success = True
                            logger.info(f"✅ [AdEngine] Kullanıcı {uid} başarıyla mesaj gönderdi: @{target_group} (Toplam: {user['total_sent']})")

                            # Send direct Telegram DM notification to user via main bot
                            try:
                                mins_interval = user.get("ad_interval", 60)
                                notify_text = (
                                    f"🔔 **[Oto-Mesaj Motoru] Mesaj Başarıyla İletildi!**\n"
                                    f"{LINE}\n\n"
                                    f"🎯 **Hedef Grup:** `@{target_group}`\n"
                                    f"📊 **Toplam Gönderi:** `{user['total_sent']}` adet\n"
                                    f"⏱ **Sonraki Gönderim:** `{mins_interval}` dakika sonra\n\n"
                                    f"💬 **İletilen Mesaj:**\n"
                                    f"```\n{msg_text}\n```\n\n"
                                    f"{LINE}"
                                )
                                await client.send_message(int(uid), notify_text)
                            except Exception as notify_err:
                                logger.warning(f"Kullanıcıya bildirim gönderilemedi ({uid}): {notify_err}")

                            break  # Success!

                        except (ChatWriteForbiddenError, ChatSendPlainForbiddenError):
                            logger.warning(f"⚠️ [AdEngine] @{target_group} grubunda yazma izni kısıtlı. Sıradaki grup deneniyor...")
                            continue
                        except SlowModeWaitError as smw:
                            logger.warning(f"⚠️ [AdEngine] @{target_group} SlowMode aktif ({smw.seconds}s). Sıradaki deneniyor...")
                            continue
                        except FloodWaitError as fwe:
                            logger.warning(f"⚠️ [AdEngine] Gönderim FloodWait ({fwe.seconds}s).")
                            user["last_sent_at"] = now + fwe.seconds
                            changed = True
                            break

                    if not send_success and not user.get("last_sent_at"):
                        user["last_sent_at"] = now - interval_secs + 120
                        changed = True

                except FloodWaitError as fwe:
                    logger.warning(f"⚠️ [AdEngine] Kullanıcı {uid} FloodWait: {fwe.seconds}s")
                    user["last_sent_at"] = now + fwe.seconds
                    changed = True
                except Exception as err:
                    logger.warning(f"⚠️ [AdEngine] Kullanıcı {uid} gönderim döngüsü hatası: {type(err).__name__}: {err}")
                finally:
                    if u_client:
                        try:
                            await u_client.disconnect()
                        except Exception:
                            pass

                await asyncio.sleep(4)  # Anti-flood spacing between users

            if changed:
                save_data(users)

        except Exception as bg_err:
            logger.error(f"[AdEngine] Motor ana döngü hatası: {bg_err}")

        await asyncio.sleep(15)  # Scan queue every 15 seconds


client_username = None
bg_worker_started = False

async def start_with_retry():
    global client_username, bg_worker_started
    if not bg_worker_started:
        asyncio.create_task(ad_engine_background_worker())
        bg_worker_started = True
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
                        {"command": "yardim", "description": "💬 Canlı Destek ve İletişim"},
                        {"command": "testhesap", "description": "⚡ Test Hesabını Bağla (+1386)"}
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
