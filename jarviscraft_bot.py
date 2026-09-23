# -*- coding: utf-8 -*-
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
import urllib.parse
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
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

# --- Brand & Links ---
CHANNEL_USERNAME = "JarvisCraftDuyuru"
CHANNEL_URL = "https://t.me/JarvisCraftDuyuru"
SUPPORT_USERNAME = "JarvisCraft"
SUPPORT_URL = "https://t.me/JarvisCraft"
SHOPIER_URL = "https://www.shopier.com/JarvisStore"
APP_URL = "https://bot-service-production-9d74.up.railway.app/jarvis/app"
SHOPIER_TOKEN = os.environ.get("SHOPIER_JARVIS_ACCESS_TOKEN", "").strip()

ADMIN_IDS = {
    int(os.environ.get("TELEGRAM_ADMIN_ID", 8791896048)),
    8791896048, 6196006704, 8116518175, 8387947754
}
DEFAULT_TEST_SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="

LINE = "----------------------------------------"
DOT = "*"

# --- Hedef Kategori Havuzlari ---
DEFAULT_CATEGORIES = {
    "ticaret": {
        "title": "Ticaret & Alim-Satim",
        "description": "65+ onayli ticaret, kupon, bakiye ve alisveris grubu",
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
        "title": "Sohbet & Topluluk",
        "description": "Aktif, temiz baslikli Turk sohbet ve arkadaslik topluluklari",
        "groups": [
            "TurkceSohbetler", "CoinSohbetTR", "KriptoTurkiye", "sohbetmuhabbettr"
        ]
    },
    "borsa": {
        "title": "Borsa & Kripto Finans",
        "description": "Binlerce uyeli aktif borsa, kripto ve finans tartisma gruplari",
        "groups": [
            "KriptoTurkiye", "CoinSohbetTR", "bitgetturkiye", "KriptoSozlukTVPiyasaMuhabbeti"
        ]
    },
    "haber": {
        "title": "Teknoloji & Yazilim",
        "description": "Gelistirici, teknoloji ve yazilim tartisma topluluklari",
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

USER_STATES = {}

async def is_user_subscribed(user_id):
    """Checks if the user has joined the official announcement channel via Telegram Bot API."""
    return True

def get_main_menu():
    return [
        [Button.url("Shopier Magazasi (Tum Ilanlar)", SHOPIER_URL)],
        [Button.inline("Oto-Reklam Motoru", b"menu_ad_engine"),
         Button.inline("Kod & Yazilim Magazasi", b"menu_store")],
        [Button.inline("Siparislerim & Uyeliklerim", b"menu_orders"),
         Button.inline("VIP & Bakiye", b"menu_vip")],
        [Button.inline("Hesabim & Profil", b"menu_profile"),
         Button.url("Web Panel", APP_URL)],
        [Button.url("Duyuru Kanali", CHANNEL_URL),
         Button.inline("Canli Destek", b"menu_support")]
    ]

def get_gatekeeper_menu():
    return [
        [Button.url("Duyuru Kanalina Katil (@JarvisCraftDuyuru)", CHANNEL_URL)],
        [Button.inline("[+] Katildim, Dogrula", b"verify_join")]
    ]

async def render_ad_engine(event, user):
    is_active = user.get("is_running", False)
    status = "[AKTIF] - Gonderim yapiliyor" if is_active else "[DURDURULDU]"
    interval = user.get('ad_interval', 60)
    msg_count = len(user.get('ad_messages', []))
    current_msg = user.get('ad_messages', ['-'])[0] if msg_count > 0 else "-"
    preview = current_msg[:70] + "..." if len(current_msg) > 70 else current_msg

    cat_key = user.get("target_category", "sohbet")
    if cat_key == "custom":
        cnt = len(user.get("custom_groups", []))
        cat_title = f"Ozel Liste ({cnt} grup)"
    else:
        info = DEFAULT_CATEGORIES.get(cat_key, DEFAULT_CATEGORIES.get("sohbet", {}))
        cat_title = f"{info['title']} ({len(info.get('groups', []))} grup)"

    account_name = user.get("account_name")
    has_session = bool(user.get("session_string"))
    if account_name:
        account_status = f"[Bagli] {account_name}"
    elif has_session:
        account_status = "[Bagli] Session Kayitli"
    else:
        account_status = "[X] Bagli Hesap Yok"

    total_sent = user.get("total_sent", 0)
    last_group = user.get("last_sent_group", "Henuz yok")
    last_group_display = f"@{last_group}" if last_group != "Henuz yok" else "Henuz yok"

    msg = (
        f"           **OTO-REKLAM & MESAJ MOTORU**\n"
        f"{LINE}\n\n"
        f"**Durum:**        {status}\n"
        f"**Gonderici:**     `{account_status}`\n"
        f"**Aralik:**        Her `{interval}` dakikada bir\n"
        f"**Hedef Havuz:**   **{cat_title}**\n"
        f"**Toplam Gonderi:** `{total_sent}` adet\n"
        f"**Son Hedef:**     `{last_group_display}`\n\n"
        f"**Aktif Reklam Metni:**\n"
        f"```\n{preview}\n```\n\n"
        f"{LINE}"
    )

    toggle = (
        Button.inline("[Durdur] Gonderimi Durdur", b"ad_stop")
        if is_active else
        Button.inline("[Baslat] Gonderimi Baslat", b"ad_start")
    )

    buttons = [
        [toggle],
        [Button.inline("Metni Duzenle", b"ad_edit_msg"),
         Button.inline("Sure Ayarla", b"ad_set_interval")],
        [Button.inline("Hedef Kategori & Havuz", b"ad_show_groups"),
         Button.inline("Ozel Grup Ekle", b"ad_add_custom_group")]
    ]
    if not has_session:
        buttons.append([Button.inline("Hizli Test Hesabi Bagla (+1386)", b"bind_test_account")])
        buttons.append([Button.inline("Kendi Hesabimi Bagla (Session)", b"input_session")])
    else:
        buttons.append([Button.inline("Gonderici Hesap Yonetimi", b"ad_add_account")])
    buttons.append([Button.inline("<-- Ana Menu", b"main_menu")])

    await safe_edit_event(event, msg, buttons=buttons)

async def render_categories_menu(event, user):
    curr_cat = user.get("target_category", "sohbet")
    custom_cnt = len(user.get("custom_groups", []))
    
    t_chk = " [Secili]" if curr_cat == "ticaret" else ""
    s_chk = " [Secili]" if curr_cat == "sohbet" else ""
    b_chk = " [Secili]" if curr_cat == "borsa" else ""
    h_chk = " [Secili]" if curr_cat == "haber" else ""
    c_chk = " [Secili]" if curr_cat == "custom" else ""

    ticaret_cnt = len(DEFAULT_CATEGORIES["ticaret"]["groups"])
    sohbet_cnt = len(DEFAULT_CATEGORIES["sohbet"]["groups"])
    borsa_cnt = len(DEFAULT_CATEGORIES["borsa"]["groups"])
    haber_cnt = len(DEFAULT_CATEGORIES["haber"]["groups"])

    custom_preview = ""
    if custom_cnt > 0:
        c_sample = user.get("custom_groups", [])[:3]
        custom_preview = " (" + ", ".join(f"@{g}" for g in c_sample) + "...)"

    msg = (
        f"           **HEDEF KATEGORI & GRUP SECIMI**\n"
        f"{LINE}\n\n"
        f"Mesajlarinizin otomatik gonderilecegi kategoriyi secin\n"
        f"veya kendi istediginiz grup/kanallari ekleyin:\n\n"
        f"• **Ticaret & Alim-Satim:** {ticaret_cnt}+ aktif ticaret grubu\n"
        f"• **Sohbet & Topluluk:** {sohbet_cnt} aktif Turk sohbet grubu\n"
        f"• **Borsa & Kripto:** {borsa_cnt} finans & coin tartisma grubu\n"
        f"• **Teknoloji & Yazilim:** {haber_cnt} yazilim & gelistirici grubu\n"
        f"• **Ozel Liste:** Kendi eklediginiz {custom_cnt} grup{custom_preview}\n\n"
        f"{LINE}\n"
        f"Kategori secin veya ozel grup ekleyin:"
    )

    buttons = [
        [Button.inline(f"Ticaret ({ticaret_cnt}+){t_chk}", b"setcat_ticaret"),
         Button.inline(f"Sohbet ({sohbet_cnt}){s_chk}", b"setcat_sohbet")],
        [Button.inline(f"Borsa & Kripto ({borsa_cnt}){b_chk}", b"setcat_borsa"),
         Button.inline(f"Teknoloji ({haber_cnt}){h_chk}", b"setcat_haber")],
        [Button.inline(f"Kendi Ozel Listem ({custom_cnt}){c_chk}", b"setcat_custom")],
        [Button.inline("[+] Ozel Grup Ekle", b"ad_add_custom_group"),
         Button.inline("[-] Ozel Listeyi Temizle", b"ad_clear_custom")],
        [Button.inline("<-- Geri (Motor Paneli)", b"menu_ad_engine")]
    ]
    await safe_edit_event(event, msg, buttons=buttons)

# -------------------------------------------------------------
# /start - Welcome Screen with Channel Gatekeeper
# -------------------------------------------------------------
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
            "ad_messages": ["JarvisCraft ile otomatik reklam gonderimi aktif."],
            "ad_interval": 60,
            "is_running": False
        }
        save_data(users)

    is_subbed = await is_user_subscribed(sender.id)
    if not is_subbed:
        gate_msg = (
            f"          **JARVISCRAFT SISTEMINE HOS GELDINIZ**\n"
            f"{LINE}\n\n"
            f"Merhaba **{sender.first_name or 'Degerli Kullanici'}**,\n\n"
            f"JarvisCraft bot ve yazilim ekosistemini kullanabilmek icin\n"
            f"resmi **Duyuru & Guncelleme Kanalimiza** katilmaniz gerekmektedir.\n\n"
            f"**Kanalimizda Neler Var?**\n"
            f"• Satisa sunulan bot ve scriptlerin tanitimlari\n"
            f"• Acik kaynak Python kodlari ve hazir kutuphaneler\n"
            f"• Ozel indirimler ve sistem guncellemeleri\n\n"
            f"{LINE}\n"
            f"Asagidaki butondan kanala katilin ve ardindan Dogrula'ya tiklayin:"
        )
        await event.respond(gate_msg, buttons=get_gatekeeper_menu())
        return

    name = sender.first_name or "Kullanici"
    welcome = (
        f"                **JARVISCRAFT**\n"
        f"{LINE}\n\n"
        f"Hos geldiniz, **{name}**.\n\n"
        f"JarvisCraft, Telegram'in gelismis\n"
        f"**yazilim, otomasyon ve bot ekosistemidir.**\n\n"
        f"• **Oto-Reklam Motoru** - 65+ gruba kesintisiz mesaj ve rotasyon\n"
        f"• **Kod & Yazilim Magazasi** - Hazir bot, script paketleri ve ozel projeler\n"
        f"• **AI Araclari** - Sesli masaustu asistani ve uretkenlik araclari\n"
        f"• **VIP Sistem** - Coklu oturum, anti-ban ve sinirsiz gonderim\n\n"
        f"{LINE}\n"
        f"Islem yapmak istediginiz bolumu secin:"
    )
    await event.respond(welcome, buttons=get_main_menu())

# -------------------------------------------------------------
# Callback Router
# -------------------------------------------------------------
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    sender = await event.get_sender()
    if not sender:
        return
    uid = str(sender.id)
    users = load_data()
    user = users.get(uid, {})

    if data == "verify_join":
        is_subbed = await is_user_subscribed(sender.id)
        if is_subbed:
            await event.answer("Dogrulama basarili. JarvisCraft'a hos geldiniz.", alert=True)
            name = sender.first_name or "Kullanici"
            welcome = (
                f"                **JARVISCRAFT**\n"
                f"{LINE}\n\n"
                f"Hos geldiniz, **{name}**.\n\n"
                f"JarvisCraft, Telegram'in gelismis\n"
                f"**yazilim, otomasyon ve bot ekosistemidir.**\n\n"
                f"• **Oto-Reklam Motoru** - 65+ gruba kesintisiz mesaj ve rotasyon\n"
                f"• **Kod & Yazilim Magazasi** - Hazir bot, script paketleri ve ozel projeler\n"
                f"• **AI Araclari** - Sesli masaustu asistani ve uretkenlik araclari\n"
                f"• **VIP Sistem** - Coklu oturum, anti-ban ve sinirsiz gonderim\n\n"
                f"{LINE}\n"
                f"Islem yapmak istediginiz bolumu secin:"
            )
            await safe_edit_event(event, welcome, buttons=get_main_menu())
        else:
            await event.answer("Kanala katilim tespit edilemedi. Lutfen @JarvisCraftDuyuru kanalina katilip tekrar deneyin.", alert=True)

    elif data == "main_menu":
        USER_STATES.pop(uid, None)
        name = sender.first_name or "Kullanici"
        welcome = (
            f"                **JARVISCRAFT**\n"
            f"{LINE}\n\n"
            f"Hos geldiniz, **{name}**.\n\n"
            f"JarvisCraft, Telegram'in gelismis\n"
            f"**yazilim, otomasyon ve bot ekosistemidir.**\n\n"
            f"• **Oto-Reklam Motoru** - 65+ gruba kesintisiz mesaj ve rotasyon\n"
            f"• **Kod & Yazilim Magazasi** - Hazir bot, script paketleri ve ozel projeler\n"
            f"• **AI Araclari** - Sesli masaustu asistani ve uretkenlik araclari\n"
            f"• **VIP Sistem** - Coklu oturum, anti-ban ve sinirsiz gonderim\n\n"
            f"{LINE}\n"
            f"Islem yapmak istediginiz bolumu secin:"
        )
        await safe_edit_event(event, welcome, buttons=get_main_menu())

    # 1. OTO-REKLAM MOTORU
    elif data == "menu_ad_engine":
        await render_ad_engine(event, user)

    elif data == "ad_start":
        if not user.get("session_string"):
            await event.answer("Gonderim yapabilmek icin once gonderici Telegram hesabi baglamalisiniz.", alert=True)
            return
        user["is_running"] = True
        user["last_sent_at"] = 0
        users[uid] = user
        save_data(users)
        await event.answer("Oto-Reklam motoru baslatildi. Mesajlariniz sirayla iletilecektir.", alert=False)
        await render_ad_engine(event, user)

    elif data == "ad_stop":
        user["is_running"] = False
        users[uid] = user
        save_data(users)
        await event.answer("Oto-Reklam motoru durduruldu.", alert=False)
        await render_ad_engine(event, user)

    elif data == "ad_edit_msg":
        USER_STATES[uid] = "waiting_ad_message"
        await safe_edit_event(
            event,
            f"           **REKLAM METNINI DUZENLE**\n"
            f"{LINE}\n\n"
            f"Gruplara otomatik gonderilmesini istediginiz reklam metnini\n"
            f"bu sohbete mesaj olarak yazip gonderin.\n\n"
            f"Not: Metniniz kaydedildikten sonra gonderim baslatildiginda\n"
            f"tum hedef gruplara bu icerik iletilecektir.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("Vazgec", b"menu_ad_engine")]]
        )

    elif data == "ad_set_interval":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        status_note = "[VIP Aktif: Hizli modlar acik]" if is_vip else "[Ucretsiz Plan: 60 dk standart varsayilandir (30-45 dk icin VIP pakete gecebilirsiniz)]"
        buttons = [
            [Button.inline("30 dk (VIP Hizli Mod)", b"interval_30"),
             Button.inline("45 dk (VIP Dengeli)", b"interval_45")],
            [Button.inline("60 dk (Onerilen Standart)", b"interval_60"),
             Button.inline("90 dk (Ekstra Guvenli)", b"interval_90")],
            [Button.inline("VIP Paketlerini Incele", b"menu_vip")],
            [Button.inline("<-- Geri", b"menu_ad_engine")]
        ]
        await safe_edit_event(
            event,
            f"           **GONDERIM ARALIGI SECIMI**\n"
            f"{LINE}\n\n"
            f"Mesajlar arasindaki bekleme suresini secin:\n\n"
            f"• **60 dk (Onerilen Standart):** Telegram hesap sagligi ve flood korumasi icin ideal standart periyot.\n"
            f"• **30 - 45 dk (VIP Hizli Mod):** Coklu hesap rotasyonuyla hesaplarinizi yormadan 2 kat daha sik gorunurluk saglar.\n"
            f"• **90 dk (Ekstra Guvenli):** Yeni veya hassas hesaplar icin sifir riskli gonderim.\n\n"
            f"Durum: {status_note}\n\n"
            f"{LINE}",
            buttons=buttons
        )

    elif data.startswith("interval_"):
        mins = int(data.split("_")[1])
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        if mins < 60 and not is_vip:
            await event.answer(f"{mins} dakikalik hizli gonderim VIP uyelere ozeldir. Ucretsiz planda 60 dk aktiftir.", alert=True)
            user["ad_interval"] = 60
            users[uid] = user
            save_data(users)
        else:
            user["ad_interval"] = mins
            users[uid] = user
            save_data(users)
            await event.answer(f"Gonderim araligi {mins} dakika olarak ayarlandi.", alert=True)
        await render_ad_engine(event, user)

    elif data == "ad_show_groups":
        await render_categories_menu(event, user)

    elif data.startswith("setcat_"):
        cat_key = data.split("_")[1]
        user["target_category"] = cat_key
        users[uid] = user
        save_data(users)
        cat_titles = {
            "ticaret": "Ticaret & Alim-Satim",
            "sohbet": "Sohbet & Topluluk",
            "borsa": "Borsa & Kripto",
            "haber": "Teknoloji & Yazilim",
            "custom": "Ozel Grup Listesi"
        }
        await event.answer(f"Hedef havuz: {cat_titles.get(cat_key, cat_key)} secildi.", alert=True)
        await render_categories_menu(event, user)

    elif data == "ad_add_custom_group":
        USER_STATES[uid] = "waiting_custom_groups"
        await safe_edit_event(
            event,
            f"           **OZEL GRUP / KANAL EKLE**\n"
            f"{LINE}\n\n"
            f"Otomatik mesaj gondermek istediginiz grup veya kanallari\n"
            f"bu sohbete mesaj olarak gonderin.\n\n"
            f"Ornek Formatlar:\n"
            f"• `@grup1 @grup2`\n"
            f"• `https://t.me/grup3`\n"
            f"• Her satira bir grup adi\n\n"
            f"Not: Gonderici hesabiniz bu gruplara sirayla\n"
            f"katilip mesajinizi belirlenen aralikla iletir.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("Iptal Et", b"ad_show_groups")]]
        )

    elif data == "ad_clear_custom":
        user["custom_groups"] = []
        if user.get("target_category") == "custom":
            user["target_category"] = "sohbet"
        users[uid] = user
        save_data(users)
        await event.answer("Ozel grup listeniz temizlendi.", alert=True)
        await render_categories_menu(event, user)

    elif data == "ad_add_account":
        acc_info = user.get("account_name", "Bagli hesap yok")
        msg = (
            f"           **GONDERICI HESAP YONETIMI**\n"
            f"{LINE}\n\n"
            f"**Mevcut Hesap:** `{acc_info}`\n\n"
            f"Mesajlarin gonderilecegi Telegram hesabinizi\n"
            f"Telethon StringSession anahtariniz ile baglayabilirsiniz.\n\n"
            f"Test Hesabi Hizli Baglama:\n"
            f"Asagidaki butona basarak hazir test hesabini (+13869914668)\n"
            f"tek tikla profilinize baglayabilirsiniz.\n\n"
            f"Destek & Kurulum: @{SUPPORT_USERNAME}\n\n"
            f"{LINE}"
        )
        await safe_edit_event(event, msg, buttons=[
            [Button.inline("Test Hesabini Bagla (+1386)", b"bind_test_account")],
            [Button.inline("StringSession Gir", b"input_session")],
            [Button.inline("<-- Geri", b"menu_ad_engine")]
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
        user["ad_messages"] = user.get("ad_messages") or ["Selamlar herkese, iyi gunler"]
        user["ad_interval"] = user.get("ad_interval", 60)
        users[uid] = user
        save_data(users)
        await event.answer("Test hesabi (+13869914668) basariyla baglandi.", alert=True)
        await render_ad_engine(event, user)

    elif data == "input_session":
        USER_STATES[uid] = "waiting_session_string"
        await safe_edit_event(
            event,
            f"           **SESSION GIRISI**\n"
            f"{LINE}\n\n"
            f"Telethon StringSession anahtarinizi\n"
            f"bu sohbete mesaj olarak gonderin.\n\n"
            f"Sistem anahtarinizi aninda test edip\n"
            f"hesap bilgilerinizi dogrulayacaktir.\n\n"
            f"{LINE}",
            buttons=[[Button.inline("Iptal Et", b"ad_add_account")]]
        )

    # 2. KOD PAKETLERI & BOT MAGAZASI
    elif data == "menu_store":
        msg = (
            f"           **KOD & YAZILIM MAGAZASI**\n"
            f"{LINE}\n\n"
            f"Profesyonel gelistiriciler ve girisimciler icin hazirlanmis,\n"
            f"**temiz kodlu**, **kuruluma hazir** paketler ve **ozel yazilim** hizmetleri.\n\n"
            f"Her pakette acik kaynak kod, kurulum dokumani\n"
            f"veya anahtar teslim gelistirme dahildir.\n\n"
            f"**Haftanin Cok Satani:**\n"
            f"     Oto-Reklam Bot Scripti\n\n"
            f"{LINE}\n"
            f"Detay gormek icin paketi veya hizmeti secin:"
        )
        buttons = [
            [Button.url("Shopier Magazasini Ac (Tum Ilanlar)", SHOPIER_URL)],
            [Button.inline("Jarvis Core AI Asistan - 350 TL", b"prod_1")],
            [Button.inline("Oto-Reklam Bot Scripti - 450 TL", b"prod_2")],
            [Button.inline("Fiyat Takip Scraper - 300 TL", b"prod_3")],
            [Button.inline("Full Mini App Kiti - 400 TL", b"prod_4")],
            [Button.inline("Ozel Web Sitesi Kodlama - 799.90 TL", b"prod_5")],
            [Button.inline("Ozel Bot Yazilimi Kodlama - 499.90 TL", b"prod_6")],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data.startswith("prod_"):
        pid = data.split("_")[1]
        products = {
            "1": {
                "title": "Jarvis Core AI Asistan Iskeleti",
                "price": "350 TL",
                "badge": "[POPULER]",
                "url": "https://www.shopier.com/JarvisStore/51058105",
                "desc": "Sesli/yazili komut algilayan, Python + LLM mimarili,\nsistem gorevlerini otomatiklestiren akilli asistan cekirdegi.",
                "features": [
                    "Python 3.10+ & AsyncIO altyapisi",
                    "Telegram & Masaustu entegrasyonu",
                    "Tam acik kaynak + kurulum kilavuzu",
                    "GPT/Gemini API entegrasyonu hazir"
                ]
            },
            "2": {
                "title": "Telegram Oto-Reklam Bot Scripti",
                "price": "450 TL",
                "badge": "[COK SATAN]",
                "url": "https://www.shopier.com/JarvisStore/51058117",
                "desc": "Coklu hesap yonetimi, anti-flood gecikme sistemi,\n65+ ticaret grubu entegrasyonu ve rotasyonlu mesaj motoru.",
                "features": [
                    "Telethon tabanli guclu motor",
                    "Anti-Ban & Replay Guard koruma",
                    "Web panel & zamanlayici entegre",
                    "Otomatik grup kesfi & katilma"
                ]
            },
            "3": {
                "title": "E-Ticaret & Fiyat Takip Scraper",
                "price": "300 TL",
                "badge": "[YENI]",
                "url": "https://www.shopier.com/JarvisStore/51058118",
                "desc": "Trendyol, Yemeksepeti ve e-ticaret sitelerinden\nanlik kupon ve fiyat alarmi toplayan bot seti.",
                "features": [
                    "Playwright & Cloudflare Bypass",
                    "Anlik Telegram alarm bildirimi",
                    "Otomatik stok takibi"
                ]
            },
            "4": {
                "title": "Full-Stack Mini App + Shopier Kiti",
                "price": "400 TL",
                "badge": "[EN IYI DEGER]",
                "url": "https://www.shopier.com/JarvisStore/51058119",
                "desc": "Kendi Telegram Mini App magazanzizi 10 dakikada kurun.\nFlask backend + Vite frontend + Shopier odeme entegrasyonu.",
                "features": [
                    "Hazir tasarim & webhooklar",
                    "Render/Vercel dagitimina hazir",
                    "Shopier otomatik odeme & teslimat"
                ]
            },
            "5": {
                "title": "Ozel Web Sitesi Gelistirme & Kodlama",
                "price": "799.90 TL",
                "badge": "[OZEL PROJE]",
                "url": SHOPIER_URL,
                "desc": "Kurumsal firma, e-ticaret, landing page veya ozel web platformu yazilim & tasarim hizmeti.\n\n**Onemli Bilgilendirme:** Belirtilen 799.90 TL taban / baslangic fiyatidir. Siteden siteye, sayfa adedine ve projenin kapsamina / ek ozelliklerine gore fiyatta degisiklik olabilir. Siparis oncesinde veya sonrasinda dogrudan destek hesabimiza yazarak projenizi detaylandirabilirsiniz.",
                "features": [
                    "Modern, %100 mobil uyumlu ve SEO dostu arayuz",
                    "React / Next.js / Python Flask mimarisi",
                    "Shopier / iyzico 3D guvenli odeme altyapisi",
                    "Hizli sunucu kurulumu ve SSL sertifikasi teslimi",
                    "Gelistirici ile birebir analiz & kapsam gorusmesi"
                ]
            },
            "6": {
                "title": "Ozel Telegram Bot Yazilimi & Kodlama",
                "price": "499.90 TL",
                "badge": "[OZEL BOT]",
                "url": SHOPIER_URL,
                "desc": "Ihtiyaciniza tam uygun ozel Telegram bot gelistirme, otomasyon, magaza/odeme botu veya veri toplama sistemi.\n\n**Onemli Bilgilendirme:** Belirtilen 499.90 TL taban / baslangic fiyatidir. Botun islevlerine, API entegrasyonlarina ve proje karmasikligina gore fiyatta degisiklik olabilir. Siparis oncesinde veya sonrasinda dogrudan destek hesabimiza yazabilirsiniz.",
                "features": [
                    "Telethon / Aiogram tabanli ultra hizli asenkron motor",
                    "Odeme bildirim, magaza veya otomatik yanit modulleri",
                    "Web paneli ve canli log izleme entegrasyonu",
                    "7/24 kesintisiz sunucu kurulumu ve teslimati",
                    "Dogrudan gelistirici ile proje planlama destegi"
                ]
            }
        }
        p = products.get(pid)
        if not p:
            return

        feat_text = "\n".join(f"  *  {f}" for f in p["features"])

        msg = (
            f"           **{p['title']}**\n"
            f"{LINE}\n\n"
            f"  {p['badge']}      **{p['price']}**\n\n"
            f"{p['desc']}\n\n"
            f"**Paket & Hizmet Detaylari:**\n"
            f"{feat_text}\n\n"
            f"{LINE}\n\n"
            f"[+] Acik kaynak kod / Anahtar teslim kurulum\n"
            f"[+] Kurulum & kullanim dokumani dahil\n"
            f"[+] Shopier 3D Secure guvenli odeme\n"
            f"[+] Odeme sonrasi dogrudan teslimat & destek"
        )

        if pid in ("5", "6"):
            buttons = [
                [Button.url(f"Shopier'dan Satin Al - {p['price']}", p.get("url", SHOPIER_URL))],
                [Button.url("Projeyi Gorus & Teklif Al (Destek)", SUPPORT_URL)],
                [Button.inline("<-- Magazaya Don", b"menu_store")]
            ]
        else:
            buttons = [
                [Button.url(f"Shopier'dan Satin Al - {p['price']}", p.get("url", SHOPIER_URL))],
                [Button.url("Demoyu Kanalda Incele", CHANNEL_URL)],
                [Button.inline("<-- Magazaya Don", b"menu_store")]
            ]
        await safe_edit_event(event, msg, buttons=buttons)

    # 3. J.A.R.V.I.S. MASAUSTU AI PROJESI
    elif data == "menu_ai_tools":
        msg = (
            f"           **J.A.R.V.I.S. AI MASAUSTU ASISTANI**\n"
            f"{LINE}\n\n"
            f"Windows icin ozel gelistirilmis, Python gerektirmeyen\n"
            f"**tasinabilir masaustu sesli asistan projesi.**\n\n"
            f"{DOT}  **Ultra Gercekci Turkce Ses:**\n"
            f"     Insan dogalliginda konusur, aninda sesli cevap verir.\n\n"
            f"{DOT}  **0 ms Aninda Susturma:**\n"
            f"     Konusurken Esc tusuna bastiginiz an susar.\n\n"
            f"{DOT}  **Canli Internet & Cok Kaynakli Web Arama:**\n"
            f"     Guncel piyasa ve haber verilerini internetten derler.\n\n"
            f"{DOT}  **Sifir Kurulum:**\n"
            f"     Direkt calistirilabilir .exe paketi.\n\n"
            f"{LINE}\n"
            f"Asagidaki butonlarla videoyu izleyin veya PC demo paketini indirin:"
        )
        buttons = [
            [Button.inline("Kullanim Videosunu Gonder (Chat'e)", b"jarvis_send_video")],
            [Button.inline("Ucretsiz PC Demo Paketi (.ZIP)", b"jarvis_send_demo")],
            [Button.url("Shopier'dan Lisans Satin Al (350 TL)", "https://www.shopier.com/JarvisStore/51058105")],
            [Button.inline("Duyuru Kanalina Paylas (Video & Demo)", b"jarvis_broadcast_channel")],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "jarvis_send_video":
        await event.answer("Tanitim videosu gonderiliyor...", alert=False)
        video_path = os.path.join("static", "jarvis_demo_video.mp4")
        caption = (
            "**J.A.R.V.I.S. Kisisel AI Masaustu Asistani - Kullanim Rehberi**\n\n"
            "• Ultra gercekci Turkce sesli yanit sistemi\n"
            "• 0 ms aninda Esc tusuyla susturma\n"
            "• Canli web tarama ve akilli gorev yurutme\n"
            "• Sifir kurulum: Windows portable EXE paketi\n\n"
            "Ucretsiz Demo: https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n"
            "Shopier Lisans: https://www.shopier.com/JarvisStore/51058105\n"
            "Duyuru Kanali: @JarvisCraftDuyuru"
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
                    f"**J.A.R.V.I.S. Tanitim Videosu:**\n"
                    f"https://bot-service-production-9d74.up.railway.app/static/jarvis_demo_video.mp4\n\n"
                    f"{caption}"
                )
        except Exception as e:
            logger.warning(f"Direct video send error: {e}")
            await event.respond(
                f"**J.A.R.V.I.S. Tanitim Videosu:**\n"
                f"https://bot-service-production-9d74.up.railway.app/static/jarvis_demo_video.mp4\n\n"
                f"{caption}"
            )

    elif data == "jarvis_send_demo":
        await event.answer("Demo paketi hazirlaniyor...", alert=False)
        demo_msg = (
            "**J.A.R.V.I.S. Musteri Demo Paketi**\n\n"
            "• 10 Soru / Komut Deneme Hakki\n"
            "• Ilk 3 yanitta ultra gercekci Turkce sesli asistan\n"
            "• 0 ms aninda `Esc` ile susturma\n"
            "• Canli cok kaynakli web arama\n\n"
            "Asagidaki baglantidan dogrudan bilgisayariniza indirebilirsiniz:\n"
            "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n\n"
            "*Indirdiginiz ZIP dosyasini klasore cikartip `LisansArena_JARVIS_DEMO.exe`ye cift tiklamaniz yeterlidir. Sifir kurulum gerektirir.*"
        )
        buttons = [
            [Button.url("Demo Paketini Indir (.ZIP)", "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip")],
            [Button.url("Tam Surum Lisans Al (350 TL)", "https://www.shopier.com/JarvisStore/51058105")],
            [Button.inline("<-- J.A.R.V.I.S. Menusu", b"menu_ai_tools")]
        ]
        await event.respond(demo_msg, buttons=buttons)

    elif data == "jarvis_broadcast_channel":
        await event.answer("Kanala gonderiliyor...", alert=False)
        channel_post = (
            "**J.A.R.V.I.S. AI MASAUSTU ASISTANI YAYINDA**\n\n"
            "Windows bilgisayarinizda sifir kurulumla calisan, konusan, arastiran ve komutlarinizi yerine getiren yapay zeka masaustu asistani.\n\n"
            "**One Cikan Ozellikler:**\n"
            "• Ultra gercekci Turkce sesli yanit\n"
            "• 0 ms aninda 'Esc' tusuyla susturma\n"
            "• Canli cok kaynakli internet aramasi\n"
            "• Kuruluma ihtiyac duymayan tasinabilir .exe\n\n"
            "Ucretsiz Demo Indir:\n"
            "https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip\n\n"
            "Shopier Guvenli Siparis (350 TL):\n"
            "https://www.shopier.com/JarvisStore/51058105\n\n"
            "Bot: @JarvisCraftsBot\n"
            f"Destek: {SUPPORT_URL} (@{SUPPORT_USERNAME})"
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
            await event.respond(f"Tanitim mesaji ve video basariyla @{CHANNEL_USERNAME} kanalina iletildi.")
        except Exception as e:
            logger.error(f"Channel broadcast error: {e}")
            await event.respond(f"Kanala paylasim yapilamadi: {e}\n(Botun kanalda Yonetici yetkisi oldugundan emin olun)")

    # 4. VIP & BAKIYE
    elif data == "menu_vip":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        if is_vip:
            rem_secs = vip_until - time.time()
            rem_days = int(rem_secs // 86400)
            rem_hours = int((rem_secs % 86400) // 3600)
            vip_status = f"[AKTIF] {rem_days} gun {rem_hours} saat kaldi"
        else:
            vip_status = "[STANDART] Ucretsiz Plan"

        msg = (
            f"           **VIP PAKETLER & AVANTAJLAR**\n"
            f"{LINE}\n\n"
            f"**Mevcut Statunuz:** `{vip_status}`\n\n"
            f"**HESAP & PLAN FARKLARI:**\n\n"
            f"**Ucretsiz (Standart) Plan:**\n"
            f"• 1 Adet Gonderici Telegram Hesabi\n"
            f"• 60 Dakika Standart Gonderim (Hesap Korumali)\n"
            f"• 4 Hazir Kategori Havuzu (Ticaret, Sohbet, Borsa, Teknoloji)\n"
            f"• Gunluk 25 Gonderi Limiti\n\n"
            f"**Haftalik VIP Paket (150 TL):**\n"
            f"• 2 Adet Gonderici Hesap Slotu (Otomatik Rotasyon)\n"
            f"• Esnek Aralik Secimi (30 - 45 Dk Hizli Mod)\n"
            f"• Sinirsiz Ozel Grup & Kanal Ekleme Destegi\n"
            f"• Canli Iletim Raporlari (Telegram DM Bildirimi)\n"
            f"• 7 Gun Kesintisiz 7/24 Bulut Otomasyonu\n\n"
            f"**Aylik Sinirsiz VIP Paket (350 TL):**\n"
            f"• 5 Adet Eszamanli Gonderici Hesap Slotu (Multi-Session)\n"
            f"• Tamamen Sinirsiz Gunluk Gonderi (Kota / Limit Yok)\n"
            f"• Gelismis Anti-Ban & FloodGuard Pro (Akilli Dinamik Aralik)\n"
            f"• Tum Hazir Havuzlar + Sinirsiz Ozel Grup/Kanal Listesi\n"
            f"• Oncelikli Arka Plan Kuyrugu & Canli DM Bildirimleri\n"
            f"• 7/24 Birebir Gelistirici Kurulum Destegi\n"
            f"• 30 Gun Kesintisiz Reklam & Tanitim Gucu\n\n"
            f"{LINE}\n"
            f"Paketinizi secip hemen yukseltebilirsiniz:"
        )
        buttons = [
            [Button.inline("Haftalik VIP Al (150 TL)", b"buy_vip_haftalik")],
            [Button.inline("Aylik Sinirsiz VIP Al (350 TL)", b"buy_vip_aylik")],
            [Button.url("Shopier Magazasindan Al", SHOPIER_URL)],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "buy_vip_haftalik":
        url = "https://www.shopier.com/JarvisStore/51058120"
        msg = (
            f"           **HAFTALIK VIP SIPARISI**\n"
            f"{LINE}\n\n"
            f"**Paket:** Haftalik VIP (7 Gun)\n"
            f"**Ucret:** 150 TL\n\n"
            f"**Ozellikler:**\n"
            f"• 2 Telegram Gonderici Hesap Slotu\n"
            f"• 30 - 45 Dk Hizli Gonderim Secenegi\n"
            f"• Sinirsiz Ozel Grup Havuzu\n"
            f"• DM Canli Gonderim Raporlari\n\n"
            f"Asagidaki Shopier linkinden 3D Secure guvencesiyle satin alabilirsiniz.\n"
            f"Satin alimdan sonra siparis numaranizi 'Siparislerim' alanindan tanimlayabilirsiniz.\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.url("Shopier ile Guvenli Ode (150 TL)", url)],
            [Button.inline("[+] Siparisimi Tanimla", b"claim_order_start")],
            [Button.inline("<-- VIP Menusune Don", b"menu_vip")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "buy_vip_aylik":
        url = "https://www.shopier.com/JarvisStore/51058121"
        msg = (
            f"           **AYLIK SINIRSIZ VIP SIPARISI**\n"
            f"{LINE}\n\n"
            f"**Paket:** Aylik Sinirsiz VIP (30 Gun)\n"
            f"**Ucret:** 350 TL\n\n"
            f"**Ozellikler:**\n"
            f"• 5 Eszamanli Telegram Gonderici Hesap Slotu\n"
            f"• Tamamen Sinirsiz Gunluk Gonderim (Sifir Kota)\n"
            f"• Anti-Ban & Akilli Dinamik Gecikme Korumasi\n"
            f"• Oncelikli Bulut Kuyrugu ve Canli DM Raporu\n"
            f"• Birebir Gelistirici Destegi\n\n"
            f"Asagidaki Shopier linkinden 3D Secure guvencesiyle satin alabilirsiniz.\n"
            f"Satin alimdan sonra siparis numaranizi 'Siparislerim' alanindan tanimlayabilirsiniz.\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.url("Shopier ile Guvenli Ode (350 TL)", url)],
            [Button.inline("[+] Siparisimi Tanimla", b"claim_order_start")],
            [Button.inline("<-- VIP Menusune Don", b"menu_vip")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    # 5. HESABIM & PROFIL
    elif data == "menu_profile":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        if is_vip:
            rem_secs = vip_until - time.time()
            rem_days = int(rem_secs // 86400)
            rem_hours = int((rem_secs % 86400) // 3600)
            plan_str = f"[VIP Aktif] {rem_days} gun {rem_hours} saat"
        else:
            plan_str = "[Standart] Ucretsiz Plan"

        balance = user.get("balance", 0.0)
        u_name = sender.first_name or "Kullanici"
        u_handle = f"@{sender.username}" if sender.username else "Yok"
        is_running = user.get("is_running", False)
        run_str = "Calisiyor" if is_running else "Durduruldu"
        acc_name = user.get("account_name", "Bagli hesap yok")
        interval = user.get("ad_interval", 60)
        total_sent = user.get("total_sent", 0)

        msg = (
            f"           **HESABIM & PROFIL BILGILERI**\n"
            f"{LINE}\n\n"
            f"**Kullanici:**    {u_name} ({u_handle})\n"
            f"**Telegram ID:**   `{uid}`\n"
            f"**Mevcut Bakiye:** `{balance:.2f} TL`\n"
            f"**Uyelik Plani:** `{plan_str}`\n\n"
            f"**Oto-Reklam Durumu:**\n"
            f"• Gonderici: `{acc_name}`\n"
            f"• Durum: `{run_str}`\n"
            f"• Periyot: Her `{interval}` dakikada bir\n"
            f"• Toplam Gonderi: `{total_sent}` adet\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.inline("Siparislerim & Uyeliklerim", b"menu_orders")],
            [Button.inline("Oto-Reklam Motoru", b"menu_ad_engine"),
             Button.inline("VIP Satin Al / Yukselt", b"menu_vip")],
            [Button.url("Web Paneli Ac", APP_URL)],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    # 6. SIPARISLERIM & UYELIKLERIM
    elif data == "menu_orders":
        vip_until = user.get("vip_until")
        is_vip = bool(vip_until and vip_until > time.time())
        orders = user.get("orders", [])

        lines = [
            f"           **SIPARISLERIM & UYELIKLERIM**",
            f"{LINE}\n"
        ]

        if is_vip:
            rem_secs = vip_until - time.time()
            rem_days = int(rem_secs // 86400)
            rem_hours = int((rem_secs % 86400) // 3600)
            plan_name = user.get("plan_name", "Aylik Sinirsiz VIP" if rem_days > 7 else "Haftalik VIP")
            slots = user.get("account_slots", 5 if rem_days > 7 else 2)
            lines.append(f"**Aktif VIP Uyeligi:**")
            lines.append(f"  • Paket: **{plan_name}**")
            lines.append(f"  • Kalan Sure: `{rem_days} gun {rem_hours} saat`")
            lines.append(f"  • Gonderici Slotu: `{slots} adet hesap`")
            lines.append(f"  • Hız: `Coklu hesap rotasyonu & anti-ban korumali`")
            lines.append(f"  • Durum: `[AKTIF] Kullanımda`\n")
        else:
            lines.append(f"**Mevcut Paket:** `Standart (Ucretsiz Plan)`\n")

        if orders:
            lines.append(f"**Siparis Gecmisi ({len(orders)} islem):**")
            for idx, o in enumerate(orders[-5:], 1):
                title = o.get("title", "Yazilim / Uyelik")
                price = o.get("price", "-")
                date_str = o.get("date", "-")
                status_str = o.get("status", "[OK] Tamamlandi")
                lines.append(f"  {idx}. **{title}** (`{price}`)\n     Tarih: {date_str} | Durum: {status_str}")
            lines.append("")
        else:
            if not is_vip:
                lines.append(
                    "Henuz tamamlanmis bir siparisiniz veya aktif VIP uyeliginiz bulunmuyor.\n\n"
                    "Shopier magazimizdan satin alim yaptiysaniz asagidaki 'Siparisimi Tanimla' "
                    "butonuna basarak siparis numaranizi girip aninda aktif edebilirsiniz.\n"
                )

        lines.append(LINE)
        msg = "\n".join(lines)
        buttons = [
            [Button.inline("[+] Siparisimi Tanimla / Sorgula", b"claim_order_start")],
            [Button.inline("Kod Magazasini Ac", b"menu_store"),
             Button.inline("VIP Satin Al / Yukselt", b"menu_vip")],
            [Button.url("Siparis Bildirimi & Destek", SUPPORT_URL)],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "claim_order_start":
        USER_STATES[uid] = "waiting_order_query"
        msg = (
            f"           **SIPARIS TANIMLAMA & SORGULAMA**\n"
            f"{LINE}\n\n"
            f"Shopier uzerinden satin alim yaptiysaniz, size verilen\n"
            f"**Siparis Numarasini** (ornegin: `337297639`)\n"
            f"veya satin alirken girdiginiz **E-posta Adresinizi**\n"
            f"bu sohbete mesaj olarak yazip gonderin.\n\n"
            f"Sistem siparisinizi otomatik dogrulayip VIP uyeliginizi\n"
            f"veya kod paketlerinizi aninda hesabiniza tanimlayacaktir.\n\n"
            f"{LINE}"
        )
        await safe_edit_event(event, msg, buttons=[
            [Button.inline("Vazgec", b"menu_orders")]
        ])

    # 7. CANLI DESTEK & ILETISIM
    elif data == "menu_support":
        msg = (
            f"           **CANLI DESTEK & ILETISIM**\n"
            f"{LINE}\n\n"
            f"Her turlu teknik soru, ozel bot/web yazilim teklifi\n"
            f"veya odeme aktivasyonu icin 7/24 hizmetinizdeyiz:\n\n"
            f"• **Resmi Destek Hesabi:** @JarvisCraft\n"
            f"• **Ortalama Yanit Suresi:** 5-10 dakika\n"
            f"• **Calisma Saatleri:** 7/24 kesintisiz destek\n\n"
            f"Dilerseniz dogrudan **@JarvisCraft** hesabina yazabilir,\n"
            f"dilerseniz asagidaki butondan bu sohbet icinde aninda destek talebi olusturabilirsiniz.\n\n"
            f"{LINE}\n\n"
            f"• **Resmi Shopier:** {SHOPIER_URL}\n"
            f"• **Duyuru Kanali:** {CHANNEL_URL}"
        )
        buttons = [
            [Button.url("@JarvisCraft Hesabina Yaz", SUPPORT_URL)],
            [Button.inline("Bu Sohbette Destek Talebi Ac", b"ticket_start")],
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

    elif data == "ticket_start":
        USER_STATES[uid] = "waiting_support_message"
        msg = (
            f"           **YENI DESTEK TALEBI OLUSTUR**\n"
            f"{LINE}\n\n"
            f"Lutfen iletmek istediginiz teknik soruyu, siparis/odeme detayinizi "
            f"veya proje talebinizi tek parca mesaj olarak yazip gonderin.\n\n"
            f"Mesajiniz dogrudan gelistirici ekibimize iletilecek ve yanitlandiginda "
            f"bu bot uzerinden aninda bildirim alacaksiniz.\n\n"
            f"{LINE}"
        )
        buttons = [
            [Button.inline("Vazgec", b"menu_support")]
        ]
        await safe_edit_event(event, msg, buttons=buttons)

# -------------------------------------------------------------
# Text Message Handler (Private Only)
# -------------------------------------------------------------
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
            f"           **DESTEK TALEBINIZ ALINDI**\n"
            f"{LINE}\n\n"
            f"Ilettiginiz mesaj dogrudan teknik destek ekibimize aktarilmistir.\n"
            f"En kisa surede bu bot uzerinden yanit alacaksiniz.\n\n"
            f"Resmi Destek: @JarvisCraft\n"
            f"{LINE}"
        )
        await event.respond(ack, buttons=[
            [Button.inline("<-- Ana Menu", b"main_menu")]
        ])

        u_handle = f"@{sender.username}" if getattr(sender, "username", None) else "yok"
        admin_alert = (
            f"[YENI DESTEK TALEBI - JarvisCraft]\n"
            f"{LINE}\n\n"
            f"Kullanici: {sender.first_name} ({u_handle})\n"
            f"ID: `{uid}`\n"
            f"Talep ID: `{ticket_id}`\n\n"
            f"Mesaj:\n"
            f"```\n{event.raw_text}\n```\n\n"
            f"Yanitlamak icin:\n"
            f"`/cevap {uid} <yanitiniz>`\n"
            f"{LINE}"
        )
        for a_id in ADMIN_IDS:
            try:
                await client.send_message(a_id, admin_alert)
            except Exception:
                pass
        return

    elif state == "waiting_order_query":
        USER_STATES.pop(uid, None)
        query = event.raw_text.strip()
        users = load_data()
        if uid not in users:
            users[uid] = {"user_id": int(uid), "created_at": time.time()}

        status_msg = await event.respond("Siparisiniz Shopier veritabaninda araniyor, lutfen bekleyin...")

        found_order = None
        # Check Shopier API if token configured
        pat = SHOPIER_TOKEN or os.environ.get("SHOPIER_JARVIS_ACCESS_TOKEN", "").strip()
        if pat:
            try:
                req = urllib.request.Request(
                    "https://api.shopier.com/v1/orders?limit=50",
                    headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data_obj = json.loads(resp.read().decode("utf-8"))
                    order_list = data_obj if isinstance(data_obj, list) else data_obj.get("data") or data_obj.get("orders") or []
                    for o in order_list:
                        o_id = str(o.get("id") or o.get("orderNumber") or "")
                        buyer = o.get("buyer") or o.get("shippingInfo") or {}
                        b_email = str(buyer.get("email") or "").lower()
                        b_phone = str(buyer.get("phone") or "").replace("+", "").replace(" ", "")
                        p_status = str(o.get("paymentStatus") or o.get("status") or "").lower()
                        if p_status in ("paid", "completed", "success"):
                            if query.lower() == o_id.lower() or query.lower() == b_email or query.replace(" ", "") == b_phone:
                                found_order = o
                                break
            except Exception as api_err:
                logger.warning(f"Shopier order query error: {api_err}")

        # Check local/firestore fallback
        if not found_order:
            try:
                import firestore_helper
                clean_email = query.replace("@", "_").replace(".", "_")
                doc = firestore_helper.get_document(f"order_email_{clean_email}") or firestore_helper.get_document(f"shopier_order_{query}")
                if doc and doc.get("orders"):
                    found_order = doc["orders"][-1]
            except Exception:
                pass

        if found_order:
            order_id = str(found_order.get("id") or found_order.get("orderNumber") or found_order.get("order_id") or query)
            line_items = found_order.get("lineItems") or found_order.get("products") or []
            item_title = "JarvisCraft Paketi"
            if line_items and isinstance(line_items[0], dict):
                item_title = line_items[0].get("title") or line_items[0].get("name") or item_title
            elif found_order.get("product_name"):
                item_title = found_order.get("product_name")

            price = str(found_order.get("totalAmount") or found_order.get("amount") or "-")
            curr_orders = users[uid].get("orders", [])
            
            # Check if order already claimed by this user
            if any(str(x.get("order_id")) == str(order_id) for x in curr_orders):
                await status_msg.edit(
                    f"**Bu Siparis Zaten Hesabiniza Tanimli:**\n"
                    f"• Siparis No: `{order_id}`\n"
                    f"• Urun: **{item_title}**\n\n"
                    f"Aktif durumunuzu 'Siparislerim & Uyeliklerim' menusunden kontrol edebilirsiniz.",
                    buttons=[[Button.inline("<-- Siparisler Menusu", b"menu_orders")]]
                )
                return

            # Determine product activation
            lowered = item_title.lower()
            if "haftalık" in lowered or "haftalik" in lowered or "150" in price:
                duration = 7 * 86400
                curr_until = max(time.time(), users[uid].get("vip_until") or 0)
                users[uid]["vip_until"] = curr_until + duration
                users[uid]["plan_name"] = "Haftalik VIP"
                users[uid]["account_slots"] = 2
                benefit_text = "Haftalik VIP uyeliginiz (7 gun, 2 hesap slotu) aninda aktif edildi."
            elif "aylık" in lowered or "aylik" in lowered or "350" in price:
                duration = 30 * 86400
                curr_until = max(time.time(), users[uid].get("vip_until") or 0)
                users[uid]["vip_until"] = curr_until + duration
                users[uid]["plan_name"] = "Aylik Sinirsiz VIP"
                users[uid]["account_slots"] = 5
                benefit_text = "Aylik Sinirsiz VIP uyeliginiz (30 gun, 5 slot, anti-ban) aninda aktif edildi."
            elif "asistan" in lowered or "jarvis core" in lowered:
                benefit_text = (
                    "Jarvis Core AI Masaustu Asistani lisansiniz tanimlandi.\n"
                    "Indirme Linki: https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip"
                )
            elif "oto-reklam" in lowered:
                benefit_text = "Telegram Oto-Reklam Bot Script paketiniz tanimlandi. Destek hattimizdan (@JarvisCraft) kurulum dosyanizi teslim alabilirsiniz."
            else:
                benefit_text = f"'{item_title}' siparisiniz dogrulandi ve profilinize basariyla islendi."

            order_record = {
                "order_id": order_id,
                "title": item_title,
                "price": f"{price} TL",
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "[OK] Tamamlandi"
            }
            users[uid].setdefault("orders", []).append(order_record)
            save_data(users)

            success_text = (
                f"           **SIPARIS BASARIYLA TANIMLANDI**\n"
                f"{LINE}\n\n"
                f"Siparis No: `{order_id}`\n"
                f"Urun / Hizmet: **{item_title}**\n"
                f"Tutar: `{price} TL`\n\n"
                f"**Aktivasyon Durumu:**\n"
                f"{benefit_text}\n\n"
                f"{LINE}\n"
                f"Tesekkur eder, iyi calismalar dileriz."
            )
            await status_msg.edit(success_text, buttons=[
                [Button.inline("Siparislerimi Goruntule", b"menu_orders")],
                [Button.inline("<-- Ana Menu", b"main_menu")]
            ])

            # Notify admins
            for a_id in ADMIN_IDS:
                try:
                    await client.send_message(
                        a_id,
                        f"[OTOMATIK SIPARIS AKTIVASYONU]\n"
                        f"Kullanici ID: `{uid}`\n"
                        f"Siparis No: `{order_id}`\n"
                        f"Urun: {item_title}\n"
                        f"Tutar: {price} TL"
                    )
                except Exception:
                    pass
        else:
            fail_text = (
                f"           **SIPARIS BULUNAMADI**\n"
                f"{LINE}\n\n"
                f"Girdiginiz bilgi: `{query}`\n\n"
                f"Shopier sistemi uzerinde bu numara veya e-posta ile henuz onaylanmis bir odeme bulunamadi.\n\n"
                f"Odemenizi henuz tamamladiysaniz banka ve Shopier onayi 1-2 dakika surebilir. "
                f"Biraz bekleyip tekrar deneyebilir veya dogrudan destek hattimiza yazabilirsiniz:\n\n"
                f"Resmi Destek: @JarvisCraft\n"
                f"{LINE}"
            )
            await status_msg.edit(fail_text, buttons=[
                [Button.inline("Tekrar Dene", b"claim_order_start")],
                [Button.url("Canli Destek Al", SUPPORT_URL)],
                [Button.inline("<-- Ana Menu", b"main_menu")]
            ])
        return

    elif state == "waiting_ad_message":
        users = load_data()
        if uid in users:
            users[uid]["ad_messages"] = [event.raw_text]
            save_data(users)
        USER_STATES.pop(uid, None)
        await event.respond(
            f"           **REKLAM METNI GUNCELLENDI**\n"
            f"{LINE}\n\n"
            f"Yeni metniniz basariyla kaydedildi.\n\n"
            f"Onizleme:\n"
            f"```\n{event.raw_text}\n```\n\n"
            f"Oto-Reklam Motorundan gonderime\n"
            f"baslayabilirsiniz.\n\n"
            f"{LINE}",
            buttons=[
                [Button.inline("Oto-Reklam Paneli", b"menu_ad_engine")],
                [Button.inline("<-- Ana Menu", b"main_menu")]
            ]
        )

    elif state == "waiting_custom_groups":
        USER_STATES.pop(uid, None)
        raw_text = event.raw_text.strip()
        cleaned = re.findall(r"(?:https?://t\.me/)?@?([a-zA-Z0-9_]{4,32})", raw_text)
        cleaned = [g for g in cleaned if g.lower() not in ("joinchat", "c", "addstickers")]

        if not cleaned:
            await event.respond("Gecerli bir grup baglantisi veya kullanici adi bulunamadi.", buttons=[
                [Button.inline("Tekrar Dene", b"ad_add_custom_group")],
                [Button.inline("<-- Geri", b"ad_show_groups")]
            ])
            return

        users = load_data()
        existing = users.get(uid, {}).get("custom_groups", [])
        combined = list(dict.fromkeys(existing + cleaned))
        users[uid]["custom_groups"] = combined
        users[uid]["target_category"] = "custom"
        save_data(users)

        preview = ", ".join(f"@{g}" for g in cleaned[:5])
        await event.respond(
            f"           **OZEL GRUPLAR EKLENDI**\n"
            f"{LINE}\n\n"
            f"Eklenen grup sayisi: **{len(cleaned)}**\n"
            f"Toplam ozel listeniz: **{len(combined)}** grup\n\n"
            f"Ornekler: {preview}\n\n"
            f"Hedef kategoriniz otomatik olarak 'Ozel Liste' yapildi.\n"
            f"{LINE}",
            buttons=[
                [Button.inline("Oto-Reklam Paneline Don", b"menu_ad_engine")],
                [Button.inline("<-- Gruplari Gor", b"ad_show_groups")]
            ]
        )

    elif state == "waiting_session_string":
        USER_STATES.pop(uid, None)
        raw_session = event.raw_text.strip()
        validating_msg = await event.respond("Session anahtari test ediliyor...")

        try:
            test_cli = TelegramClient(StringSession(raw_session), API_ID, API_HASH)
            await test_cli.connect()
            if await test_cli.is_user_authorized():
                me = await test_cli.get_me()
                acc_name = f"{me.first_name} (@{me.username})" if me.username else me.first_name
                phone = me.phone or "Gizli"

                users = load_data()
                users[uid]["session_string"] = raw_session
                users[uid]["account_name"] = acc_name
                users[uid]["account_phone"] = phone
                users[uid]["account_id"] = me.id
                save_data(users)

                await test_cli.disconnect()
                await validating_msg.edit(
                    f"           **HESAP BASARIYLA BAGLANDI**\n"
                    f"{LINE}\n\n"
                    f"Hesap: **{acc_name}**\n"
                    f"Telefon: `{phone}`\n"
                    f"ID: `{me.id}`\n\n"
                    f"Oto-Reklam motoru artik bu hesap uzerinden mesaj iletecektir.\n"
                    f"{LINE}",
                    buttons=[
                        [Button.inline("Oto-Reklam Motoruna Git", b"menu_ad_engine")],
                        [Button.inline("<-- Ana Menu", b"main_menu")]
                    ]
                )
            else:
                await test_cli.disconnect()
                await validating_msg.edit(
                    f"Gecersiz veya sonlanmis Session anahtari. Lutfen tekrar deneyin.",
                    buttons=[
                        [Button.inline("Tekrar Dene", b"input_session")],
                        [Button.inline("<-- Geri", b"ad_add_account")]
                    ]
                )
        except Exception as e:
            await validating_msg.edit(
                f"Session baglanti hatasi: {e}",
                buttons=[
                    [Button.inline("Tekrar Dene", b"input_session")],
                    [Button.inline("<-- Geri", b"ad_add_account")]
                ]
            )

# -------------------------------------------------------------
# User Commands Shortcuts
# -------------------------------------------------------------
@client.on(events.NewMessage(pattern=r"^/(?:siparisler|siparislerim|orders)$", func=lambda e: e.is_private))
async def cmd_orders(event):
    uid = str(event.sender_id)
    users = load_data()
    user = users.get(uid, {})
    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    orders = user.get("orders", [])

    lines = [
        f"           **SIPARISLERIM & UYELIKLERIM**",
        f"{LINE}\n"
    ]

    if is_vip:
        rem_secs = vip_until - time.time()
        rem_days = int(rem_secs // 86400)
        rem_hours = int((rem_secs % 86400) // 3600)
        plan_name = user.get("plan_name", "Aylik Sinirsiz VIP" if rem_days > 7 else "Haftalik VIP")
        slots = user.get("account_slots", 5 if rem_days > 7 else 2)
        lines.append(f"**Aktif VIP Uyeligi:**")
        lines.append(f"  • Paket: **{plan_name}**")
        lines.append(f"  • Kalan Sure: `{rem_days} gun {rem_hours} saat`")
        lines.append(f"  • Gonderici Slotu: `{slots} adet hesap`")
        lines.append(f"  • Hiz: `Coklu hesap rotasyonu & anti-ban korumali`")
        lines.append(f"  • Durum: `[AKTIF] Kullanımda`\n")
    else:
        lines.append(f"**Mevcut Paket:** `Standart (Ucretsiz Plan)`\n")

    if orders:
        lines.append(f"**Siparis Gecmisi ({len(orders)} islem):**")
        for idx, o in enumerate(orders[-5:], 1):
            title = o.get("title", "Yazilim / Uyelik")
            price = o.get("price", "-")
            date_str = o.get("date", "-")
            status_str = o.get("status", "[OK] Tamamlandi")
            lines.append(f"  {idx}. **{title}** (`{price}`)\n     Tarih: {date_str} | Durum: {status_str}")
        lines.append("")
    else:
        if not is_vip:
            lines.append(
                "Henuz tamamlanmis bir siparisiniz veya aktif VIP uyeliginiz bulunmuyor.\n\n"
                "Shopier magazimizdan satin alim yaptiysaniz asagidaki 'Siparisimi Tanimla' "
                "butonuna basarak siparis numaranizi girip aninda aktif edebilirsiniz.\n"
            )

    lines.append(LINE)
    msg = "\n".join(lines)
    buttons = [
        [Button.inline("[+] Siparisimi Tanimla / Sorgula", b"claim_order_start")],
        [Button.inline("Kod Magazasini Ac", b"menu_store"),
         Button.inline("VIP Satin Al / Yukselt", b"menu_vip")],
        [Button.url("Siparis Bildirimi & Destek", SUPPORT_URL)],
        [Button.inline("<-- Ana Menu", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:hesap|hesabim|profil|profile)$", func=lambda e: e.is_private))
async def cmd_profile(event):
    uid = str(event.sender_id)
    sender = await event.get_sender()
    users = load_data()
    user = users.get(uid, {})
    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    if is_vip:
        rem_secs = vip_until - time.time()
        rem_days = int(rem_secs // 86400)
        rem_hours = int((rem_secs % 86400) // 3600)
        plan_str = f"[VIP Aktif] {rem_days} gun {rem_hours} saat"
    else:
        plan_str = "[Standart] Ucretsiz Plan"

    balance = user.get("balance", 0.0)
    u_name = sender.first_name or "Kullanici"
    u_handle = f"@{sender.username}" if getattr(sender, "username", None) else "Yok"
    is_running = user.get("is_running", False)
    run_str = "Calisiyor" if is_running else "Durduruldu"
    acc_name = user.get("account_name", "Bagli hesap yok")
    interval = user.get("ad_interval", 60)
    total_sent = user.get("total_sent", 0)

    msg = (
        f"           **HESABIM & PROFIL BILGILERI**\n"
        f"{LINE}\n\n"
        f"**Kullanici:**    {u_name} ({u_handle})\n"
        f"**Telegram ID:**   `{uid}`\n"
        f"**Mevcut Bakiye:** `{balance:.2f} TL`\n"
        f"**Uyelik Plani:** `{plan_str}`\n\n"
        f"**Oto-Reklam Durumu:**\n"
        f"• Gonderici: `{acc_name}`\n"
        f"• Durum: `{run_str}`\n"
        f"• Periyot: Her `{interval}` dakikada bir\n"
        f"• Toplam Gonderi: `{total_sent}` adet\n\n"
        f"{LINE}"
    )
    buttons = [
        [Button.inline("Siparislerim & Uyeliklerim", b"menu_orders")],
        [Button.inline("Oto-Reklam Motoru", b"menu_ad_engine"),
         Button.inline("VIP Satin Al / Yukselt", b"menu_vip")],
        [Button.url("Web Paneli Ac", APP_URL)],
        [Button.inline("<-- Ana Menu", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:destek|yardim|support|help)$", func=lambda e: e.is_private))
async def cmd_support(event):
    msg = (
        f"           **CANLI DESTEK & ILETISIM**\n"
        f"{LINE}\n\n"
        f"Her turlu teknik soru, ozel bot/web yazilim teklifi\n"
        f"veya odeme aktivasyonu icin 7/24 hizmetinizdeyiz:\n\n"
        f"• **Resmi Destek Hesabi:** @JarvisCraft\n"
        f"• **Ortalama Yanit Suresi:** 5-10 dakika\n"
        f"• **Calisma Saatleri:** 7/24 kesintisiz destek\n\n"
        f"{LINE}\n\n"
        f"• **Resmi Shopier:** {SHOPIER_URL}\n"
        f"• **Duyuru Kanali:** {CHANNEL_URL}"
    )
    buttons = [
        [Button.url("@JarvisCraft Hesabina Yaz", SUPPORT_URL)],
        [Button.inline("Bu Sohbette Destek Talebi Ac", b"ticket_start")],
        [Button.inline("<-- Ana Menu", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r"^/(?:vip|paketler)$", func=lambda e: e.is_private))
async def cmd_vip(event):
    uid = str(event.sender_id)
    users = load_data()
    user = users.get(uid, {})
    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    if is_vip:
        rem_secs = vip_until - time.time()
        rem_days = int(rem_secs // 86400)
        rem_hours = int((rem_secs % 86400) // 3600)
        vip_status = f"[AKTIF] {rem_days} gun {rem_hours} saat kaldi"
    else:
        vip_status = "[STANDART] Ucretsiz Plan"

    msg = (
        f"           **VIP PAKETLER & AVANTAJLAR**\n"
        f"{LINE}\n\n"
        f"**Mevcut Statunuz:** `{vip_status}`\n\n"
        f"**HESAP & PLAN FARKLARI:**\n\n"
        f"**Ucretsiz (Standart) Plan:**\n"
        f"• 1 Adet Gonderici Telegram Hesabi\n"
        f"• 60 Dakika Standart Gonderim (Hesap Korumali)\n"
        f"• 4 Hazir Kategori Havuzu\n"
        f"• Gunluk 25 Gonderi Limiti\n\n"
        f"**Haftalik VIP Paket (150 TL):**\n"
        f"• 2 Adet Gonderici Hesap Slotu (Otomatik Rotasyon)\n"
        f"• Esnek Aralik Secimi (30 - 45 Dk Hizli Mod)\n"
        f"• Sinirsiz Ozel Grup Ekleme Destegi\n"
        f"• Canli DM Bildirimleri\n"
        f"• 7 Gun Kesintisiz Bulut Otomasyonu\n\n"
        f"**Aylik Sinirsiz VIP Paket (350 TL):**\n"
        f"• 5 Adet Eszamanli Gonderici Hesap Slotu\n"
        f"• Tamamen Sinirsiz Gunluk Gonderi\n"
        f"• Gelismis Anti-Ban & FloodGuard Pro\n"
        f"• Tum Havuzlar + Sinirsiz Ozel Grup Listesi\n"
        f"• Oncelikli Kuyruk & Birebir Gelistirici Destegi\n"
        f"• 30 Gun Kesintisiz Guc\n\n"
        f"{LINE}"
    )
    buttons = [
        [Button.inline("Haftalik VIP Al (150 TL)", b"buy_vip_haftalik")],
        [Button.inline("Aylik Sinirsiz VIP Al (350 TL)", b"buy_vip_aylik")],
        [Button.url("Shopier Magazasindan Al", SHOPIER_URL)],
        [Button.inline("<-- Ana Menu", b"main_menu")]
    ]
    await event.respond(msg, buttons=buttons)

# -------------------------------------------------------------
# Admin Commands
# -------------------------------------------------------------
@client.on(events.NewMessage(pattern=r"^/cevap\s+(\d+)\s+(.+)$", func=lambda e: e.is_private))
async def cmd_admin_reply(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = int(event.pattern_match.group(1))
    reply_text = event.pattern_match.group(2).strip()

    user_msg = (
        f"**[JarvisCraft Destek Ekibi Yaniti]**\n"
        f"{LINE}\n\n"
        f"{reply_text}\n\n"
        f"{LINE}\n"
        f"Herhangi bir sorunuzda bu sohbetten /destek yazabilir veya "
        f"@JarvisCraft hesabina ulasabilirsiniz."
    )
    try:
        await client.send_message(target_uid, user_msg)
        await event.respond(f"Yanit basariyla iletildi (Kullanici: `{target_uid}`).")
    except Exception as e:
        await event.respond(f"Yanit gonderilemedi: {e}")

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
    plan_title = "Haftalik VIP" if tier == "haftalik" else "Aylik Sinirsiz VIP"
    price = "150 TL" if tier == "haftalik" else "350 TL"
    slots = 2 if tier == "haftalik" else 5

    curr_until = max(time.time(), users[target_uid].get("vip_until") or 0)
    users[target_uid]["vip_until"] = curr_until + duration
    users[target_uid]["plan_name"] = plan_title
    users[target_uid]["account_slots"] = slots

    order_record = {
        "order_id": str(uuid.uuid4())[:8],
        "title": plan_title,
        "price": price,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "[OK] Tamamlandi (Yonetici Tanimlamasi)"
    }
    if "orders" not in users[target_uid]:
        users[target_uid]["orders"] = []
    users[target_uid]["orders"].append(order_record)
    save_data(users)

    rem_days = int((users[target_uid]["vip_until"] - time.time()) // 86400)
    try:
        notify_user = (
            f"**TEBRIKLER! VIP UYELIGINIZ TANIMLANDI**\n"
            f"{LINE}\n\n"
            f"**Paket:** {plan_title}\n"
            f"**Hesap Slotu:** {slots} adet\n"
            f"**Toplam Sure:** {rem_days} gun\n\n"
            f"Oto-Reklam motorunuzdan artik esnek araliklari ve coklu hesaplari kullanabilirsiniz.\n"
            f"{LINE}"
        )
        await client.send_message(int(target_uid), notify_user)
    except Exception:
        pass

    await event.respond(f"Basarili: Kullanici `{target_uid}` icin **{plan_title}** tanimlandi ({rem_days} gun aktif).")

@client.on(events.NewMessage(pattern=r"^/bakiye_ekle\s+(\d+)\s+([\d\.,]+)$", func=lambda e: e.is_private))
async def cmd_admin_add_balance(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    raw_amount = event.pattern_match.group(2).replace(",", ".")
    try:
        amount = float(raw_amount)
    except ValueError:
        await event.respond("Gecersiz tutar formatı.")
        return

    users = load_data()
    if target_uid not in users:
        users[target_uid] = {"user_id": int(target_uid), "created_at": time.time()}

    curr_bal = users[target_uid].get("balance", 0.0)
    new_bal = curr_bal + amount
    users[target_uid]["balance"] = new_bal
    save_data(users)

    try:
        await client.send_message(
            int(target_uid),
            f"**BAKIYE YUKLEMESI BASARILI**\n{LINE}\n\n"
            f"Hesabiniza `{amount:.2f} TL` bakiye eklendi.\n"
            f"Yeni Bakiyeniz: `{new_bal:.2f} TL`\n{LINE}"
        )
    except Exception:
        pass

    await event.respond(f"Kullanici `{target_uid}` bakiyesine `{amount:.2f} TL` eklendi. Yeni: `{new_bal:.2f} TL`")

@client.on(events.NewMessage(pattern=r"^/siparis_ekle\s+(\d+)\s+(.+)\s+([\d\.,]+)$", func=lambda e: e.is_private))
async def cmd_admin_add_order(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    prod_title = event.pattern_match.group(2).strip()
    price = event.pattern_match.group(3).strip() + " TL"

    users = load_data()
    if target_uid not in users:
        users[target_uid] = {"user_id": int(target_uid), "created_at": time.time()}

    if "orders" not in users[target_uid]:
        users[target_uid]["orders"] = []

    order_record = {
        "order_id": str(uuid.uuid4())[:8],
        "title": prod_title,
        "price": price,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "[OK] Tamamlandi (Yonetici Tanimlamasi)"
    }
    users[target_uid]["orders"].append(order_record)
    save_data(users)

    try:
        await client.send_message(
            int(target_uid),
            f"**SIPARISINIZ TANIMLANDI**\n{LINE}\n\n"
            f"**Urun:** {prod_title}\n"
            f"**Tutar:** {price}\n\n"
            f"Siparislerinizi ve teslimat detaylarinizi /siparisler komutu ile inceleyebilirsiniz.\n{LINE}"
        )
    except Exception:
        pass

    await event.respond(f"Kullanici `{target_uid}` icin siparis kaydi eklendi: **{prod_title}** ({price})")

@client.on(events.NewMessage(pattern=r"^/kullanici\s+(\d+)$", func=lambda e: e.is_private))
async def cmd_admin_user_info(event):
    if event.sender_id not in ADMIN_IDS:
        return
    target_uid = str(event.pattern_match.group(1))
    users = load_data()
    user = users.get(target_uid)
    if not user:
        await event.respond(f"Kullanici `{target_uid}` bulunamadi.")
        return

    vip_until = user.get("vip_until")
    is_vip = bool(vip_until and vip_until > time.time())
    if is_vip:
        rem_secs = vip_until - time.time()
        rem_days = int(rem_secs // 86400)
        vip_str = f"VIP Aktif ({rem_days} gun)"
    else:
        vip_str = "Standart (Ucretsiz)"

    acc_name = user.get("account_name", "Bagli degil")
    total_sent = user.get("total_sent", 0)
    orders_cnt = len(user.get("orders", []))
    tickets_cnt = len(user.get("tickets", []))

    info = (
        f"**KULLANICI BILGILERI: `{target_uid}`**\n{LINE}\n\n"
        f"• Ad: {user.get('first_name', '-')}\n"
        f"• Username: @{user.get('username', '-')}\n"
        f"• Bakiye: `{user.get('balance', 0.0):.2f} TL`\n"
        f"• Statu: `{vip_str}`\n"
        f"• Bagli Hesap: `{acc_name}`\n"
        f"• Toplam Gonderi: `{total_sent}`\n"
        f"• Siparis Adedi: `{orders_cnt}`\n"
        f"• Destek Talepleri: `{tickets_cnt}`\n{LINE}"
    )
    await event.respond(info)

# -------------------------------------------------------------
# Oto-Reklam & Mesaj Motoru Arka Plan Servisi
# -------------------------------------------------------------
async def ad_engine_background_worker():
    logger.info("JarvisCraft Oto-Mesaj Arka Plan Motoru BASLATILDI.")
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
                                f"**[Oto-Mesaj Motoru] Gunluk Kota Bildirimi**\n{LINE}\n\n"
                                f"Ucretsiz standart planda gunluk 25 adetlik gonderi kotaniza ulastiniz.\n"
                                f"Kotaniz yarin saat 00:00'da sifirlanacaktir.\n\n"
                                f"Limitsiz gonderim ve VIP ozellikler icin paketlerimizi inceleyebilirsiniz.",
                                buttons=[[Button.inline("VIP Paketleri Incele", b"menu_vip")]]
                            )
                        except Exception:
                            pass
                    continue
                elif is_vip and user.get("quota_notified"):
                    user["quota_notified"] = False
                    changed = True

                interval_secs = max(30, user.get("ad_interval", 60)) * 60
                last_sent = user.get("last_sent_at", 0)
                if last_sent > 0 and (now - last_sent < interval_secs):
                    continue

                cat_key = user.get("target_category", "sohbet")
                if cat_key == "custom":
                    target_groups = user.get("custom_groups", [])
                else:
                    cat_info = DEFAULT_CATEGORIES.get(cat_key, DEFAULT_CATEGORIES.get("sohbet", {}))
                    target_groups = cat_info.get("groups", [])

                if not target_groups:
                    continue

                msg_list = user.get("ad_messages", [])
                msg_text = msg_list[0] if msg_list else "Selamlar herkese, iyi gunler"

                u_client = None
                try:
                    u_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                    await u_client.connect()

                    if not await u_client.is_user_authorized():
                        logger.error(f"[AdEngine] Kullanici {uid} oturumu gecersiz/sonlanmis.")
                        user["is_running"] = False
                        user["last_error"] = "Oturum suresi dolmus veya gecersiz."
                        changed = True
                        continue

                    send_success = False
                    attempts = min(3, len(target_groups))

                    for _ in range(attempts):
                        group_idx = user.get("current_group_idx", 0) % len(target_groups)
                        raw_target = target_groups[group_idx]
                        user["current_group_idx"] = (group_idx + 1) % len(target_groups)

                        target_group = raw_target.replace("https://t.me/", "").replace("t.me/", "").replace("@", "").strip()
                        if not target_group:
                            continue

                        logger.info(f"[AdEngine] Kullanici {uid} ({user.get('account_name')}) -> @{target_group} hedefine gonderiliyor...")

                        try:
                            entity = await u_client.get_entity(target_group)
                        except Exception as get_err:
                            logger.warning(f"[AdEngine] @{target_group} cozulemedi: {get_err}")
                            continue

                        if getattr(entity, "broadcast", False):
                            logger.info(f"[AdEngine] @{target_group} duyuru kanalidir. Siradakine geciliyor.")
                            continue

                        is_member = getattr(entity, "left", False) is False
                        if not is_member:
                            try:
                                await u_client(functions.channels.JoinChannelRequest(channel=entity))
                                logger.info(f"[AdEngine] @{target_group} grubuna basariyla katilindi.")
                                await asyncio.sleep(2.0)
                            except UserAlreadyParticipantError:
                                pass
                            except InviteRequestSentError:
                                continue
                            except (ChannelPrivateError, ChatWriteForbiddenError):
                                continue
                            except FloodWaitError as fwe:
                                user["last_sent_at"] = now + fwe.seconds
                                changed = True
                                break
                            except Exception:
                                continue

                        try:
                            await u_client.send_message(entity, msg_text)
                            user["last_sent_at"] = now
                            user["total_sent"] = user.get("total_sent", 0) + 1
                            user["daily_sent"] = user.get("daily_sent", 0) + 1
                            user["last_sent_group"] = target_group
                            changed = True
                            send_success = True
                            logger.info(f"[AdEngine] Kullanici {uid} basariyla mesaj gonderdi: @{target_group} (Toplam: {user['total_sent']})")

                            try:
                                mins_interval = user.get("ad_interval", 60)
                                notify_text = (
                                    f"**[Oto-Mesaj Motoru] Mesaj Basariyla Iletildi**\n"
                                    f"{LINE}\n\n"
                                    f"Hedef Grup: `@{target_group}`\n"
                                    f"Toplam Gonderi: `{user['total_sent']}` adet\n"
                                    f"Sonraki Gonderim: `{mins_interval}` dakika sonra\n\n"
                                    f"Iletilen Mesaj:\n"
                                    f"```\n{msg_text}\n```\n\n"
                                    f"{LINE}"
                                )
                                await client.send_message(int(uid), notify_text)
                            except Exception:
                                pass

                            break

                        except (ChatWriteForbiddenError, ChatSendPlainForbiddenError):
                            continue
                        except SlowModeWaitError:
                            continue
                        except FloodWaitError as fwe:
                            user["last_sent_at"] = now + fwe.seconds
                            changed = True
                            break

                    if not send_success and not user.get("last_sent_at"):
                        user["last_sent_at"] = now - interval_secs + 120
                        changed = True

                except FloodWaitError as fwe:
                    user["last_sent_at"] = now + fwe.seconds
                    changed = True
                except Exception as cli_err:
                    logger.warning(f"[AdEngine] Oturum hatasi ({uid}): {cli_err}")
                finally:
                    if u_client:
                        try:
                            await u_client.disconnect()
                        except Exception:
                            pass

            if changed:
                save_data(users)

        except Exception as e:
            logger.error(f"[AdEngine] Arka plan dongu hatasi: {e}")

        await asyncio.sleep(15)

# -------------------------------------------------------------
# Bot Starter and Main Entrypoint
# -------------------------------------------------------------
async def start_with_retry():
    while True:
        try:
            write_bot_status("jarvis", state="connecting", telegram_ready=False, token=BOT_TOKEN)
            logger.info("JarvisCraft Botu baglaniyor...")
            await client.start(bot_token=BOT_TOKEN)
            me = await client.get_me()
            write_bot_status(
                "jarvis",
                state="ready",
                telegram_ready=True,
                token=BOT_TOKEN,
                bot_username=getattr(me, "username", None),
                connected=True,
            )
            logger.info("JarvisCraft Botu BASARIYLA BAGLANDI!")

            asyncio.create_task(ad_engine_background_worker())

            while True:
                await asyncio.sleep(30)
                if not client.is_connected():
                    logger.warning("JarvisCraft Bot baglantisi koptu, yeniden baglaniyor...")
                    break
        except Exception as e:
            msg = str(e)
            if invalid_token_error(msg):
                write_bot_status("jarvis", state="invalid_token", telegram_ready=False, token=BOT_TOKEN, last_error=msg)
                logger.error(f"Gecersiz bot tokeni: {e}")
                return
            write_bot_status("jarvis", state="error", telegram_ready=False, token=BOT_TOKEN, last_error=msg)
            logger.error(f"JarvisCraft bot calisma hatasi: {e}. 10 saniye icinde tekrar denenecek...")
            await asyncio.sleep(10)

def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_with_retry())
    except KeyboardInterrupt:
        logger.info("JarvisCraft Bot manuel olarak kapatildi.")
        write_bot_status("jarvis", state="stopped", telegram_ready=False, token=BOT_TOKEN)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        write_bot_status("jarvis", state="error", telegram_ready=False, token=BOT_TOKEN, last_error=str(e))

if __name__ == "__main__":
    main()
