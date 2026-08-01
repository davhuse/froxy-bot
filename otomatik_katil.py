import asyncio
from datetime import datetime, timezone, timedelta
import random
import os
import json
import re
import requests
import sys
import shutil

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
from gemini_helper import get_ai_response, get_ad_variation
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest, SearchRequest
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, UsernameNotOccupiedError, 
    UsernameInvalidError, ChannelPrivateError, ChatWriteForbiddenError,
    SlowModeWaitError, UserBannedInChannelError, PeerFloodError,
    UserRestrictedError
)

# --- AYARLAR ---
api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
SESSION_NAME = 'c4hex_session' # Masaüstündeki hazır oturumu kullan

import builtins
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    builtins.print(*args, **kwargs)

gruplar = [
    # Kullanıcının onayladığı hedef gruplar (12 Haziran 2026 güncellemesi)
    "TicaretGrubuuu",
    "kuponindirimsatis",
    "zeroticaret",
    "tahaaslan11",
    "casinox_grup",
    "alimsatimmerkezii",
    "reklamreferans",
    "sosyalmedyaalimsatimticaret",
    "kuponsatisgrup",
    "kuponcekkodsatis",
    "referanslinkpaylasimigrup",
    "kuponsatislari0",
    "YuceKuponSatis",
    "letgoilanlari",
    "-1001572316417",  # Serbest Ticaret Grubu (1515 üye)
    "-3608209943",     # DERGAH (1582 üye)
    "ticar4t",
    "kuponhesapsatis",
    "kuponvekodsatisgrubu",
    "indirimkodusatis",
    "mukyemek",
    "kupongrupta",
    "kuponkodindirimilanlar",
    "Kuponcekm",
]


def _hedef_listesini_dosyadan_genislet():
    """gruplar.txt icerigini hedef listesine ekler.

    Dosya yillardir duruyordu ama uretim kodu onu hic okumuyordu: hedef listesi
    yalnizca yukaridaki sabit liste idi.  Dosyaya grup eklemek/cikarmak hicbir
    sey degistirmiyordu, ki bu sessizce yanlis sonuc veren bir tuzak.  Artik
    dosya da okunuyor; sabit liste ile birlestiriliyor.
    """
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gruplar.txt')
    if not os.path.exists(yol):
        return
    mevcut = {str(g).lower().lstrip('@') for g in gruplar}
    eklenen = []
    try:
        with open(yol, 'r', encoding='utf-8') as f:
            for satir in f:
                ad = satir.strip().lstrip('@')
                if not ad or ad.startswith('#'):
                    continue
                if ad.lower() not in mevcut:
                    gruplar.append(ad)
                    mevcut.add(ad.lower())
                    eklenen.append(ad)
    except Exception as e:
        print(f"⚠️ gruplar.txt okunamadı: {e}")
        return
    if eklenen:
        print(f"📄 gruplar.txt'den {len(eklenen)} hedef eklendi: {', '.join(eklenen)}")


_hedef_listesini_dosyadan_genislet()

# @Nightsatis (-1003336542169) korumali listeden cikarildi: KeyVadi ve Froxy
# orada banli, korumali kaldigi surece bot her tur mesaj deneyip ban hatasi
# aliyor, kara listeye de ekleyemiyor, gruptan da cikamiyordu.
PROTECTED_GROUP_ALIASES = {}

# Kullanıcı tarafından katılım talebi geri çekilen gruplar. Bu gruplar yeni
# katılım kuyruğuna tekrar alınmaz. Hesap zaten üyeyse reklam hedefi olmaya
# devam eder; yalnızca bekleyen talep geri çekilir.
CANCELLED_JOIN_REQUESTS = {"kuponceking"}

# Uyeliginden cikilacak gruplar.  Ban yedigimiz bir grupta uye kalmaya devam
# etmek, yoneticiler hesabi tekrar fark ettiginde ikinci bir bana yol aciyor.
# Calisma basina bir kez islenir.
GROUPS_TO_LEAVE = {
    "kuponsatimalim",
    # Kullanicinin reklami kestigi ve uyelikten de cikilmasini istedigi gruplar
    "ticaretsaha",
    "ilanticaret",
    "referansreklam1",
    "reklamvereferanss",
    "sanalalimsatimticaret",
    "nightsatis",
}

def normalize_group_key(grup_name):
    g_lower = str(grup_name or '').lower().replace('@', '').strip()
    g_lower = g_lower.rstrip('/')
    if '/' in g_lower:
        g_lower = g_lower.split('/')[-1]
    return g_lower

def get_all_protected_groups():
    protected = {normalize_group_key(g) for g in gruplar}
    for key, value in PROTECTED_GROUP_ALIASES.items():
        protected.add(normalize_group_key(key))
        protected.add(normalize_group_key(value))
    return protected

def is_group_protected(grup_name):
    g_lower = normalize_group_key(grup_name)
    protected = get_all_protected_groups()
    alias = PROTECTED_GROUP_ALIASES.get(g_lower)
    return g_lower in protected or (alias and normalize_group_key(alias) in protected)

async def cancel_pending_join_request(client, client_name, joined_dialogs, group_username):
    """Üye olmayan hesap için bekleyen Telegram katılım isteğini geri çeker."""
    group_key = normalize_group_key(group_username)
    if group_key in joined_dialogs:
        print(f"[{client_name}] ℹ️ @{group_key} hesabın zaten üye olduğu grup; katılım talebi iptali uygulanmadı.")
        return False
    try:
        entity = await client.get_entity(group_key)
        await client(LeaveChannelRequest(entity))
        print(f"[{client_name}] ✅ @{group_key} bekleyen katılım talebi iptal edildi.")
        return True
    except Exception as exc:
        # İstek daha önce iptal edilmişse veya hiç oluşmamışsa döngüyü bozma.
        print(f"[{client_name}] ℹ️ @{group_key} için iptal gerekmiyor/uygulanamadı: {type(exc).__name__}")
        return False

STATS_FILE = 'stats.json'
AD_ACCOUNT_STATUS_FILE = 'ad_account_status.json'

def update_ad_account_status(client_name, **fields):
    """Persist a small, non-sensitive delivery heartbeat for the status page."""
    from datetime import datetime, timezone
    try:
        state = {}
        if os.path.exists(AD_ACCOUNT_STATUS_FILE):
            with open(AD_ACCOUNT_STATUS_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        record = state.get(client_name, {})
        record.update(fields)
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        state[client_name] = record
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', client_name)
        tmp_file = f'{AD_ACCOUNT_STATUS_FILE}.{os.getpid()}.{safe_name}.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, AD_ACCOUNT_STATUS_FILE)
    except Exception as exc:
        print(f"[{client_name}] Ad-status heartbeat failed: {type(exc).__name__}")

def update_stats(sent=0, discovered=0, blacklisted=0, active=0):
    try:
        import os, json
        stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                try:
                    stats = json.load(f)
                except:
                    pass
        
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        if stats.get("last_reset") != today:
            stats["last_reset"] = today
            stats["messages_sent_today"] = 0
            stats["auto_discovered"] = 0
            
        stats["messages_sent_today"] = stats.get("messages_sent_today", 0) + sent
        stats["auto_discovered"] = stats.get("auto_discovered", 0) + discovered
        if blacklisted > 0: stats["blacklisted_total"] = blacklisted
        if active > 0: stats["active_groups"] = active
        
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        print(f"⚠️ Stat güncelleme hatası: {e}")

def parse_spintax(text):
    import random, re
    def replace(match):
        options = match.group(1).split('|')
        return random.choice(options)
    return re.sub(r'\{([^\{\}]*)\}', replace, text)

SHORT_AD_GROUP_USERNAMES = {'ilanticaret'}
SHORT_AD_GROUP_TITLES = {'ticaret ve ilan grubu - sanal'}
SPYFORUM_GROUP_MARKER = 'spyforum'
EXCLUDED_REFERENCE_CHANNELS = {"froxyreferans", "keyvadireferans", "lisansarenareferans"}
EXCLUDED_REFERENCE_CHAT_IDS = {3982754573, 4401324614, 4316589940}
# Reklam gonderilmeyecek gruplar.  Bu liste bilerek KOD icinde tutuluyor:
# blacklist.txt her acilista ve her 5 dakikada bir Firestore'daki surumle
# eziliyor, dolayisiyla dosyaya yazilan haric tutmalar kalici olmuyor.
# Buradaki kayitlara hicbir senkron dokunamaz.
MANUALLY_EXCLUDED_AD_GROUPS = {
    "ticaretforumofficial",
    "illegalalimsatimerkezi",
    "sultanbeyliikinciel0",
    "reklamonliene",
    "referansreklamyardimlasma",
    # Kullanicinin 26 Temmuz 2026'da kesilmesini istedigi gruplar
    "ilanticaret",
    "referansreklam1",
    "reklamvereferanss",
    "sanalalimsatimticaret",
    "ticaretsaha",
    # Ban yendigi icin uyelikten de cikilan gruplar.  Telegram
    # UserBannedInChannel dondurdugu halde @Nightsatis korumali listede
    # oldugu icin ne kara listeye alinabiliyor ne de terk edilebiliyordu;
    # bot her tur banli gruba mesaj denemeye devam ediyordu.
    "kuponsatimalim",
    "nightsatis",
    "-1003336542169",
}
TICARET_FORUM_MAX_CHARS = 700
TICARET_FORUM_FALLBACKS = {
    'keyvadi': (
        "\u2b50 KEYVADI DIJITAL URUNLER\n"
        "Canva, Netflix, YouTube, Adobe, yapay zeka ve oyun urunlerinde hizli teslimat.\n\n"
        "One cikanlar: Canva Pro 1 Yil | YouTube Premium | Netflix 4K | Gemini Pro | Steam Key\n\n"
        "Siparis ve guncel fiyatlar: @KeyVadiSatisBot"
    ),
    'lisansarena': (
        "\u2728 LISANSARENA DIJITAL HIZMETLER\n"
        "Premium hesap, lisans ve dijital urunlerde hizli teslimat.\n\n"
        "One cikanlar: Canva | Office 365 | Windows 11 | YouTube Premium | Netflix 4K | Gemini Pro\n\n"
        "Siparis ve guncel fiyatlar: @LisansArenaBot"
    ),
    'froxy': (
        "FROXY AI | Telegram otomatik reklam sistemi\n"
        "Guvenli altyapi, bot kurulumu ve 7/24 destek.\n\n"
        "Detay ve fiyat icin: @FroxyDestekBOT"
    ),
}


def _normalize_group_identifier(value):
    return str(value or '').strip().lower().lstrip('@')


def is_short_ad_group(grup_name, entity=None):
    """Kisa reklam sablonu kullanacak grubu username veya tam basliktan ayirt et."""
    identifiers = [_normalize_group_identifier(grup_name)]
    title = ''
    if entity is not None:
        identifiers.append(_normalize_group_identifier(getattr(entity, 'username', '')))
        title = _normalize_group_identifier(getattr(entity, 'title', ''))

    if any(item in SHORT_AD_GROUP_USERNAMES for item in identifiers):
        return True
    return title in SHORT_AD_GROUP_TITLES


def is_spyforum_group(grup_name, entity=None):
    """SpyForum'u username veya basliktan ayirt et."""
    values = [grup_name]
    if entity is not None:
        values.extend((getattr(entity, 'username', ''), getattr(entity, 'title', '')))
    for value in values:
        compact = re.sub(r'[^a-z0-9]', '', _normalize_group_identifier(value))
        if SPYFORUM_GROUP_MARKER in compact:
            return True
    return False


def account_brand(client_name):
    name = (client_name or '').lower()
    if 'lisans' in name or name in {'hesap #3', 'hesap #5'}:
        return 'lisansarena'
    if 'froxy' in name or name in {'hesap #1', 'yerel hesap'}:
        return 'froxy'
    return 'keyvadi'


def account_flags(client_name):
    brand = account_brand(client_name)
    return brand == 'keyvadi', brand == 'lisansarena', brand == 'froxy'


def short_group_message(is_keyvadi, is_lisansarena, is_froxy=False):
    brand = 'froxy' if is_froxy else ('lisansarena' if is_lisansarena else 'keyvadi')
    filename = f'message_ticaret_{brand}_short.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as template_file:
            message = template_file.read().strip()
    except OSError:
        message = TICARET_FORUM_FALLBACKS[brand]

    # Bu grupta tek, sade metin kullanilir; uzun bir dosya yanlislikla
    # yerlestirilse dahi reklam blogu veya banner ile gonderilmez.
    return message if 0 < len(message) <= TICARET_FORUM_MAX_CHARS else TICARET_FORUM_FALLBACKS[brand]


def process_marketing_features(msg, is_keyvadi, is_lisansarena, is_short=False):
    msg = msg.strip()
    if is_short:
        return msg

    # Şablonlar artık tek bir ürün ihtiyacına odaklanıyor. Her mesaja aynı
    # uzun "günün fırsatları" bloğunu eklemek fiyat çelişkisi yaratıyor ve
    # reklamı spam/katalog görünümüne sokuyordu; burada yalnızca CTA garanti edilir.

    if is_keyvadi:
        bot_uname = "@KeyVadiSatisBot"
        if bot_uname not in msg:
            msg += f"\n\n🤖 **Hızlı Sipariş & Canlı Destek Botumuz:** {bot_uname}"
    elif is_lisansarena:
        bot_uname = "@LisansArenaBot"
        if bot_uname not in msg:
            msg += f"\n\n🤖 **Hızlı Sipariş & Canlı Destek Botumuz:** {bot_uname}"
    else:
        bot_uname = "@FroxyDestekBOT"
        if bot_uname not in msg:
            msg += f"\n\n🤖 **Yapay Zeka Platformu Botumuz:** {bot_uname}"
    return msg



PROGRESS_FILE = 'progress.txt'
BLACKLIST_FILE = 'blacklist.txt'
BLACKLIST_META_FILE = 'blacklist_meta.json'
BLACKLIST_MIGRATION_MARKER = 'blacklist_migration_v2.done'
AUTO_GROUPS_FILE = 'auto_groups.txt'
MESSAGES_DIR = 'messages'
MSG_HISTORY_FILE = 'msg_history.json'
COOLDOWN_FILE = 'group_cooldown.json'
ACCOUNT_RESTRICTIONS_FILE = 'account_restrictions.json'
GROUP_FAILURES_FILE = 'group_failures.json'
SEND_LOCK_FILE = 'send_locks.json'
GROUP_COOLDOWN_HOURS = 1  # Varsayılan: 1 saat ortak cooldown. Config'den ezilebilir.
# Ayni gruba iki FARKLI hesabin gonderimi arasinda birakilacak en az sure.
# Cooldown hesap bazli oldugu icin bu olmadan uc hesap ayni gruba saniyeler
# icinde ust uste reklam birakiyordu.
INTER_ACCOUNT_GAP_SECONDS = 60
if os.path.exists("bot_config.json"):
    try:
        with open("bot_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            GROUP_COOLDOWN_HOURS = cfg.get("group_cooldown_hours", 1)
    except:
        pass

NEGATIVE_KEYWORDS = [
    "sigara", "vape", "puff", "tütün", "likit", "shisha", "nargile", "elektronik sigara", "elektroniksigara",
    "ayakkabı", "ayakkabi", "giyim", "butik", "moda", "elbise", "çanta", "canta",
    "brawl", "pubg", "valorant", "clash", "roblox", "free fire", "mobile legends", "metin2", "knight online",
    "korg", "pa800", "pa2x", "pa600", "pa900", "orgcu", "müzik", "muzik", "enstrüman",
    "gürcistan", "gurcistan", "batum", "tiflisi",
    "escort", "sex", "porno", "ifşa", "ifsa", "adult", "travesti",
    "film", "dizi", "izle", "sinema", "warez",
    "bahis", "iddaa", "casino", "kumar", "rulet", "bet", "kazan", "tahmin",
    "araba", "oto", "motor", "vasıta", "toptan", "tekstil", "diş", "hekim", "medikal", 
    "kitap", "ders", "gayrimenkul", "emlak", "ev", "daire", "kiralık", "arazi", "arsa",
    "telefon", "cihaz", "parça", "donanım", "pc"
]

# --- Auto-DM: Yanıt veren kullanıcıları takip et ---
replied_users = set()
PENDING_INVITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pending_invites.json')

def load_pending_invites():
    if os.path.exists(PENDING_INVITES_FILE):
        try:
            with open(PENDING_INVITES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass
    return set()

def save_pending_invites(data):
    try:
        _atomik_json_yaz(PENDING_INVITES_FILE, sorted(list(data)), indent=2)
    except Exception as e:
        print(f"⚠️ pending_invites kaydetme hatası: {e}")

pending_invites = load_pending_invites()
dm_count_today = 0
dm_last_reset = ""
MAX_DM_PER_DAY = 20
# Reklam gonderebilecek tek hesaplar. Kullanici adi ilk kilit, bilinen
# hesaplarda telefon ikinci kilittir. Eski KeyVadiOnline/User/Uzer hesaplari
# burada bilerek yer almaz; gecmis cooldown rumuzlari yetki vermez.
ACTIVE_ACCOUNT_IDENTITIES = {
    'froxy_ai': {
        'stable_name': 'FroxyOnline',
        'phone': '905015291021',
        'user_id': 8797763469,
        'slot': 1,
    },
    'keyvadidestek': {
        'stable_name': 'KeyVadiOnline',
        'phone': '905056798875',
        'user_id': 6196006704,
        'slot': 2,
    },
    'lisansarenaonline': {
        'stable_name': 'LisansArenaOnline',
        # Verilen telefon mevcut Telegram oturumuyla uyusmadi. Dogrulanmis,
        # degismez Telegram ID + kullanici adi birlikte kullaniliyor.
        'phone': None,
        'user_id': 8879941384,
        'slot': 3,
    },
}
ACTIVE_ACCOUNT_USERNAMES = set(ACTIVE_ACCOUNT_IDENTITIES)
ACCOUNT_STABLE_NAMES = {
    username: identity['stable_name']
    for username, identity in ACTIVE_ACCOUNT_IDENTITIES.items()
}


def normalize_phone(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())

# --- Auto-DM: Anahtar kelimeler ---
DM_TRIGGER_KEYWORDS = [
    "yapay zeka", "chatgpt", "claude", "gemini", "ai ", " ai",
    "gpt", "deepseek", "canva", "adobe", "lisans", "premium hesap",
    "kupon", "indirim", "trendyol", "capcut",
]

SALES_INTENT_KEYWORDS = {
    "fiyat", "ücret", "tl", "satın", "almak", "alacağım", "sipariş",
    "ürün", "stok", "link", "shopier", "ödeme", "ödemek", "kampanya",
    "indirim", "premium", "lisans", "hesap", "abonelik", "paket", "üyelik",
    "canva", "adobe", "netflix", "youtube", "spotify", "capcut", "chatgpt",
    "var mı", "mevcut mu", "nasıl alırım", "satın al",
}

EXPLICIT_SALES_INTENT_KEYWORDS = {
    "fiyat", "ücret", "tl", "kaç para", "ne kadar", "satın", "almak",
    "alacağım", "sipariş", "stok", "link", "shopier", "ödeme", "ödemek",
    "kampanya", "indirim", "var mı", "mevcut mu", "nasıl alırım", "satın al",
}

NON_SALES_DM_PATTERNS = (
    "selam", "slm", "merhaba", "günaydın", "iyi geceler", "teşekkür",
    "sağ ol", "islam", "islami", "allah", "dua", "amin", "hayırlı",
)

def has_sales_intent(text):
    normalized = (text or "").strip().lower()
    return bool(normalized) and any(
        re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", normalized)
        for keyword in SALES_INTENT_KEYWORDS
    )

def has_explicit_sales_intent(text):
    normalized = (text or "").strip().lower()
    return bool(normalized) and any(
        re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", normalized)
        for keyword in EXPLICIT_SALES_INTENT_KEYWORDS
    )

def is_obviously_non_sales_dm(text):
    normalized = (text or "").strip().lower()
    if not normalized:
        return True
    words = re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", normalized)
    if len(words) <= 2 and any(word in NON_SALES_DM_PATTERNS for word in words):
        return True
    return any(pattern in normalized for pattern in NON_SALES_DM_PATTERNS if pattern in {"islam", "islami", "allah", "dua", "amin"})

# --- Grup Cooldown Sistemi ---
def load_cooldowns():
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def _atomik_json_yaz(path, data, **dump_kwargs):
    """Once gecici dosyaya yaz, sonra yerine tasi.

    'w' modu dosyayi ANINDA sifirliyor; Render deploy sirasinda SIGTERM ya da
    OOM tam json.dump ortasinda gelirse dosya yarim/bos kaliyor ve bir sonraki
    aciliste sessizce {} olarak okunuyordu -- tum cooldown gecmisi silinip
    buluta da bos hali yaziliyordu.  os.replace ayni dosya sisteminde atomik.
    """
    gecici = f"{path}.tmp"
    try:
        with open(gecici, 'w', encoding='utf-8') as f:
            json.dump(data, f, **dump_kwargs)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, path)
        return True
    except Exception as e:
        print(f"⚠️ {path} yazılamadı: {e}")
        try:
            if os.path.exists(gecici):
                os.remove(gecici)
        except Exception:
            pass
        return False


def save_cooldowns(data):
    _atomik_json_yaz(COOLDOWN_FILE, data, indent=2)

def _numeric_chat_key(value):
    """'-1001693128625', '1693128625' -> '1693128625'.

    Ayni grup diyalog kimligi (-100 onekli) ve entity.id (onek siz) olmak uzere
    iki farkli bicimde karsimiza cikiyor.  Durum kayitlarinin ayni gruba iki ayri
    anahtarla yazilmamasi icin ikisini tek bicime indiriyoruz.
    """
    text = str(value or '').strip()
    negative = text.startswith('-')
    digits = text.lstrip('-')
    if not digits.isdigit():
        return ''
    if negative and digits.startswith('100') and len(digits) >= 12:
        digits = digits[3:]
    return digits


def group_state_keys(grup_name, entity=None):
    """Bir grubun durum anahtarlari; ilki kanonik, kalanlar eski kayitlar icin.

    Yazma islemleri her zaman ilk anahtari kullanir, okuma islemleri listenin
    tamamina bakar.  Boylece diskteki eski isim/ID anahtarli kayitlar gecerli
    kalir ve zamanla kendiliginden tek bicime doner.
    """
    keys = []

    def ekle(value):
        if value and value not in keys:
            keys.append(value)

    numeric = ''
    if entity is not None:
        numeric = _numeric_chat_key(getattr(entity, 'id', None))
    if not numeric:
        numeric = _numeric_chat_key(grup_name)
    if numeric:
        ekle('id:' + numeric)

    name_key = normalize_group_key(grup_name)
    ekle(normalize_group_key(PROTECTED_GROUP_ALIASES.get(name_key, name_key)))

    if entity is not None:
        uname = normalize_group_key(getattr(entity, 'username', '') or '')
        if uname:
            ekle(normalize_group_key(PROTECTED_GROUP_ALIASES.get(uname, uname)))
        chat_id = getattr(entity, 'id', None)
        if chat_id is not None:
            ekle(str(chat_id))

    # Eski kayitlar diyalog kimligini '-100' onekiyle tutuyordu; okuma
    # sirasinda o bicimi de aday olarak degerlendir.
    if numeric:
        ekle(numeric)
        ekle('-100' + numeric)

    return keys or [normalize_group_key(grup_name)]


def cooldown_key(grup_name, entity=None):
    return group_state_keys(grup_name, entity)[0]


def target_dedupe_key(group_name, entity=None):
    return group_state_keys(group_name, entity)[0]


def is_reference_channel(group_name, entity=None):
    """Recognize referral channels by username or Telegram chat ID."""
    identifiers = {normalize_group_key(group_name)}
    if entity is not None:
        identifiers.add(normalize_group_key(getattr(entity, 'username', '')))
        chat_id = getattr(entity, 'id', None)
        if chat_id is not None:
            try:
                if abs(int(chat_id)) in EXCLUDED_REFERENCE_CHAT_IDS:
                    return True
            except (TypeError, ValueError):
                pass

    for identifier in identifiers:
        if identifier in EXCLUDED_REFERENCE_CHANNELS:
            return True
        numeric = identifier.removeprefix('-100').lstrip('-')
        if numeric.isdigit() and int(numeric) in EXCLUDED_REFERENCE_CHAT_IDS:
            return True
    return False


def is_excluded_ad_target(group_name, entity=None):
    if is_reference_channel(group_name, entity):
        return True
    identifiers = {normalize_group_key(group_name)}
    if entity is not None:
        identifiers.add(normalize_group_key(getattr(entity, 'username', '')))
    return bool(identifiers.intersection(MANUALLY_EXCLUDED_AD_GROUPS))

def _load_json_file(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                value = json.load(f)
                return value if isinstance(value, type(default)) else default
    except Exception:
        pass
    return default

def _save_json_file(path, data):
    return _atomik_json_yaz(path, data, indent=2, ensure_ascii=False)

def load_account_restrictions():
    return _load_json_file(ACCOUNT_RESTRICTIONS_FILE, {})

VALID_RESTRICTION_SCOPES = {'send', 'join', 'discover', 'account'}

def _parse_utc_datetime(value):
    from datetime import datetime, timezone
    try:
        expires = datetime.fromisoformat(value)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires
    except Exception:
        return None

def _infer_restriction_scope(record):
    scope = (record or {}).get('scope')
    if scope in VALID_RESTRICTION_SCOPES:
        return scope
    reason = f"{(record or {}).get('reason', '')} {(record or {}).get('error_type', '')}".lower()
    if any(token in reason for token in ('discover', 'scraper', 'search', 'kesfi', 'keşfi', 'keÅŸfi', 'arama')):
        return 'discover'
    if any(token in reason for token in ('join', 'katilim', 'katılım', 'katÄ±lÄ±m')):
        return 'join'
    return 'send'

def _restriction_items(state):
    if not isinstance(state, dict):
        return []
    scopes = state.get('scopes')
    items = []
    if isinstance(scopes, dict):
        for scope, record in scopes.items():
            if isinstance(record, dict):
                normalized = dict(record)
                normalized['scope'] = normalized.get('scope') or scope
                items.append((normalized['scope'], normalized))
    elif state.get('until'):
        scope = _infer_restriction_scope(state)
        normalized = dict(state)
        normalized['scope'] = scope
        items.append((scope, normalized))
    return items

def _restriction_applies(record_scope, requested_scope):
    if record_scope == 'account':
        return True
    return record_scope == requested_scope

def _cleanup_account_restrictions(client_name=None):
    from datetime import datetime, timezone
    restrictions = load_account_restrictions()
    changed = False
    names = [client_name] if client_name else list(restrictions.keys())
    for name in names:
        state = restrictions.get(name, {})
        active_scopes = {}
        for scope, record in _restriction_items(state):
            expires = _parse_utc_datetime(record.get('until'))
            if not expires or datetime.now(timezone.utc) >= expires:
                changed = True
                continue
            scope = scope if scope in VALID_RESTRICTION_SCOPES else _infer_restriction_scope(record)
            record = dict(record)
            record['scope'] = scope
            active_scopes[scope] = record
        if active_scopes:
            restrictions[name] = {'scopes': active_scopes}
            if state != restrictions[name]:
                changed = True
        elif name in restrictions:
            restrictions.pop(name, None)
            changed = True
    if changed:
        _save_json_file(ACCOUNT_RESTRICTIONS_FILE, restrictions)
    return restrictions

def is_account_restricted(client_name, scope='send'):
    restrictions = _cleanup_account_restrictions(client_name)
    state = restrictions.get(client_name, {})
    for record_scope, _record in _restriction_items(state):
        if _restriction_applies(record_scope, scope):
            return True
    return False

def set_account_restriction(client_name, seconds, reason, error_type=None, scope='send'):
    from datetime import datetime, timedelta, timezone
    seconds = max(1, int(seconds or 1))
    scope = scope if scope in VALID_RESTRICTION_SCOPES else 'send'
    restrictions = _cleanup_account_restrictions(client_name)
    state = restrictions.get(client_name, {})
    scopes = {}
    for existing_scope, record in _restriction_items(state):
        if existing_scope in VALID_RESTRICTION_SCOPES:
            scopes[existing_scope] = record
    now = datetime.now(timezone.utc)
    scopes[scope] = {
        'until': (now + timedelta(seconds=seconds)).isoformat(),
        'reason': reason,
        'error_type': error_type or reason,
        'scope': scope,
        'updated_at': now.isoformat()
    }
    restrictions[client_name] = {'scopes': scopes}
    _save_json_file(ACCOUNT_RESTRICTIONS_FILE, restrictions)

def account_restriction_status(client_name, scope=None):
    state = _cleanup_account_restrictions(client_name).get(client_name, {})
    if not scope:
        return state
    for record_scope, record in _restriction_items(state):
        if _restriction_applies(record_scope, scope):
            return record
    return {}

def claim_send_lock(grup_name, client_name, ttl_seconds=1800, entity=None):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    locks = _load_json_file(SEND_LOCK_FILE, {})
    for key, state in list(locks.items()):
        expires = _parse_utc_datetime((state or {}).get('until')) if isinstance(state, dict) else None
        if not expires or now >= expires:
            locks.pop(key, None)
    group_key = cooldown_key(grup_name, entity)
    lock_key = f"{client_name}:{group_key}"
    group_lock_key = f"group:{group_key}"
    current = locks.get(lock_key, {})
    current_until = _parse_utc_datetime(current.get('until')) if isinstance(current, dict) else None
    if current_until and now < current_until:
        return False
    group_current = locks.get(group_lock_key, {})
    group_current_until = _parse_utc_datetime(group_current.get('until')) if isinstance(group_current, dict) else None
    if group_current_until and now < group_current_until:
        return False
    locks[lock_key] = {
        'until': (now + timedelta(seconds=max(1, int(ttl_seconds)))).isoformat(),
        'updated_at': now.isoformat()
    }
    locks[group_lock_key] = {
        'until': (now + timedelta(seconds=max(1, int(ttl_seconds)))).isoformat(),
        'updated_at': now.isoformat(),
        'client': client_name
    }
    _save_json_file(SEND_LOCK_FILE, locks)
    return True

def release_send_lock(grup_name, client_name, entity=None):
    locks = _load_json_file(SEND_LOCK_FILE, {})
    changed = False
    # Kanonik anahtarin yani sira eski bicimli kilitleri de birak.
    for group_key in set(group_state_keys(grup_name, entity)) | {grup_name.lower()}:
        for key in (f"{client_name}:{group_key}", f"group:{group_key}"):
            if key in locks:
                locks.pop(key, None)
                changed = True
    if changed:
        _save_json_file(SEND_LOCK_FILE, locks)

def record_group_failure(grup_name, client_name, reason, retry_after=300, entity=None):
    """Temporary per-account/group retry state; never writes BLACKLIST_FILE."""
    from datetime import datetime, timedelta, timezone
    failures = _load_json_file(GROUP_FAILURES_FILE, {})
    key = cooldown_key(grup_name, entity)
    failures.setdefault(key, {})[client_name] = {
        'reason': reason,
        'retry_at': (datetime.now(timezone.utc) + timedelta(seconds=max(1, int(retry_after)))).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    _save_json_file(GROUP_FAILURES_FILE, failures)

def is_group_retry_blocked(grup_name, client_name, entity=None):
    from datetime import datetime, timezone
    failures = _load_json_file(GROUP_FAILURES_FILE, {})
    now = datetime.now(timezone.utc)
    for key in group_state_keys(grup_name, entity):
        state = failures.get(key, {}).get(client_name, {})
        retry_at = state.get('retry_at') if isinstance(state, dict) else None
        if not retry_at:
            continue
        try:
            if now < datetime.fromisoformat(retry_at):
                return True
        except Exception:
            continue
    return False

def clear_group_failure(grup_name, client_name, entity=None):
    failures = _load_json_file(GROUP_FAILURES_FILE, {})
    changed = False
    for key in group_state_keys(grup_name, entity):
        group_state = failures.get(key, {})
        if client_name in group_state:
            group_state.pop(client_name, None)
            if group_state:
                failures[key] = group_state
            else:
                failures.pop(key, None)
            changed = True
    if changed:
        _save_json_file(GROUP_FAILURES_FILE, failures)

def blacklist_group(grup_name, reason, client_name):
    """Persist a confirmed group-level blacklist with an auditable reason."""
    from datetime import datetime, timezone
    save_to_list(grup_name, BLACKLIST_FILE)
    metadata = _load_json_file(BLACKLIST_META_FILE, {})
    metadata[grup_name.lower()] = {
        'reason': reason,
        'client': client_name,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    _save_json_file(BLACKLIST_META_FILE, metadata)

def migrate_legacy_blacklist_once():
    """Back up legacy blacklist decisions and retain only approved groups."""
    if os.path.exists(BLACKLIST_MIGRATION_MARKER) or not os.path.exists(BLACKLIST_FILE):
        return False
    try:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = f'blacklist_legacy_backup_{stamp}.txt'
        shutil.copy2(BLACKLIST_FILE, backup)
        keep = {x.lower() for x in get_all_protected_groups() if x.strip()}
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            old_entries = {x.strip() for x in f if x.strip()}
        retained = sorted(x for x in old_entries if x.lower() in keep)
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(retained) + ('\n' if retained else ''))
        metadata = _load_json_file(BLACKLIST_META_FILE, {})
        for group in retained:
            metadata.setdefault(group.lower(), {'reason': 'legacy_approved_group', 'client': 'migration'})
        _save_json_file(BLACKLIST_META_FILE, metadata)
        with open(BLACKLIST_MIGRATION_MARKER, 'w', encoding='utf-8') as f:
            f.write(f'v2 migrated {stamp}; backup={backup}\n')
        try:
            fs_set_state(blacklist='\n'.join(retained) + ('\n' if retained else ''))
        except Exception:
            pass
        print(f"🧹 Legacy blacklist migrated: {len(old_entries)} -> {len(retained)}; backup={backup}")
        return True
    except Exception as e:
        print(f"⚠️ Legacy blacklist migration failed; original file preserved: {e}")
        return False

def is_on_cooldown(grup_name, client_name, entity=None):
    """
    Hesap + grup bazlı reklam aralığını kontrol eder.
    Her aktif hesap aynı gruba kendi mesajını atabilir, sonra en az 1 saat bekler.
    """
    from datetime import datetime

    # Dinamik olarak config'den oku
    cooldown_hours = GROUP_COOLDOWN_HOURS
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                cooldown_hours = cfg.get("group_cooldown_hours", GROUP_COOLDOWN_HOURS)
        except:
            pass
    try:
        cooldown_hours = max(float(cooldown_hours), 1.0)
    except (TypeError, ValueError):
        cooldown_hours = 1.0
            
    if is_account_restricted(client_name) or is_group_retry_blocked(grup_name, client_name, entity):
        return True

    cooldowns = load_cooldowns()
    now = datetime.now()

    legacy_mapping = {
        'FroxyOnline': ['Hesap #1', 'froxy_ai', 'c4hex'],
        'KeyVadiOnline': ['Hesap #2', 'keyvadionline', 'userrrrrrrrrra'],
        'LisansArenaOnline': ['Hesap #3', 'lisansarenaonline'],
    }
    my_aliases = set([client_name, client_name.lower()])
    if client_name in legacy_mapping:
        my_aliases.update(legacy_mapping[client_name])

    # Ayni grup gecmiste farkli anahtarla kaydedilmis olabilir; hepsine bak.
    for key in group_state_keys(grup_name, entity):
        group_data = cooldowns.get(key)
        if not group_data:
            continue

        # Eski tip dize formatı (tek zaman damgası) uyumluluğu
        if isinstance(group_data, str):
            try:
                last_sent = datetime.fromisoformat(group_data)
                if (now - last_sent).total_seconds() / 3600 < cooldown_hours:
                    return True
            except:
                pass
            continue

        this_acc_time = None
        for alias in my_aliases:
            if alias in group_data:
                this_acc_time = group_data[alias]
                break

        if this_acc_time:
            try:
                last_sent = datetime.fromisoformat(this_acc_time)
                if (now - last_sent).total_seconds() / 3600 < cooldown_hours:
                    return True
            except:
                pass

        # Hesaplar arasi kisa aralik (ör. 60 saniye safety buffer)
        for diger_hesap, diger_zaman in group_data.items():
            if diger_hesap in my_aliases or not diger_zaman:
                continue
            try:
                gecen = (now - datetime.fromisoformat(diger_zaman)).total_seconds()
                if gecen < INTER_ACCOUNT_GAP_SECONDS:
                    return True
            except Exception:
                continue

    return False

def set_cooldown(grup_name, client_name, entity=None):
    """Gruba bu hesap tarafından mesaj gönderildi olarak işaretle"""
    from datetime import datetime
    cooldowns = load_cooldowns()
    key = cooldown_key(grup_name, entity)

    # Eski tip veri varsa veya boşsa temizle
    if key not in cooldowns or isinstance(cooldowns[key], str):
        cooldowns[key] = {}

    cooldowns[key][client_name] = datetime.now().isoformat()
    save_cooldowns(cooldowns)

def get_canonical_account_name(client_name):
    name = str(client_name or '').strip().lower()
    if 'lisans' in name or name in {'hesap #3', 'hesap #5', 'lisansarenaonline'}:
        return 'LisansArenaOnline'
    if 'froxy' in name or name in {'hesap #1', 'froxyonline', 'froxy_ai', 'c4hex'}:
        return 'FroxyOnline'
    return 'KeyVadiOnline'

def get_account_aliases(client_name):
    cname = get_canonical_account_name(client_name)
    # Yalniz aktif kimlik ve marka anahtarlari. Eski User/Hesap/c4hex
    # rumuzlarini burada tutmak Firestore'da yasakli hesaplar halen blast
    # atiyormus gibi gorunmesine yol aciyordu. Kanonik marka anahtari eski
    # cooldown gecmisini korumaya yeterlidir.
    aliases = {cname, cname.lower()}
    if cname == 'FroxyOnline':
        aliases.add('froxy_ai')
    elif cname == 'KeyVadiOnline':
        aliases.add('keyvadidestek')
    elif cname == 'LisansArenaOnline':
        aliases.add('lisansarenaonline')
    return aliases

def save_last_blast_time(client_name):
    """Hesabın son blast tamamlanma zamanını kaydeder (tüm rumuzlar için)"""
    try:
        from datetime import datetime
        cname = get_canonical_account_name(client_name)
        cooldowns = load_cooldowns()
        now_str = datetime.now().isoformat()
        for alias in get_account_aliases(client_name):
            cooldowns[f"__LAST_BLAST_TIME_{alias}"] = now_str
        save_cooldowns(cooldowns)
        try:
            fs_set_state(cooldowns=json.dumps(cooldowns, ensure_ascii=False, indent=2))
        except Exception:
            pass
        print(f"[{cname}] 💾 Son blast zamanı kaydedildi: {now_str}")
    except Exception as e:
        print(f"[{client_name}] ⚠️ Son blast zamanı kaydetme hatası: {e}")

def get_last_blast_remaining_wait(client_name, target_wait_seconds=3600):
    """Sunucu yeniden başlatıldığında hesabın kalan bekleme süresini hesaplar"""
    try:
        from datetime import datetime
        cname = get_canonical_account_name(client_name)
        cooldowns = load_cooldowns()
        
        fs_cdata = {}
        try:
            _, _, _, _, fs_cooldowns, _ = fs_get_state()
            if fs_cooldowns:
                fs_cdata = json.loads(fs_cooldowns)
        except Exception:
            pass

        timestamps = []
        for alias in get_account_aliases(client_name):
            k = f"__LAST_BLAST_TIME_{alias}"
            # Yerel ve bulut kaydindan en yenisini kullan. Eski kod yerel
            # kayit varsa daha yeni Firestore degerini hic okumuyordu.
            for val in (cooldowns.get(k), fs_cdata.get(k)):
                if val and isinstance(val, str):
                    try:
                        timestamps.append(datetime.fromisoformat(val))
                    except Exception:
                        pass

        if not timestamps:
            print(f"[{cname}] 🛡️ Sunucu başlangıcı: Son blast kaydı bulunamadı, 60 dakika güvenlik beklemesi uygulanıyor.")
            return target_wait_seconds

        latest_dt = max(timestamps)
        elapsed = (datetime.now() - latest_dt).total_seconds()
        if elapsed < target_wait_seconds:
            rem = int(target_wait_seconds - elapsed)
            print(f"[{cname}] ⏳ Son blast {int(elapsed // 60)}dk önce yapılmış → Kalan {int(rem // 60)}dk ({rem}sn) bekleniyor.")
            return rem
        else:
            print(f"[{cname}] ✅ Son blast {int(elapsed // 60)}dk önce yapılmış (1 saat doldu), yeni blast zamanı geldi.")
            return 0
    except Exception as e:
        print(f"[{client_name}] ⚠️ Kalan bekleme hesaplama hatası: {e}")
        return target_wait_seconds

# --- Mesaj Rotasyonu (6 şablon: kısa/uzun, soru/direkt, fiyat/sosyal) ---
FROXY_MESSAGES = [
    os.path.join(MESSAGES_DIR, 'froxy_hook.txt'),
    os.path.join(MESSAGES_DIR, 'froxy_compare.txt'),
    os.path.join(MESSAGES_DIR, 'froxy_social.txt'),
    os.path.join(MESSAGES_DIR, 'froxy_question.txt'),
    os.path.join(MESSAGES_DIR, 'froxy_short.txt'),
    os.path.join(MESSAGES_DIR, 'froxy_price.txt'),
]
KEYVADI_MESSAGES = [
    os.path.join(MESSAGES_DIR, 'keyvadi_1.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_2.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_3.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_4.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_5.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_6.txt'),
]

LISANSARENA_MESSAGES = [
    os.path.join(MESSAGES_DIR, 'lisansarena_1.txt'),
    os.path.join(MESSAGES_DIR, 'lisansarena_2.txt'),
    os.path.join(MESSAGES_DIR, 'lisansarena_3.txt'),
    os.path.join(MESSAGES_DIR, 'lisansarena_4.txt'),
    os.path.join(MESSAGES_DIR, 'lisansarena_5.txt'),
    os.path.join(MESSAGES_DIR, 'lisansarena_6.txt'),
]

# Mesaj geçmişi (aynı gruba aynı mesaj gitmesin)
def load_msg_history():
    if os.path.exists(MSG_HISTORY_FILE):
        try:
            with open(MSG_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_msg_history(history):
    try:
        with open(MSG_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except:
        pass

_last_global_chosen_map = {}

def pick_message_for_group(grup_name, msg_files, history):
    """Grup için son gönderilen mesajdan ve peş peşe atılan son mesajdan farklı bir mesaj seç"""
    if not msg_files:
        return ""
    brand_key = tuple(sorted(msg_files))
    last_global = _last_global_chosen_map.get(brand_key, "")
    
    last_used = history.get(grup_name.lower(), "")
    available = [f for f in msg_files if f != last_used]
    if not available:
        available = list(msg_files)
    
    # Ardışık iki grupta aynı mesaj gitmesin diye son küresel seçimden farklısını tercih et
    if len(available) > 1 and last_global in available:
        filtered = [f for f in available if f != last_global]
        if filtered:
            available = filtered
            
    chosen = random.choice(available)
    history[grup_name.lower()] = chosen
    _last_global_chosen_map[brand_key] = chosen
    return chosen

def is_active_hours():
    """TR saatlerinde aktif saatleri kontrol et (UTC+3)"""
    from datetime import datetime, timezone, timedelta
    tr_time = datetime.now(timezone(timedelta(hours=3)))
    hour = tr_time.hour
    # Peak saatler: 12:00-14:00 ve 19:00-23:59 (en yüksek etkileşim)
    # Normal saatler: 00:00-01:59 ve 08:00-11:59 ve 15:00-18:59
    # Gece saatleri: 02:00-07:59 (mesajlar saat başı atılır)
    if (12 <= hour <= 14) or (19 <= hour <= 23):
        return 'peak'
    elif (2 <= hour <= 7):
        return 'night'
    else:
        return 'normal'

def minutes_until_active():
    """Artık dead saatleri kullanmıyoruz, 0 döndür"""
    return 0

# --- Auto-Scrape: yalnızca hedef müşteri kitlesine yakın sorgular ---
SCRAPE_KEYWORDS = [
    "dijital ürün satış", "dijital hesap satış", "premium hesap satış",
    "hesap alım satım", "sanal ticaret", "sanal alım satım",
    "kupon satış", "kupon alım satım", "kod satış", "indirim kodu satış",
    "reklam referans", "reklam grubu", "sosyal medya alım satım",
    "smm panel satış", "lisans satış", "yazılım lisans satış",
    "shopier satış", "epin satış", "oyun kod satış",
    "canva pro satış", "adobe lisans", "office lisans",
    "netflix hesap satış", "youtube premium satış", "spotify premium satış",
    "chatgpt plus satış", "yapay zeka araçları", "ai araçları satış"
]

async def auto_scrape_groups(client, client_name, joined_usernames=None):
    """Telegram global aramasıyla yeni, aktif ve kaliteli Türkçe satış grupları keşfeder."""
    if is_account_restricted(client_name, scope='discover'):
        state = account_restriction_status(client_name, scope='discover')
        print(f"[{client_name}] Auto-Scraper discovery kısıtı bitene kadar atlandı: {state.get('until', 'belirsiz')}")
        return

    print(f"\n🔍 [{client_name}] Gelişmiş Grup Keşfi (Auto-Scraper v2) başlıyor...")
    
    # Yapılandırmayı bot_config.json dosyasından dinamik olarak oku
    scraper_active = True
    keywords_list = SCRAPE_KEYWORDS
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                scraper_active = cfg.get("scraper_active", True)
                custom_kw = cfg.get("scrape_keywords", None)
                if cfg.get("use_custom_scrape_keywords", False) and custom_kw:
                    keywords_list = custom_kw
        except:
            pass
            
    if not scraper_active:
        print(f"ℹ️ [{client_name}] Auto-Scraper pasif (kontrol panelinden kapatılmış).")
        return 0
        
    if not keywords_list:
        print(f"⚠️ [{client_name}] Scraper anahtar kelime listesi boş!")
        return 0
        
    existing_groups = set(g.lower() for g in gruplar)
    if joined_usernames:
        existing_groups.update(joined_usernames)
    blacklist = get_list(BLACKLIST_FILE)
    blacklist_lower = set(b.lower() for b in blacklist)
    scraped_history = get_list("scraped_groups.txt")
    scraped_history_lower = set(s.lower() for s in scraped_history)
    new_found = 0
    blacklisted_count = 0
    
    # Türkçe satış grubu olup olmadığını kontrol etmek için kelimeler
    sales_keywords = [
        "satış", "satis", "ticaret", "ilan", "reklam", "kupon", "indirim",
        "shopier", "hesap", "alım", "satım", "alim", "satim", "smm", "kod",
        "ucuz", "ref", "pazar", "lisans", "premium", "dijital", "adobe", "canva",
        "trendyol", "kampanya", "fırsat", "firsat", "epin", "yazılım", "yazilim", 
        "yapay zeka", "ai", "chatgpt"
    ]
    
    # Günde 1 kez çalıştığı için TÜM keyword'leri tara (karıştırarak)
    DAILY_GROUP_LIMIT = 50  # Günlük maksimum yeni grup sayısı
    selected_keywords = keywords_list.copy()
    random.shuffle(selected_keywords)
    print(f"🔎 [{client_name}] Günlük tarama: {len(selected_keywords)} anahtar kelime, max {DAILY_GROUP_LIMIT} yeni grup hedefi")
    
    from telethon.tl.types import Channel, Chat
    
    for keyword in selected_keywords:
        await asyncio.sleep(2.0)
        if new_found >= DAILY_GROUP_LIMIT:
            print(f"🎯 [{client_name}] Günlük limit ({DAILY_GROUP_LIMIT} grup) doldu, tarama durduruluyor.")
            break
        print(f"🔎 [{client_name}] Aranıyor: '{keyword}'")
        try:
            result = await client(SearchRequest(q=keyword, limit=50))
            keyword_found = 0
            keyword_blacklisted = 0
            
            for chat in result.chats:
                is_group = False
                if isinstance(chat, Channel):
                    if not getattr(chat, 'broadcast', False):
                        is_group = True
                elif isinstance(chat, Chat):
                    is_group = True
                    
                # Broadcast channels are skipped during discovery, but are not
                # globally blacklisted unless Telegram confirms write denial.
                username_attr = getattr(chat, 'username', None)
                if not is_group or not username_attr:
                    if isinstance(chat, Channel) and getattr(chat, 'broadcast', False) and username_attr:
                        username = username_attr.lower()
                    continue
                    
                username = chat.username.lower()
                if username in existing_groups or username in blacklist_lower or username in scraped_history_lower:
                    continue
                    
                member_count = getattr(chat, 'participants_count', None)
                title = (chat.title or "").lower()
                
                # === FİLTRE 1: Üye sayısı (500'den az = zaman kaybı) ===
                if member_count is not None and member_count < 500:
                    print(f"  ⏭️ @{chat.username} → Üye az ({member_count}), bu taramada atlandı")
                    continue
                
                # === FİLTRE 2: Başlık dil/alaka/negatif kontrolü ===
                has_sales_word = any(w in title for w in sales_keywords)
                has_negative = any(w in title for w in NEGATIVE_KEYWORDS)
                
                if has_negative or not has_sales_word:
                    print(f"  ⏭️ @{chat.username} → Alakasız/negatif ('{chat.title}'), bu taramada atlandı")
                    continue
                
                # === FİLTRE 2.5: İstek/Onay kontrolü (Direkt katılım olmalı) ===
                if getattr(chat, 'join_request', False):
                    print(f"  ⏭️ @{chat.username} → Katılım isteği gerekiyor, admin onayı bekleniyor")
                    continue
                
                # === FİLTRE 3: Derin kalite taraması (son 5 mesaj) ===
                try:
                    recent_msgs = await client.get_messages(chat, limit=5)
                    
                    if not recent_msgs or len(recent_msgs) == 0:
                        print(f"  ⏭️ @{chat.username} → Boş grup, bu taramada atlandı")
                        continue
                    
                    # İnaktiflik kontrolü (5 gün)
                    from datetime import datetime, timezone
                    now_utc = datetime.now(timezone.utc)
                    last_msg_date = recent_msgs[0].date
                    delta_days = (now_utc - last_msg_date).days
                    if delta_days >= 5:
                        print(f"  ⏭️ @{chat.username} → İnaktif ({delta_days} gün), bu taramada atlandı")
                        continue
                    
                    # Spam çöplüğü tespiti
                    bot_mention_count = 0
                    unique_senders = set()
                    
                    for m in recent_msgs:
                        msg_text = (getattr(m, 'raw_text', '') or '').lower()
                        sender_id = getattr(m, 'sender_id', None)
                        if sender_id:
                            unique_senders.add(sender_id)
                        
                        # @...Bot mention'ları say
                        bot_mentions = re.findall(r'@\w+bot\b', msg_text, re.IGNORECASE)
                        if bot_mentions:
                            bot_mention_count += 1
                    
                    # Son 5 mesajın 3+'ü bot reklamı → spam çöplüğü
                    if bot_mention_count >= 3:
                        if username not in blacklist_lower:
                            keyword_blacklisted += 1
                            print(f"  🗑️ @{chat.username} → Spam çöplüğü ({bot_mention_count}/5 bot reklamı), kara liste")
                        continue
                    
                    # Son 5 mesajda sadece 1-2 unique gönderen → ölü grup
                    if len(recent_msgs) >= 5 and len(unique_senders) <= 2:
                        print(f"  ⏭️ @{chat.username} → Ölü grup ({len(unique_senders)} kişi aktif), bu taramada atlandı")
                        continue
                    
                except Exception:
                    pass
                    
                # === TÜM FİLTRELERİ GEÇTİ — KALİTELİ GRUP ===
                try:
                    save_to_list(chat.username, "scraped_groups.txt")
                    scraped_history_lower.add(username)
                except Exception as e:
                    print(f"⚠️ scraped_groups.txt kaydetme hatası: {e}")

                new_found += 1
                keyword_found += 1
                print(f"  🆕 KALİTELİ GRUP KEŞFEDİLDİ (Onay Bekleniyor): @{chat.username} (Üye: {member_count or '?'}, Başlık: '{chat.title}')")
                
                # Admin'e onay için bireysel bildirim gönder (Otomatik katılım iptal edildi)
                try:
                    admin_id = None
                    if os.path.exists("bot_config.json"):
                        with open("bot_config.json", "r", encoding="utf-8") as f_cfg:
                            cfg = json.load(f_cfg)
                            admin_id = cfg.get("admin_id")
                    if admin_id:
                        bildirim = (
                            f"🔍 **Yeni Kaliteli Grup Keşfedildi!**\n"
                            f"━━━━━━━━━━━━━━━━━\n"
                            f"• Kullanıcı Adı: @{chat.username}\n"
                            f"• Üye Sayısı: {member_count or '?'}\n"
                            f"• Başlık: {chat.title or '?'}\n"
                            f"━━━━━━━━━━━━━━━━━\n"
                            f"ℹ️ Eklemek için bu mesaja **reply (yanıtla)** yaparak **ekle** veya **ok** yazabilirsin."
                        )
                        await client.send_message(int(admin_id), bildirim)
                        print(f"📩 [{client_name}] Admin'e @{chat.username} için onay bildirimi gönderildi.")
                except Exception as ne:
                    print(f"⚠️ Bireysel admin bildirim hatası: {ne}")
                
            summary = f"'{keyword}': +{keyword_found} yeni"
            if keyword_blacklisted > 0:
                summary += f", {keyword_blacklisted} kara listeye alındı"
            print(f"  📊 [{client_name}] {summary}")
            blacklisted_count += keyword_blacklisted
            await asyncio.sleep(3)
                
        except FloodWaitError as e:
            set_account_restriction(client_name, e.seconds, 'Telegram discovery FloodWait', type(e).__name__, scope='discover')
            print(f"⏳ [{client_name}] Auto-Scraper FloodWait ({e.seconds}s); sadece discovery duraklatıldı.")
            break
        except Exception as e:
            print(f"⚠️ [{client_name}] Auto-Scraper hatası ('{keyword}'): {type(e).__name__} - {e}")
            
    if new_found > 0:
        update_stats(discovered=new_found)
    
    print(f"\n📊 [{client_name}] Scraper Sonuç: {new_found} yeni kaliteli grup onay bekliyor, {blacklisted_count} çöp grup kara listeye alındı.")
        
    return new_found

# Akıllı DM Mesaj Şablonları (anahtar kelimeye göre)
DM_TEMPLATES = {
    "ai": (
        "Merhaba 👋\n\n"
        "Yapay zeka ile ilgili mesajınızı gördüm. "
        "ChatGPT, Claude, Gemini ve 1100+ AI modelini tek panelden kullanabilirsiniz — "
        "üstelik ilk 100 kredi ücretsiz!\n\n"
        "Detaylar için: @FroxyDestekBOT\n"
        "İyi günler! 🙏"
    ),
    "kupon": (
        "Merhaba 👋\n\n"
        "Kupon/indirim ile ilgili mesajınızı gördüm. "
        "Trendyol Yemek, Market ve Shell kuponlarını en uygun fiyatlarla sunuyoruz!\n\n"
        "Detaylar için: @KeyVadiSatisBot\n"
        "İyi günler! 🙏"
    ),
    "yazilim": (
        "Merhaba 👋\n\n"
        "Yazılım/lisans ile ilgili mesajınızı gördüm. "
        "Adobe CC, Canva Pro ve diğer premium lisanslar en uygun fiyatlarla!\n\n"
        "Detaylar için: @KeyVadiSatisBot\n"
        "İyi günler! 🙏"
    ),
    "genel": (
        "Merhaba 👋\n\n"
        "Gruptaki mesajınızı gördüm. Size yardımcı olabilirim!\n"
        "Yapay zeka, premium lisanslar ve dijital ürünler için:\n"
        "• AI Modelleri: @FroxyDestekBOT\n"
        "• Lisans & Kuponlar: @KeyVadiSatisBot\n\n"
        "İyi günler! 🙏"
    ),
}

def get_dm_category(text):
    """Mesaj metninden DM kategorisini belirle"""
    text_lower = text.lower()
    ai_words = ["yapay zeka", "chatgpt", "claude", "gemini", "gpt", "ai ", " ai", "deepseek", "llama"]
    kupon_words = ["kupon", "indirim", "trendyol", "shell", "akaryakıt"]
    yazilim_words = ["adobe", "canva", "capcut", "lisans", "premium", "photoshop", "illustrator"]
    
    if any(w in text_lower for w in ai_words):
        return "ai"
    elif any(w in text_lower for w in kupon_words):
        return "kupon"
    elif any(w in text_lower for w in yazilim_words):
        return "yazilim"
    return None


# Firestore Ayarları
API_KEY    = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def fs_get_state():
    try:
        url = f"{BASE_URL}/reklam/state?key={API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            fields = r.json().get("fields", {})
            progress = fields.get("progress_list", {}).get("stringValue", "")
            blacklist = fields.get("blacklist_list", {}).get("stringValue", "")
            auto_groups = fields.get("auto_groups_list", {}).get("stringValue", "")
            scraped_groups = fields.get("scraped_groups_list", {}).get("stringValue", "")
            cooldowns = fields.get("cooldowns_list", {}).get("stringValue", "")
            welcomed = fields.get("welcomed_users_list", {}).get("stringValue", "")
            return progress, blacklist, auto_groups, scraped_groups, cooldowns, welcomed
    except Exception as e:
        print(f"⚠️ Firestore yükleme hatası: {e}")
    return "", "", "", "", "", ""

def fs_set_state(progress=None, blacklist=None, auto_groups=None, scraped_groups=None, cooldowns=None, welcomed_users=None):
    try:
        fields = {}
        mask_parts = []
        
        if progress is not None:
            fields["progress_list"] = {"stringValue": progress}
            mask_parts.append("updateMask.fieldPaths=progress_list")
        if blacklist is not None:
            fields["blacklist_list"] = {"stringValue": blacklist}
            mask_parts.append("updateMask.fieldPaths=blacklist_list")
        if auto_groups is not None:
            fields["auto_groups_list"] = {"stringValue": auto_groups}
            mask_parts.append("updateMask.fieldPaths=auto_groups_list")
        if scraped_groups is not None:
            fields["scraped_groups_list"] = {"stringValue": scraped_groups}
            mask_parts.append("updateMask.fieldPaths=scraped_groups_list")
        if cooldowns is not None:
            fields["cooldowns_list"] = {"stringValue": cooldowns}
            mask_parts.append("updateMask.fieldPaths=cooldowns_list")
        if welcomed_users is not None:
            fields["welcomed_users_list"] = {"stringValue": welcomed_users}
            mask_parts.append("updateMask.fieldPaths=welcomed_users_list")
            
        if not fields:
            return
            
        mask_str = "&".join(mask_parts)
        url = f"{BASE_URL}/reklam/state?{mask_str}&key={API_KEY}"
        # Yanit kodu kontrol edilmeliydi: requests 4xx/5xx'te exception ATMAZ,
        # dolayisiyla belge 1 MiB sinirini asinca ya da kota dolunca senkron
        # sessizce oluyor, log yine 'buluta yazildi' diyordu.
        cevap = requests.patch(url, json={"fields": fields}, timeout=10)
        if cevap.status_code >= 400:
            print(f"⚠️ [Firestore] Yazma reddedildi: HTTP {cevap.status_code} "
                  f"— {cevap.text[:160]}")
            return False
        return True
    except Exception as e:
        print(f"⚠️ Firestore kaydetme hatası: {e}")

def get_list(dosya):
    if os.path.exists(dosya):
        with open(dosya, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_list(grup, dosya):
    if dosya == BLACKLIST_FILE:
        g_lower = normalize_group_key(grup)
        target_groups = {"kuponindirimsatis", "ticaretguvenilir", "kuponsatimalim", "indirimkodusatis", "yucekuponsatis", "kuponindirimpazari", "sosyalmedyaalimsatimticaret", "nightsatis", "kuponindirimsatis", "kuponsatisgrup", "kuponhesapsatis", "kuponceking", "tahaaslan11", "alimsatimmerkezii"}
        if is_group_protected(grup) or g_lower in target_groups:
            print(f"⚠️ [Security] Korumalı/hedef grup @{grup} kara listeye eklenmesi engellendi, 1 saatlik geçici bekleme süresine alındı.")
            return

        if os.path.exists(AUTO_GROUPS_FILE):
            try:
                with open(AUTO_GROUPS_FILE, "r", encoding="utf-8") as f:
                    auto_list = [line.strip() for line in f if line.strip()]
                if any(normalize_group_key(x) == g_lower for x in auto_list):
                    new_auto = [x for x in auto_list if normalize_group_key(x) != g_lower]
                    with open(AUTO_GROUPS_FILE, "w", encoding="utf-8") as f:
                        f.write("\n".join(new_auto) + "\n")
                    print(f"🗑️ [Auto-Groups] @{grup} yazma hatası/ban nedeniyle auto_groups.txt listesinden kaldırıldı.")
                    try:
                        fs_set_state(auto_groups="\n".join(new_auto) + "\n")
                    except:
                        pass
            except Exception as e:
                print(f"⚠️ auto_groups.txt güncellenirken hata: {e}")
            
    with open(dosya, 'a', encoding='utf-8') as f:
        f.write(grup + '\n')
    
    # Firestore durum eşitlemesi
    try:
        if dosya == BLACKLIST_FILE:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            fs_set_state(blacklist=content)
        elif dosya == PROGRESS_FILE:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            fs_set_state(progress=content)
        elif dosya == AUTO_GROUPS_FILE:
            with open(AUTO_GROUPS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            fs_set_state(auto_groups=content)
        elif dosya == "scraped_groups.txt":
            with open("scraped_groups.txt", 'r', encoding='utf-8') as f:
                content = f.read()
            fs_set_state(scraped_groups=content)
    except Exception as e:
        print(f"⚠️ Firestore güncelleme hatası: {e}")

def register_admin_handler(client, client_name, joined_dialogs):
    # bot_config.json'dan admin_id'yi oku
    admin_id = None
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                admin_id = cfg.get("admin_id")
        except:
            pass
            
    if not admin_id:
        print(f"⚠️ [{client_name}] Uyarı: admin_id bulunamadığı için admin komut işleyicisi başlatılamadı.")
        return
        
    @client.on(events.NewMessage(incoming=True, chats=int(admin_id)))
    async def handle_admin_reply(event):
        try:
            msg_text = (event.raw_text or "").strip().lower()
            
            # 1. Bireysel grup bildirimi yanıtı (Reply-to-approve)
            if event.is_reply and msg_text in ['ekle', 'ok', 'y', 'evet', 'confirm', 'approve']:
                reply_msg = await event.get_reply_message()
                if reply_msg and reply_msg.sender_id == (await client.get_me()).id:
                    # Kullanıcı adını mesaj metninden ayıkla
                    match = re.search(r'• Kullanıcı Adı:\s*@?(\w+)', reply_msg.raw_text)
                    if match:
                        grup_username = match.group(1).strip()
                        print(f"[{client_name}] 📥 Admin onayı alındı: @{grup_username}")
                        
                        # Blacklist'te ise çıkar
                        blacklist = get_list(BLACKLIST_FILE)
                        if grup_username.lower() in set(x.lower() for x in blacklist):
                            try:
                                with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                                    lines = f.read().splitlines()
                                new_lines = [l for l in lines if l.strip().lower() != grup_username.lower()]
                                with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                                    f.write('\n'.join(new_lines) + '\n')
                                print(f"[{client_name}] 🔓 @{grup_username} kara listeden çıkarıldı.")
                            except Exception as ble:
                                print(f"⚠️ Kara listeden çıkarma hatası: {ble}")
                        
                        # auto_groups.txt'ye ekle
                        local_auto = get_list(AUTO_GROUPS_FILE)
                        if grup_username.lower() not in set(x.lower() for x in local_auto):
                            save_to_list(grup_username, AUTO_GROUPS_FILE)
                            
                        # Gruba katılmayı dene
                        try:
                            entity = await client.get_entity(grup_username)
                            await client(JoinChannelRequest(entity))
                            joined_dialogs[grup_username.lower()] = entity
                            await event.respond(f"✅ **@{grup_username} onaylandı!**\nGruba başarıyla katıldım ve reklam listesine ekledim.")
                        except Exception as je:
                            await event.respond(f"⚠️ **@{grup_username}** listeye eklendi ancak gruba katılım başarısız oldu:\n`{type(je).__name__}: {je}`")
                        return
                    else:
                        await event.respond("⚠️ Yanıtlanan mesajda onaylanacak grup kullanıcı adı bulunamadı.")
                        return

            # 1.5. Manuel tarama tetikleme
            if msg_text in ['/tara', 'tara', 'scan', '/scan']:
                await event.respond("🔍 **Grup taraması başlatılıyor...**\nBu işlem birkaç dakika sürebilir.")
                try:
                    with open("trigger_scraper.flag", "w", encoding="utf-8") as f:
                        f.write("trigger")
                except Exception as e:
                    await event.respond(f"⚠️ Hata: {e}")
                return

            # 2. Doğrudan link veya kullanıcı adı ekleme (Mesaj ile doğrudan ekleme)
            grup_to_add = None
            if msg_text.startswith('/ekle '):
                grup_to_add = event.raw_text[6:].strip()
            elif msg_text.startswith('@'):
                grup_to_add = event.raw_text[1:].strip()
            elif 't.me/' in msg_text or 'telegram.me/' in msg_text:
                parts = event.raw_text.split('/')
                grup_to_add = parts[-1].strip()
                
            if grup_to_add:
                grup_to_add = re.sub(r'[^a-zA-Z0-9_]', '', grup_to_add)
                if len(grup_to_add) >= 3:
                    # Blacklist'ten çıkar
                    blacklist = get_list(BLACKLIST_FILE)
                    if grup_to_add.lower() in set(x.lower() for x in blacklist):
                        try:
                            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                                lines = f.read().splitlines()
                            new_lines = [l for l in lines if l.strip().lower() != grup_to_add.lower()]
                            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(new_lines) + '\n')
                        except:
                            pass
                    
                    local_auto = get_list(AUTO_GROUPS_FILE)
                    if grup_to_add.lower() not in set(x.lower() for x in local_auto):
                        save_to_list(grup_to_add, AUTO_GROUPS_FILE)
                        
                    try:
                        entity = await client.get_entity(grup_to_add)
                        await client(JoinChannelRequest(entity))
                        joined_dialogs[grup_to_add.lower()] = entity
                        await event.respond(f"✅ **@{grup_to_add} başarıyla eklendi!**\nGruba katıldım ve reklam listesine ekledim.")
                    except Exception as je:
                        await event.respond(f"⚠️ **@{grup_to_add}** listeye eklendi ancak gruba katılım başarısız oldu:\n`{type(je).__name__}: {je}`")
        except Exception as ex:
            print(f"[{client_name}] ⚠️ Admin yanıt işleme hatası: {ex}")

replied_users_cooldown = {}
welcomed_users = set()

def load_welcomed_users():
    global welcomed_users
    if os.path.exists("welcomed_users.json"):
        try:
            with open("welcomed_users.json", "r", encoding="utf-8") as f:
                welcomed_users = set(json.load(f))
        except:
            pass

def save_welcomed_users():
    try:
        with open("welcomed_users.json", "w", encoding="utf-8") as f:
            json.dump(list(welcomed_users), f)
        content = "\n".join(welcomed_users) + "\n"
        fs_set_state(welcomed_users=content)
    except Exception as e:
        print(f"⚠️ Karşılanan kullanıcılar kaydedilirken hata: {e}")

load_welcomed_users()

async def async_get_document(doc_id):
    loop = asyncio.get_event_loop()
    import firestore_helper
    return await loop.run_in_executor(None, firestore_helper.get_document, doc_id)

async def async_set_document(doc_id, fields_dict):
    loop = asyncio.get_event_loop()
    import firestore_helper
    return await loop.run_in_executor(None, firestore_helper.set_document, doc_id, fields_dict)

async def presence_watchdog(client):
    from telethon.tl.types import UserStatusOnline, UserStatusRecently
    import firestore_helper
    import asyncio
    print("[Presence Watchdog] Starting Habil presence tracker...")
    while True:
        try:
            admin_user = await client.get_entity('Haacet')
            is_online = False
            if admin_user and admin_user.status:
                is_online = isinstance(admin_user.status, (UserStatusOnline, UserStatusRecently))
            
            await async_set_document("habil_presence", {"is_online": is_online})
        except Exception as e:
            print(f"[Presence Watchdog] Habil status check error: {e}")
        await asyncio.sleep(60)


_RECONNECT_LOCKS = {}

async def ensure_telegram_connection(client, client_name, force=False):
    """Keep a Telegram client usable after transient network/DC disconnects."""
    if not force and client.is_connected():
        return True

    lock = _RECONNECT_LOCKS.setdefault(client_name, asyncio.Lock())
    async with lock:
        if not force and client.is_connected():
            return True
        for attempt in range(1, 4):
            try:
                if force and client.is_connected():
                    await client.disconnect()
                await client.connect()
                if client.is_connected() and await client.is_user_authorized():
                    print(f"[{client_name}] Telegram bağlantısı yenilendi (deneme {attempt}).")
                    return True
            except Exception as exc:
                print(f"[{client_name}] Telegram reconnect denemesi {attempt}/3 başarısız: {type(exc).__name__}")
            await asyncio.sleep(min(5 * attempt, 15))
    return False

async def connection_watchdog(client, client_name):
    while True:
        try:
            await ensure_telegram_connection(client, client_name)
        except Exception as exc:
            print(f"[{client_name}] bağlantı watchdog hatası: {type(exc).__name__}")
        await asyncio.sleep(30)

def match_product_from_text(msg_text, all_products):
    msg_clean = msg_text.lower().strip()
    
    # Aliases & normalization
    msg_clean = msg_clean.replace("you tube", "youtube")
    msg_clean = re.sub(r'\byt\b', 'youtube', msg_clean)
    msg_clean = re.sub(r'\bwin\b', 'windows', msg_clean)
    msg_clean = msg_clean.replace("win10", "windows")
    msg_clean = msg_clean.replace("win11", "windows")
    msg_clean = msg_clean.replace("office365", "office 365")
    msg_clean = msg_clean.replace("gamepass", "game pass")
    msg_clean = msg_clean.replace("cc", "creative cloud")
    
    def _get_words(text):
        return re.findall(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+', text.lower())
        
    query_words = _get_words(msg_clean)
    
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "creative",
        "4k", "uhd", "game", "lisans", "microsoft",
        "tradingview", "nordvpn", "vpn", "kaspersky", "envato", "freepik",
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot",
        "hbo", "prime", "perplexity", "magnific", "telegram", "tg"
    }
    
    has_brand = any(w in brand_keywords for w in query_words)
    if not has_brand:
        return None, 0
        
    query_brands = [w for w in query_words if w in brand_keywords]
        
    skip_words = {
        "var", "mi", "mı", "mu", "mü", "ve", "de", "da", "için", "misiniz", "miyiz",
        "olur", "miyim", "yok", "acaba", "hizmeti", "ürünü", "hesabı", "kodu", "kuponu",
        "premium", "alacaktım", "hocam", "knk", "kanka", "bir", "alacağım", "alacaktim",
        "istiyorum", "lazım", "lazim", "alalım", "alalim", "kaç", "kac", "fiyat",
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi",
        "nasıl", "nasil", "nedir", "site", "link", "al", "almak", "satın"
    }
    
    best_product = None
    best_score = 0
    
    for p in all_products:
        title_lower = p.get("title", "").lower()
        title_words = set(_get_words(title_lower))
        
        if "bakiye" in title_lower or "keyvadi" in title_lower:
            continue
            
        # Enforce brand check
        if query_brands:
            if not any(b in title_words for b in query_brands):
                continue
            
        score = 0
        matched_brand = False
        
        for i in range(len(query_words) - 1):
            phrase = f"{query_words[i]} {query_words[i+1]}"
            if phrase in title_lower:
                score += 50
                
        for w in query_words:
            if w in skip_words:
                continue
            if len(w) <= 1:
                continue
            if w in title_words:
                score += 20
                if w in brand_keywords:
                    matched_brand = True
            elif len(w) > 5:
                for tw in title_words:
                    if w in tw or tw in w:
                        score += 8
                        break
        
        # Duration mismatch (Reduced penalty: only penalize if duration is specified and mismatched)
        q_durations = {"haftalık", "aylık", "yıllık", "günlük"}
        q_dur = [w for w in query_words if w in q_durations]
        q_nums = [w for w in query_words if w.isdigit()]
        if q_dur and q_nums:
            dur_phrase = f"{q_nums[0]} {q_dur[0]}"
            if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                score -= 15 
                        
        if not matched_brand and score < 50:
            continue
            
        # Penalties
        if "ultra" in query_words and "ultra" not in title_words:
            score -= 100
        if "ultra" not in query_words and "ultra" in title_words and "pro" in query_words:
            score -= 100
        if "pro" in query_words and "pro" not in title_words and "davet" not in title_words:
            if any(bw in query_words for bw in ["gemini", "grok", "gamma"]):
                score -= 80
                
        q_durations = {"haftalık", "aylık", "yıllık", "günlük"}
        q_dur = [w for w in query_words if w in q_durations]
        q_nums = [w for w in query_words if w.isdigit()]
        if q_dur and q_nums:
            dur_phrase = f"{q_nums[0]} {q_dur[0]}"
            if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                score -= 30
                
        if "yemek" in query_words and "yemek" not in title_words:
            score -= 100
        if "market" in query_words and "market" not in title_words:
            score -= 100
        if "yemek" not in query_words and "yemek" in title_words:
            score -= 50
        if "market" not in query_words and "market" in title_words:
            score -= 50
            
        if "windows" in query_words and "windows" not in title_words:
            score -= 80
        if "office" in query_words and "office" not in title_words:
            score -= 80
            
        if score > best_score:
            best_score = score
            best_product = p
            
    if best_score >= 20:
        return best_product, best_score
    return None, 0

def match_multiple_products_from_text(msg_text, all_products):
    msg_clean = msg_text.lower().strip()
    
    # Aliases & normalization
    msg_clean = msg_clean.replace("you tube", "youtube")
    msg_clean = re.sub(r'\byt\b', 'youtube', msg_clean)
    msg_clean = re.sub(r'\bwin\b', 'windows', msg_clean)
    msg_clean = msg_clean.replace("win10", "windows")
    msg_clean = msg_clean.replace("win11", "windows")
    msg_clean = msg_clean.replace("office365", "office 365")
    msg_clean = msg_clean.replace("gamepass", "game pass")
    msg_clean = msg_clean.replace("cc", "creative cloud")
    
    def _get_words(text):
        return re.findall(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+', text.lower())
        
    query_words = _get_words(msg_clean)
    
    brand_keywords = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "creative",
        "4k", "uhd", "game", "lisans", "microsoft",
        "tradingview", "nordvpn", "vpn", "kaspersky", "envato", "freepik",
        "autocad", "figma", "elementor", "grammarly", "deepl", "ideogram", "quillbot",
        "hbo", "prime", "perplexity", "magnific", "telegram", "tg"
    }
    
    primary_brands = {
        "netflix", "youtube", "adobe", "canva", "windows", "office", "gemini", "grok",
        "xbox", "spotify", "exxen", "trendyol", "duolingo", "semrush", "capcut",
        "scribd", "gamma", "kiro", "steam", "shell", "whatsapp", "apple",
        "crunchyroll", "chatgpt", "midjourney", "tradingview", "nordvpn", "vpn",
        "kaspersky", "envato", "freepik", "autocad", "figma", "elementor", 
        "grammarly", "deepl", "ideogram", "quillbot", "hbo", "prime", "perplexity", 
        "magnific"
    }
    
    query_brands = [w for w in query_words if w in brand_keywords]
    if not query_brands:
        return []
        
    query_primary_brands = [w for w in query_words if w in primary_brands]
    target_brands = list(set(query_primary_brands if query_primary_brands else query_brands))
    
    skip_words = {
        "var", "mi", "mı", "mu", "mü", "ve", "de", "da", "için", "misiniz", "miyiz",
        "olur", "miyim", "yok", "acaba", "hizmeti", "ürünü", "hesabı", "kodu", "kuponu",
        "premium", "alacaktım", "hocam", "knk", "kanka", "bir", "alacağım", "alacaktim",
        "istiyorum", "lazım", "lazim", "alalım", "alalim", "kaç", "kac", "fiyat",
        "ne", "tl", "lira", "bak", "abi", "güvenilir", "güvenilirmi",
        "nasıl", "nasil", "nedir", "site", "link", "al", "almak", "satın"
    }
    
    matched_products = []
    
    for brand in target_brands:
        best_product = None
        best_score = 0
        
        for p in all_products:
            title_lower = p.get("title", "").lower()
            title_words = set(_get_words(title_lower))
            
            if "bakiye" in title_lower or "keyvadi" in title_lower:
                continue
                
            # Enforce brand check
            if brand not in title_words:
                if brand == "adobe" and "creative" in title_words:
                    pass
                elif brand == "creative" and "adobe" in title_words:
                    pass
                else:
                    continue
                
            score = 0
            matched_brand = False
            
            for i in range(len(query_words) - 1):
                phrase = f"{query_words[i]} {query_words[i+1]}"
                if phrase in title_lower:
                    score += 50
                    
            for w in query_words:
                if w in skip_words:
                    continue
                if len(w) <= 1:
                    continue
                if w in title_words:
                    score += 20
                    if w in brand_keywords:
                        matched_brand = True
                elif len(w) > 5:
                    for tw in title_words:
                        if w in tw or tw in w:
                            score += 8
                            break
            
            # Duration mismatch
            q_durations = {"haftalık", "aylık", "yıllık", "günlük"}
            q_dur = [w for w in query_words if w in q_durations]
            q_nums = [w for w in query_words if w.isdigit()]
            if q_dur and q_nums:
                dur_phrase = f"{q_nums[0]} {q_dur[0]}"
                if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                    score -= 15
                            
            if not matched_brand and score < 50:
                continue
                
            # Penalties
            if "ultra" in query_words and "ultra" not in title_words:
                score -= 100
            if "ultra" not in query_words and "ultra" in title_words and "pro" in query_words:
                score -= 100
            if "pro" in query_words and "pro" not in title_words and "davet" not in title_words:
                if any(bw in query_words for bw in ["gemini", "grok", "gamma"]):
                    score -= 80
                    
            if q_dur and q_nums:
                dur_phrase = f"{q_nums[0]} {q_dur[0]}"
                if dur_phrase not in title_lower and len(q_nums[0]) <= 2:
                    score -= 30
                    
            if "yemek" in query_words and "yemek" not in title_words:
                score -= 100
            if "market" in query_words and "market" not in title_words:
                score -= 100
            if "yemek" not in query_words and "yemek" in title_words:
                score -= 50
            if "market" not in query_words and "market" in title_words:
                score -= 50
                
            if "windows" in query_words and "windows" not in title_words:
                score -= 80
            if "office" in query_words and "office" not in title_words:
                score -= 80
                
            if score > best_score:
                best_score = score
                best_product = p
                
        if best_product and best_score >= 20:
            if best_product not in matched_products:
                matched_products.append(best_product)
                
    return matched_products

def register_telegram_code_forwarder(client, client_name):
    admin_id = None
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
                admin_id = cfg.get("admin_id")
        except:
            pass
            
    if not admin_id:
        return

    @client.on(events.NewMessage(incoming=True, chats=777000))
    async def handle_telegram_official_message(event):
        msg_text = event.raw_text or ""
        print(f"📥 [KOD ALICI] {client_name} Telegram hesabından resmi bir mesaj aldı:\n{msg_text}")
        try:
            await client.send_message(int(admin_id), f"🔐 **[Giriş Kodu Yakalandı]**\n\nHesap: **{client_name}**\nMesaj:\n`{msg_text}`")
            print(f"📤 [KOD ALICI] Kod başarıyla admin_id {admin_id}'ye iletildi.")
        except Exception as e:
            print(f"⚠️ [KOD ALICI] İletilirken hata: {e}")

PROCESSED_DM_MSG_IDS = set()
USER_DM_LAST_REPLY_TIME = {}
USER_DM_LAST_REPLY_TEXT = {}

def register_auto_reply_handler(client, client_name, our_user_ids):
    @client.on(events.NewMessage(incoming=True))
    async def handle_private_message(event):
        if not event.is_private or getattr(event, 'out', False):
            return
            
        sender = await event.get_sender()
        if not sender:
            return
            
        sender_id = sender.id
        msg_id = getattr(event.message, 'id', None)

        # 1. Message ID Deduplication Check
        dedupe_key = (client_name, event.chat_id, msg_id)
        if msg_id and dedupe_key in PROCESSED_DM_MSG_IDS:
            return

        if getattr(sender, 'bot', False) or event.sender_id == 777000:
            return
            
        fname = getattr(sender, 'first_name', '') or ''
        uname = getattr(sender, 'username', '') or ''
        if 'creator' in fname.lower() or 'creator' in uname.lower():
            return
            
        # 2. Bot-to-bot / Account loop prevention
        if sender_id in our_user_ids:
            return

        user_key = (client_name, sender_id)

        # 3. Per-User Rate Limiter (15 seconds Cooldown for ALL senders)
        import time
        now = time.time()
        if user_key in USER_DM_LAST_REPLY_TIME:
            if now - USER_DM_LAST_REPLY_TIME[user_key] < 15:
                print(f"⏳ [{client_name}] @{getattr(sender, 'username', sender_id)} 15sn cooldown içinde, mükerrer mesaj yoksayıldı.")
                return

        normalized_text = (event.raw_text or '').strip().lower()
        previous_time = USER_DM_LAST_REPLY_TIME.get(user_key)
        previous_text = USER_DM_LAST_REPLY_TEXT.get(user_key, '')
        if previous_time and now - previous_time < 90 and normalized_text == previous_text:
            return

        print(f"📥 [{client_name}] DM Alındı: GÖNDEREN={sender_id} (@{getattr(sender, 'username', '')}) MESAJ='{event.raw_text}'")

        msg_text = (event.raw_text or "").strip().lower()
        if not msg_text:
            return
        if is_obviously_non_sales_dm(event.raw_text):
            print(f"[{client_name}] DM satış dışı görünüyor, otomatik yanıt atlandı.")
            return

        is_keyvadi, is_lisansarena, is_froxy = account_flags(client_name)
        
        products = []
        if is_lisansarena:
            if os.path.exists("lisansarena_shopier_links.json"):
                try:
                    with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            pid = item.get("id")
                            title = item.get("title")
                            url = item.get("url")
                            pdata = item.get("priceData") or {}
                            price_val = pdata.get("price", "0") if isinstance(pdata, dict) else "0"
                            try:
                                price_str = f"{float(price_val):.2f} TL"
                            except:
                                price_str = f"{price_val} TL"
                            products.append({
                                "id": pid,
                                "title": title,
                                "price": price_str,
                                "url": url
                            })
                except Exception as e:
                    print(f"⚠️ Error loading LisansArena products: {e}")
        elif is_keyvadi:
            if os.path.exists("keyvadi_shopier_links.json"):
                try:
                    with open("keyvadi_shopier_links.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            pid = item.get("id")
                            title = item.get("title")
                            url = item.get("url")
                            price_val = item.get("price", "0")
                            products.append({
                                "id": pid,
                                "title": title,
                                "price": price_val,
                                "url": url
                            })
                except:
                    pass

        matched_products = []
        if products:
            matched_products = match_multiple_products_from_text(event.raw_text, products)
            
        reply_text = None
        matched_desc = ""
        if matched_products:
            if len(matched_products) == 1:
                reply_text = matched_products[0]['url']
                matched_desc = matched_products[0]['title']
            else:
                lines = ["🔍 **Aradığınız Ürünler:**\n"]
                for p in matched_products[:5]:
                    lines.append(f"• **{p['title']}** ({p['price']}):\n  👉 {p['url']}")
                reply_text = "\n".join(lines)
                matched_desc = ", ".join(p['title'] for p in matched_products)
        else:
            # Yapay Zeka (AI) Yanıtlayıcı Devreye Girsin (OpenRouter / Pollinations)
            brand_name = "Froxy" if is_froxy else ("LisansArena" if is_lisansarena else "KeyVadi")
            if not has_explicit_sales_intent(event.raw_text):
                print(f"[{client_name}] DM satış niyeti içermiyor, AI yanıtı atlandı.")
                return
            ai_res = get_ai_response(event.raw_text, brand_name, products)
            if ai_res:
                reply_text = ai_res
                matched_desc = "🤖 AI Akıllı Yanıt"

        if not reply_text:
            return
            
        try:
            await event.reply(reply_text)
            if msg_id:
                PROCESSED_DM_MSG_IDS.add(dedupe_key)
                if len(PROCESSED_DM_MSG_IDS) > 5000:
                    PROCESSED_DM_MSG_IDS.clear()
            USER_DM_LAST_REPLY_TIME[user_key] = now
            USER_DM_LAST_REPLY_TEXT[user_key] = normalized_text
            print(f"[{client_name}] ✉️ Özel mesaj otomatik yanıtlandı ({matched_desc}): @{sender.username or sender_id}")
        except Exception as e:
            print(f"[{client_name}] ⚠️ Özel mesaj otomatik yanıtlanırken hata: {e}")

DEAD_SESSION_ERRORS = (
    "AuthKeyDuplicatedError",
    "AuthKeyUnregisteredError",
    "SessionRevokedError",
    "UserDeactivatedError",
    "UserDeactivatedBanError",
)

# Slot -> (marka, Render ortam degiskeni). Oturum oldugunde hangi anahtarin
# yenilenmesi gerektigini loglarda acikca gostermek icin kullanilir.
SLOT_RECOVERY_HINTS = {
    1: ("Froxy", "AD_STRING_SESSION_FROXY"),
    2: ("KeyVadi", "AD_STRING_SESSION_KEYVADI"),
    3: ("LisansArena", "AD_STRING_SESSION_LISANSARENA"),
}


def report_client_error(slot, exc):
    """Oturum hatalarini ayirt edip ne yapilmasi gerektigini net sekilde yazar."""
    brand, env_var = SLOT_RECOVERY_HINTS.get(slot, (f"Hesap #{slot}", ""))
    name = type(exc).__name__
    if name in DEAD_SESSION_ERRORS:
        print(f"💀 {slot}. Hesap ({brand}) OTURUMU ÖLÜ: {name}")
        print(f"   ➜ Bu StringSession bir daha kullanılamaz; hesaba yeniden giriş yapıp")
        print(f"     yeni anahtarı Render'da {env_var} ortam değişkenine yazmanız gerekiyor.")
    else:
        print(f"❌ HATA: {slot}. Hesap ({brand}) bağlanırken hata oluştu: {name} - {exc}")


BEKLENEN_HESAPLAR = {'FroxyOnline', 'KeyVadiOnline', 'LisansArenaOnline'}


_last_eksik_alert_time = 0

async def uyar_eksik_hesap(ayakta, active_clients):
    global _last_eksik_alert_time
    import time
    eksik = sorted(BEKLENEN_HESAPLAR - set(ayakta))
    if not eksik or not active_clients:
        return
    # Throttle to once per 60 minutes max
    if time.time() - _last_eksik_alert_time < 3600:
        return
    _last_eksik_alert_time = time.time()
    admin_id = None
    try:
        if os.path.exists("bot_config.json"):
            with open("bot_config.json", "r", encoding="utf-8") as f_cfg:
                admin_id = json.load(f_cfg).get("admin_id")
    except Exception:
        pass
    mesaj = (
        "🚨 **Reklam hesabı düştü**\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"• Bağlanamayan: {', '.join(eksik)}\n"
        f"• Ayakta olan: {', '.join(sorted(ayakta)) or 'yok'}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "Oturum anahtarı geçersizleşmiş olabilir. Yeni anahtar üretip Render'da "
        "ilgili AD_STRING_SESSION_* değişkenini güncelleyin."
    )
    print(f"🚨 EKSİK HESAP: {eksik} — admine bildiriliyor.")
    if not admin_id:
        return

    # Bildirimi ayakta kalan reklam hesaplarindan biri gonderir.  KeyVadi
    # ayaktaysa oncelik onda; degilse sirayla digerleri denenir.
    sirali = sorted(active_clients,
                    key=lambda c: 0 if 'KeyVadi' in (c[1] or '') else 1)
    for client, name, _ in sirali:
        try:
            await client.send_message(int(admin_id), mesaj)
            print(f"📩 Eksik hesap bildirimi {name} hesabından gönderildi.")
            return
        except Exception:
            continue
    print("⚠️ Hiçbir hesap bildirimi gönderemedi.")


async def main():
    import psutil, os
    cur_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.info['pid'] != cur_pid and 'python' in (p.info['name'] or '').lower():
                cmd = ' '.join(p.info['cmdline'] or [])
                if 'otomatik_katil.py' in cmd:
                    print(f"🧹 Eski otomatik_katil.py (PID {p.info['pid']}) kapatılıyor...")
                    p.kill()
        except Exception:
            pass

    print("\n🚀 Habil Reklam Botu v2 - Akıllı Mod")
    print("-----------------------------------")

    string_session_key = ""
    string_session_key_2 = ""
    string_session_key_3 = ""
    ad_sleep_min = 600
    ad_sleep_max = 1200
    
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
                # Render env vars are the durable source of truth. The filesystem
                # is replaced on every deploy and may still contain stale sessions.
                # Uretimde config fallback kullanmak eski User/KeyVadiOnline
                # oturumlarini yeniden canlandirabildigi icin Render yalnizca
                # acikca tanimlanmis ortam degiskenlerini kabul eder.
                is_render_runtime = bool(
                    os.environ.get("RENDER")
                    or os.environ.get("RENDER_SERVICE_ID")
                    or os.environ.get("RENDER_EXTERNAL_URL")
                )
                env_froxy = os.environ.get("AD_STRING_SESSION_FROXY", "").strip()
                env_keyvadi = os.environ.get("AD_STRING_SESSION_KEYVADI", "").strip()
                env_lisans = os.environ.get("AD_STRING_SESSION_LISANSARENA", "").strip()
                if is_render_runtime:
                    string_session_key = env_froxy
                    string_session_key_2 = env_keyvadi
                    string_session_key_3 = env_lisans
                else:
                    string_session_key = env_froxy or cfg.get("string_session_key", "") or cfg.get("ad_string_session", "")
                    string_session_key_2 = env_keyvadi or cfg.get("string_session_key_2", "") or cfg.get("ad_string_session2_final", "") or cfg.get("ad_string_session2_new", "")
                    string_session_key_3 = env_lisans or cfg.get("string_session_key_3", "") or cfg.get("ad_string_session3_final", "") or cfg.get("ad_string_session3_new", "")
                ad_sleep_min = cfg.get("ad_sleep_min", 600)
                ad_sleep_max = cfg.get("ad_sleep_max", 1200)
        except:
            pass

    active_clients = []
    
    # Client 1
    if string_session_key:
        print("🔑 1. Hesap: StringSession kullanılarak bağlanılıyor...")
        try:
            from telethon.sessions import StringSession
            client1 = TelegramClient(StringSession(string_session_key), api_id, api_hash, timeout=20, connection_retries=-1, auto_reconnect=True, flood_sleep_threshold=5)
            await client1.connect()
            if await client1.is_user_authorized():
                me = await client1.get_me()
                active_clients.append((client1, "Hesap #1", {"id": me.id, "slot": 1}))
                print(f"✅ 1. Hesap yetkilendirildi ve aktif edildi. ID: {me.id}")
                client1.loop.create_task(presence_watchdog(client1))
            else:
                print("❌ HATA: 1. Hesap yetkilendirilmemiş!")
        except Exception as e:
            report_client_error(1, e)
            
    # Client 2
    if string_session_key_2:
        print("🔑 2. Hesap: StringSession kullanılarak bağlanılıyor...")
        try:
            from telethon.sessions import StringSession
            client2 = TelegramClient(StringSession(string_session_key_2), api_id, api_hash, timeout=20, connection_retries=-1, auto_reconnect=True, flood_sleep_threshold=5)
            await client2.connect()
            if await client2.is_user_authorized():
                me = await client2.get_me()
                active_clients.append((client2, "Hesap #2", {"id": me.id, "slot": 2}))
                print(f"✅ 2. Hesap yetkilendirildi. ID: {me.id}")
            else:
                print("❌ HATA: 2. Hesap (KeyVadi) yetkilendirilmemiş!")
        except Exception as e:
            report_client_error(2, e)

    # Client 3
    if string_session_key_3:
        print("🔑 3. Hesap (LisansArena): StringSession kullanılarak bağlanılıyor...")
        try:
            from telethon.sessions import StringSession
            client3 = TelegramClient(StringSession(string_session_key_3), api_id, api_hash, timeout=20, connection_retries=-1, auto_reconnect=True, flood_sleep_threshold=5)
            await client3.connect()
            if await client3.is_user_authorized():
                me = await client3.get_me()
                active_clients.append((client3, "Hesap #3", {"id": me.id, "slot": 3}))
                print(f"✅ 3. Hesap yetkilendirildi. ID: {me.id}")
            else:
                print("❌ HATA: 3. Hesap (LisansArena) yetkilendirilmemiş!")
        except Exception as e:
            report_client_error(3, e)

    # Fallback to local session file if no string session is configured at all
    if not string_session_key and not string_session_key_2 and not string_session_key_3:
        print("📂 Yerel oturum dosyası kullanılarak bağlanılıyor...")
        try:
            client1 = TelegramClient(SESSION_NAME, api_id, api_hash, timeout=20, connection_retries=-1, auto_reconnect=True, flood_sleep_threshold=5)
            await client1.connect()
            if await client1.is_user_authorized():
                me = await client1.get_me()
                active_clients.append((client1, "Yerel Hesap", {"id": me.id, "slot": None}))
                print(f"✅ Yerel hesap yetkilendirildi. ID: {me.id}")
            else:
                print("❌ HATA: Yerel hesap yetkilendirilmemiş!")
        except Exception as e:
            print(f"❌ HATA: Yerel hesap bağlanırken hata oluştu: {type(e).__name__} - {e}")
            import sys
            sys.exit(1)
            
    # Resolve the actual username before starting any handlers. This prevents
    # stale sessions in old slots from becoming advertising accounts again.
    allowed_clients = []
    for active_client, _, info in active_clients:
        try:
            me = await active_client.get_me()
            username = (getattr(me, 'username', '') or '').lower()
            identity = ACTIVE_ACCOUNT_IDENTITIES.get(username)
            if not identity:
                print(f"⚠️ @{username or 'bilinmeyen'} reklam hesabı izin listesinde değil; session bağlantısı kapatılıyor.")
                await active_client.disconnect()
                continue

            actual_slot = info.get('slot')
            expected_slot = identity['slot']
            if actual_slot is not None and actual_slot != expected_slot:
                print(f"⛔ @{username} yanlış oturum yuvasında (gelen={actual_slot}, beklenen={expected_slot}); bağlantı kapatılıyor.")
                await active_client.disconnect()
                continue

            expected_phone = normalize_phone(identity.get('phone'))
            actual_phone = normalize_phone(getattr(me, 'phone', ''))
            if expected_phone and actual_phone != expected_phone:
                print(f"⛔ @{username} telefon kimliği doğrulanamadı; bağlantı kapatılıyor.")
                await active_client.disconnect()
                continue

            expected_user_id = identity.get('user_id')
            if expected_user_id and me.id != expected_user_id:
                print(f"⛔ @{username} Telegram kullanıcı kimliği doğrulanamadı; bağlantı kapatılıyor.")
                await active_client.disconnect()
                continue

            stable_name = identity['stable_name']
            allowed_clients.append((active_client, stable_name, {
                'id': me.id,
                'username': username,
                'slot': expected_slot,
            }))
            print(f"🔒 @{username} kimliği doğrulandı ve {stable_name} hesabına kilitlendi.")
        except Exception as e:
            print(f"⚠️ Aktif hesap doğrulanamadı, bağlantı kapatılıyor: {e}")
            try:
                await active_client.disconnect()
            except Exception:
                pass
    active_clients = allowed_clients

    # Bir hesap dustugunde kimse fark etmiyordu; sistem sessizce iki hesapla
    # devam ediyordu.  Eksik hesap varsa admine Telegram'dan haber ver.
    await uyar_eksik_hesap({name for _, name, _ in active_clients}, active_clients)

    if not active_clients:
        print("❌ HATA: Hiçbir aktif ve yetkili Telegram hesabı bulunamadı! Watchdog kilitlenmesini önlemek için 10 dakika bekleniyor...")
        await asyncio.sleep(600)
        import sys
        sys.exit(1)

    # Sistem genelinde bizim olan User ID'lerin toplanması
    our_user_ids = set()
    for _, _, info in active_clients:
        if "id" in info:
            our_user_ids.add(info["id"])
            
    # bot_config.json dosyasından bot id'lerini ve admin id'lerini ayıkla
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for key, val in cfg.items():
                if ("token" in key.lower()) and isinstance(val, str) and ":" in val:
                    try:
                        bot_id = int(val.split(":")[0])
                        our_user_ids.add(bot_id)
                    except:
                        pass
            print(f"🔒 Sistem Hesap, Bot ve Admin Kimlikleri Kaydedildi: {list(our_user_ids)}")
        except Exception as e:
            print(f"⚠️ Bot/Admin ID'leri ayıklanırken hata: {e}")

    state_lock = asyncio.Lock()
    active_jobs = set()

    # Auto-DM: KALDIRILDI (sadece gruplara mesaj gönderilecek)

    # --- AUTO-SCRAPE: AKTİF ---
    first_client, first_name, _ = active_clients[0]

    async def setup_reference_channels_autoclean(client, client_name):
        """Ref kanallarından ilan mesajlarını temizler ve Rose Bot ekler."""
        ref_list = ["@FroxyReferans", "@KeyVadiReferans", "@LisansArenaReferans"]
        for ref_ch in ref_list:
            try:
                entity = await client.get_entity(ref_ch)
                # 1. Reklam mesajı temizleme
                async for msg in client.iter_messages(entity, limit=30):
                    txt = (msg.text or "").lower()
                    if any(kw in txt for kw in ["shopier.com", "satın alabilir", "fiyatı:", "keyvadisatisbot", "lisansarenabot", "otomatik teslimat"]):
                        try:
                            await client.delete_messages(entity, msg.id)
                            print(f"[{client_name}] 🧹 {ref_ch} kanalından eski ilan mesajı (ID {msg.id}) temizlendi.")
                        except Exception:
                            pass
                # 2. MissRose_bot ekleme ve admin yapma
                try:
                    rose = await client.get_input_entity("@MissRose_bot")
                    await client(InviteToChannelRequest(channel=entity, users=[rose]))
                    from telethon.tl.types import ChatAdminRights
                    rights = ChatAdminRights(
                        post_messages=True, delete_messages=True, ban_users=True,
                        invite_users=True, pin_messages=True, add_admins=False,
                        anonymous=False, manage_call=True, other=True
                    )
                    await client(EditAdminRequest(channel=entity, user_id=rose, admin_rights=rights, rank='Moderator'))
                    print(f"[{client_name}] 🌹 {ref_ch} kanalına MissRose_bot eklendi ve Admin yapıldı.")
                except Exception:
                    pass
            except Exception:
                pass

    async def run_worker(client, client_name, joined_dialogs):
        if account_brand(client_name) == 'keyvadi' or '2' in client_name or 'keyvadi' in client_name.lower():
            try:
                from telethon.tl.functions.account import UpdateProfileRequest
                await client(UpdateProfileRequest(
                    about="Referanslar: https://t.me/satisrefim/9615 | Bot: @KeyVadiSatisBot"
                ))
                print(f"✅ [{client_name}] KeyVadi hesabı biografisi güncellendi: https://t.me/satisrefim/9615")
            except Exception as e:
                print(f"⚠️ [{client_name}] Bio güncelleme uyarısı: {e}")

        protected_groups = get_all_protected_groups()
        cancelled_join_requests_handled = set()
        groups_left_handled = set()
        ref_channels_handled = set()
        
        VERIFIED_FILE = f"verified_groups_{client_name.replace(' ', '_').replace('#', '')}.json"
        MIN_UNIQUE_SENDERS = 10   # Grupta en az 10 farklı kişi yazmış olmalı
        MSG_CHECK_LIMIT = 50      # Son 50 mesaja bak
        VERIFY_TTL_HOURS = 24     # Doğrulanmış gruplar 24 saat geçerli

        async def check_group_activity(entity, group_key):
            """
            Son MSG_CHECK_LIMIT mesajı tara:
            - Kendi hesaplarımız hariç
            - Ardışık aynı kişi mesajları tek sayılır
            - Min MIN_UNIQUE_SENDERS farklı kişi yazmışsa True
            """
            try:
                unique_senders = set()
                last_sender = None
                async for msg in client.iter_messages(entity, limit=MSG_CHECK_LIMIT):
                    if not msg.sender_id:
                        continue
                    if msg.sender_id in our_user_ids:
                        continue  # Kendi hesaplarımızı sayıntıya katma
                    if msg.sender_id == last_sender:
                        continue  # Ardışık mesajlar sayma
                    last_sender = msg.sender_id
                    unique_senders.add(msg.sender_id)
                    if len(unique_senders) >= MIN_UNIQUE_SENDERS:
                        return True  # Yeterli, erken çık
                return len(unique_senders) >= MIN_UNIQUE_SENDERS
            except Exception as ae:
                print(f"[{client_name}] ⚠️ Aktivite kontrolü hatası ({group_key}): {ae}")
                return True  # Hata durumunda dahil et (kayıp yapmayız)

        async def cache_dialogs():
            nonlocal protected_groups
            protected_groups = get_all_protected_groups()
            print(f"🚀 [{client_name}] Diyaloglar önbelleğe alınıyor...")
            try:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                new_blacklisted_groups = []
                all_groups_info = []

                # Doğrulanmış grupları yükle (24 saatlik TTL)
                verified_groups = {}
                if os.path.exists(VERIFIED_FILE):
                    try:
                        with open(VERIFIED_FILE, 'r', encoding='utf-8') as vf:
                            verified_groups = json.load(vf)
                        # Süresi dolmuş kayıtları temizle
                        cutoff = now.timestamp() - VERIFY_TTL_HOURS * 3600
                        verified_groups = {k: v for k, v in verified_groups.items() if v > cutoff}
                    except:
                        verified_groups = {}

                
                # 'id' değerini koruyarak geri kalan anahtarları temizle
                me_id = joined_dialogs.get("id")
                joined_dialogs.clear()
                if me_id is not None:
                    joined_dialogs["id"] = me_id
                
                async for dialog in client.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        username_lower = dialog.entity.username.lower() if (hasattr(dialog.entity, 'username') and dialog.entity.username) else None
                        title = getattr(dialog.entity, 'title', '') or ''
                        member_count = getattr(dialog.entity, 'participants_count', None)
                        is_broadcast = getattr(dialog.entity, 'broadcast', False)
                        
                        dialog_id_str = str(dialog.id)
                        is_protected = False
                        if username_lower and username_lower in protected_groups:
                            is_protected = True
                        elif dialog_id_str in protected_groups:
                            is_protected = True

                        # ⚡ WHITELIST MODU DEVRE DIŞI: Kullanıcı katıldığı tüm gruplara göndermek istiyor.
                        # (Gruptan çıkma ve otomatik kara liste devre dışı bırakıldı)
                        pass

                        # Save in joined_dialogs under username (if any) and ID string
                        if username_lower:
                            joined_dialogs[username_lower] = dialog.entity
                        joined_dialogs[dialog_id_str] = dialog.entity
                        
                        # Korumalı grupları (sabit hedef listesi) doğrudan önbelleğe ekle ve geç
                        if is_protected:
                            if username_lower and username_lower in pending_invites:
                                pending_invites.remove(username_lower)
                            if dialog_id_str in pending_invites:
                                pending_invites.remove(dialog_id_str)
                            all_groups_info.append({
                                "username": dialog.entity.username or dialog_id_str,
                                "title": title,
                                "members": member_count,
                                "broadcast": is_broadcast,
                                "days_inactive": 0
                            })
                            continue
                        
                        # Otomatik Çıkma/Kara Liste Mantığı Kaldırıldı. Tüm grupları direkt ekle.
                        all_groups_info.append({
                            "username": dialog.entity.username or dialog_id_str,
                            "title": title,
                            "members": member_count,
                            "broadcast": is_broadcast,
                            "days_inactive": 0
                        })
                            
                # Grup bilgilerini dosyaya kaydet
                groups_file = f"cached_groups_{client_name.replace(' ', '_').replace('#', '')}.json"
                try:
                    with open(groups_file, 'w', encoding='utf-8') as f:
                        json.dump(all_groups_info, f, ensure_ascii=False, indent=2)
                except:
                    pass

                # Doğrulanmış grupları kaydet (24h TTL cache)
                try:
                    with open(VERIFIED_FILE, 'w', encoding='utf-8') as vf:
                        json.dump(verified_groups, vf, indent=2)
                    print(f"[{client_name}] ✅ {len(verified_groups)} aktif grup doğrulandı ve kaydedildi.")
                except:
                    pass

                
                if new_blacklisted_groups:
                    print(f"[{client_name}] 💾 {len(new_blacklisted_groups)} inaktif/küçük grup kara listeye kaydediliyor...")
                    async with state_lock:
                        # Tekrarları önlemek için birleştirip yazalım
                        existing_black = get_list(BLACKLIST_FILE)
                        new_to_write = [g for g in new_blacklisted_groups if g.lower() not in set(x.lower() for x in existing_black)]
                        if new_to_write:
                            with open(BLACKLIST_FILE, 'a', encoding='utf-8') as f:
                                for g in new_to_write:
                                    f.write(g + '\n')
                            try:
                                progress_content = ""
                                if os.path.exists(PROGRESS_FILE):
                                    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                                        progress_content = f.read()
                                blacklist_content = ""
                                if os.path.exists(BLACKLIST_FILE):
                                    with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                                        blacklist_content = f.read()
                                fs_set_state(progress_content, blacklist_content)
                            except Exception as fs_err:
                                print(f"⚠️ Firestore güncelleme hatası: {fs_err}")
                                
                print(f"✅ Worker {client_name}: {len(joined_dialogs)} diyalog önbelleğe alındı.")
            except FloodWaitError as e:
                set_account_restriction(client_name, e.seconds, 'Telegram diyalog önbelleği FloodWait', type(e).__name__, scope='send')
                print(f"🚨 Worker {client_name} önbellek aşamasında Flood yedi! Hesap {e.seconds} saniye duraklatıldı.")
            except Exception as e:
                print(f"⚠️ Worker {client_name} önbellek hatası: {e}")

        # ═══════════════════════════════════════════════════
        # BLAST MODE: Tüm gruplara aynı anda mesaj at
        # ═══════════════════════════════════════════════════
        while True:
            if os.path.exists("bot_config.json"):
                try:
                    with open("bot_config.json", "r", encoding="utf-8") as f:
                        cfg_chk = json.load(f)
                    if not cfg_chk.get("ad_bot_running", True):
                        print(f"🛑 [{client_name}] Panelde Reklam Botu kapatıldı (ad_bot_running=False). Döngü sonlandırılıyor.")
                        break
                except Exception:
                    pass

            if is_account_restricted(client_name, scope='send'):
                state = account_restriction_status(client_name, scope='send')
                print(f"[{client_name}] ⏸️ Hesap kısıtlaması aktif; {state.get('until', 'belirsiz')} tarihine kadar gönderim durdu.")
                await asyncio.sleep(60)
                continue

            # Her blast turu öncesi son blast zamanına bak.
            # Son blast üzerinden 1 saat geçmediyse kalan süreyi bekle, 1 saat geçtiyse hemen başla.
            rem_wait = get_last_blast_remaining_wait(client_name, target_wait_seconds=3600)
            if rem_wait > 0:
                elapsed_min = (3600 - rem_wait) // 60
                rem_min = rem_wait // 60
                print(f"\n[{client_name}] ⏳ Son yayın {elapsed_min}dk önce tamamlanmış → Kalan {rem_min}dk ({rem_wait}sn) bekleniyor...")
                kalan_wait = rem_wait
                while kalan_wait > 0:
                    dakika = kalan_wait // 60
                    saniye = kalan_wait % 60
                    if kalan_wait == rem_wait or kalan_wait % 60 == 0:
                        print(f"[{client_name}] ⏱️ Kalan: {dakika}dk {saniye}sn")
                    uyku = min(15, kalan_wait)
                    await asyncio.sleep(uyku)
                    kalan_wait -= uyku

            # Dinamik olarak korumalı listeyi güncelle
            protected_groups = get_all_protected_groups()
            
            # Her blast döngüsü başında diyalogları güncelle
            await cache_dialogs()

            # Referans kanali bakimi calisma basina BIR KEZ.  Her turda
            # calisirken 3 kanal x 3 hesap x 24 tur = gunde ~216 adet
            # channels.inviteToChannel + editAdmin istegi uretiyordu;
            # inviteToChannel Telegram'in PeerFlood'u en hizli tetikledigi
            # cagridir ve bu kanallar zaten bizim, her saat bakim gerekmiyor.
            if not ref_channels_handled:
                ref_channels_handled.add(client_name)
                await setup_reference_channels_autoclean(client, client_name)

            # Geri çekilmesi istenen talepleri runtime başına yalnızca bir kez
            # işle. Üye olan hesaplardan çıkış yapılmaz.
            for cancelled_group in CANCELLED_JOIN_REQUESTS - cancelled_join_requests_handled:
                await cancel_pending_join_request(client, client_name, joined_dialogs, cancelled_group)
                cancelled_join_requests_handled.add(cancelled_group)

            # Ayrilmasi istenen gruplardan cik (calisma basina bir kez).
            for leave_group in GROUPS_TO_LEAVE - groups_left_handled:
                groups_left_handled.add(leave_group)
                entity = joined_dialogs.get(normalize_group_key(leave_group))
                if not entity:
                    continue
                if is_group_protected(leave_group):
                    print(f"[{client_name}] ⚠️ @{leave_group} korumalı listede, çıkış yapılmadı.")
                    continue
                try:
                    await client(LeaveChannelRequest(entity))
                    joined_dialogs.pop(normalize_group_key(leave_group), None)
                    print(f"[{client_name}] 🚪 @{leave_group} grubundan çıkıldı (ayrılma listesi).")
                except Exception as le:
                    print(f"[{client_name}] ⚠️ @{leave_group} grubundan çıkılamadı: {type(le).__name__}")


            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            blacklist_lower.update(EXCLUDED_REFERENCE_CHANNELS)

            # Kara listeyi kanonik anahtara cevir.  Ayni grup hedef kumesinde hem
            # kullanici adiyla hem '-100...' diyalog kimligiyle duruyor; isim
            # karsilastirmasi ID bicimini yakalamiyordu ve tekillestirmede o
            # temsilci kazandiginda kara listedeki gruba reklam gidiyordu.
            blacklist_keys = set()
            for engelli in blacklist_lower:
                blacklist_keys.update(
                    group_state_keys(engelli, joined_dialogs.get(engelli)))

            # Hedef gruplar: Korumalı / Onaylı grupların hepsi + Hesabın üye olduğu tüm gruplar (Referans kanalları hariç)
            hedef_set = protected_groups.copy()
            for g_key in joined_dialogs:
                if g_key != "id" and not is_excluded_ad_target(g_key, joined_dialogs.get(g_key)):
                    hedef_set.add(g_key)
            hedef_set = {g for g in hedef_set if not is_excluded_ad_target(g, joined_dialogs.get(g.lower()))}

            # KeyVadiOnline target set (Original 13 + strictly indirim363 and kuponkodalimsatim)
            if client_name.lower() in ["keyvadionline", "hesap #2"]:
                keyvadi_allowed = {
                    "ticaretguvenilir", "kuponsatimalim", "indirimkodusatis", "yucekuponsatis",
                    "kuponindirimpazari", "sosyalmedyaalimsatimticaret", "nightsatis",
                    "kuponindirimsatis", "kuponsatisgrup", "kuponhesapsatis", "kuponceking",
                    "tahaaslan11", "alimsatimmerkezii", "indirim363", "kuponkodalimsatim"
                }
                hedef_set = {g for g in hedef_set if normalize_group_key(g) in keyvadi_allowed}

            print(f"[{client_name}] 📌 Toplam Gönderim Hedefi (Üye olunan + Korumalı): {len(hedef_set)} grup")
            
            # Önbellekte olan + kara listede olmayan hedef gruplar
            blast_targets = []
            seen_target_chat_ids = set()
            debug_blacklisted = 0
            debug_not_cached = 0
            small_groups_skipped = 0
            for username_lower in hedef_set:
                entity = joined_dialogs.get(username_lower)
                if (blacklist_keys.intersection(group_state_keys(username_lower, entity))
                        or is_excluded_ad_target(username_lower, entity)):
                    debug_blacklisted += 1
                    continue
                if username_lower in joined_dialogs:
                    entity = joined_dialogs[username_lower]
                    if getattr(entity, 'broadcast', False):
                        continue
                    member_count = getattr(entity, 'participants_count', None)
                    dedupe_key = target_dedupe_key(username_lower, entity)
                    if dedupe_key in seen_target_chat_ids:
                        continue
                    seen_target_chat_ids.add(dedupe_key)
                    blast_targets.append(username_lower)
                else:
                    debug_not_cached += 1
            # (Kapatıldı: Kullanıcı her hesabın katıldığı tüm gruplara göndermesini istiyor)
            # if len(active_clients) > 1:
            #     num_clients = len(active_clients)
            #     client_idx = 0
            #     for idx, (c, name, _) in enumerate(active_clients):
            #         if name == client_name:
            #             client_idx = idx
            #             break
            #     
            #     import hashlib
            #     def group_belongs_to_this_acc(gname):
            #         h = int(hashlib.md5(gname.encode('utf-8')).hexdigest(), 16)
            #         return (h % num_clients == client_idx)
            #     
            #     original_count = len(blast_targets)
            #     blast_targets = [g for g in blast_targets if group_belongs_to_this_acc(g)]
            #     print(f"[{client_name}] 🔀 İş yükü bölündü: {original_count} gruptan {len(blast_targets)} tanesi bu hesaba atandı.")
            pass

            
            print(f"[{client_name}] 📊 Hedef: {len(hedef_set)} | Gönderilecek: {len(blast_targets)} | Kara liste: {debug_blacklisted} | Küçük grup çıkar: {small_groups_skipped} | Üye değil: {debug_not_cached}")

            # Deploy/restart turun ortasinda olursa tur-sonu kaydi yazilamaz.
            # Gonderime baslamadan once bir guvenlik zamani yazmak, yeniden
            # acilan servisin ayni gruplara bastan blast atmasini engeller.
            if blast_targets:
                save_last_blast_time(client_name)
            
            update_ad_account_status(
                client_name,
                phase='sending' if blast_targets else 'idle',
                target_groups=len(hedef_set),
                sendable_groups=len(blast_targets),
                blacklisted_groups=debug_blacklisted,
                not_joined_groups=debug_not_cached,
            )

            # Sayaclar dongu govdesinde ilklenmeli: asagida bekleme suresini
            # belirleyen kosul bunlari okuyor ve blast_targets bos oldugunda
            # (yeni hesap, tum gruplar cooldown'da) tanimsiz kaliyorlardi ->
            # NameError -> worker cokup 60 saniyede bir yeniden basliyordu.
            sent_count = 0
            fail_count = 0

            if not blast_targets:
                print(f"[{client_name}] ⚠️ Önbellekte mesaj atılacak grup yok. Yeni gruplara katılma aşamasına geçiliyor...")
            else:
                print(f"\n[{client_name}] 🚀 BLAST MODE: {len(blast_targets)} gruba mesaj gönderiliyor!")
                
                # Aktif saat kontrolü
                from datetime import datetime, timezone, timedelta
                tr_time = datetime.now(timezone(timedelta(hours=3)))
                saat_durumu = is_active_hours()
                
                if saat_durumu == 'night':
                    print(f"[{client_name}] 🌙 TR saati {tr_time.strftime('%H:%M')} — Gece modu aktif, gönderim saat başı yapılacak.")
                elif saat_durumu == 'peak':
                    print(f"[{client_name}] 🔥 TR saati {tr_time.strftime('%H:%M')} — PEAK SAAT! Maksimum etkileşim bekleniyor.")
                elif saat_durumu == 'normal':
                    print(f"[{client_name}] 📤 TR saati {tr_time.strftime('%H:%M')} — normal saat, gönderim devam ediyor.")
                
                # Rotation updates: pick from variation templates if they exist
                is_keyv, is_lisans, is_froxy = account_flags(client_name)
                
                if is_lisans:
                    variations = LISANSARENA_MESSAGES
                    available_files = [v for v in variations if os.path.exists(v)]
                elif is_keyv:
                    variations = KEYVADI_MESSAGES
                    available_files = [v for v in variations if os.path.exists(v)]
                else:
                    variations = FROXY_MESSAGES
                    available_files = [v for v in variations if os.path.exists(v)]
                
                msg_history = load_msg_history()

                sent_count = 0
                fail_count = 0

                # Bu turda mesaj gonderilen gruplarin kanonik anahtarlari.
                # Her blast turunun basinda bosaltilir; ayni hesabin ayni gruba
                # tur icinde ikinci kez gondermesini kalici cooldown dosyasindan
                # bagimsiz olarak engeller (retry yolu dahil).
                sent_this_cycle = set()

                async def reset_failure(grup_name):
                    clear_group_failure(grup_name, client_name,
                                        joined_dialogs.get(grup_name.lower()))

                async def blast_one(grup_name, retry_count=0):
                    """Tek bir gruba rotasyonlu mesaj gönder"""
                    nonlocal sent_count, fail_count
                    if not await ensure_telegram_connection(client, client_name):
                        print(f"[{client_name}] Telegram bağlantısı yok, @{grup_name} bu turda atlanıyor.")
                        fail_count += 1
                        return
                    entity = joined_dialogs.get(grup_name.lower())
                    if not entity:
                        return
                    group_key = cooldown_key(grup_name, entity)
                    if group_key in sent_this_cycle:
                        print(f"[{client_name}] ⏭️ @{grup_name} bu turda zaten gönderildi, atlanıyor...")
                        return
                    if is_group_retry_blocked(grup_name, client_name, entity):
                        print(f"[{client_name}] ⏸️ @{grup_name} geçici/hesaba özel gönderim engelinde, atlanıyor...")
                        return

                    lock_claimed = False
                    async with state_lock:
                        if group_key in sent_this_cycle:
                            print(f"[{client_name}] ⏭️ @{grup_name} bu turda zaten gönderildi, atlanıyor...")
                            return
                        if is_on_cooldown(grup_name, client_name, entity):
                            print(f"[{client_name}] ⏳ @{grup_name} cooldown süresinde, atlanıyor...")
                            return
                        if not claim_send_lock(grup_name, client_name, entity=entity):
                            print(f"[{client_name}] 🔒 @{grup_name} gönderim kilidinde, bu turda atlanıyor...")
                            return
                        lock_claimed = True

                    retry_after = 0
                    try:
                        # Mesaj rotasyonu: bu grup için farklı mesaj seç
                        if available_files:
                            chosen_file = pick_message_for_group(grup_name, available_files, msg_history)
                            try:
                                with open(chosen_file, 'r', encoding='utf-8') as fm:
                                    base_msg = fm.read()
                            except:
                                base_msg = "Merhaba! Detaylar için @FroxyDestekBOT"
                        else:
                            base_msg = "Merhaba! Detaylar için @FroxyDestekBOT"
                        
                        is_keyvadi, is_lisansarena, is_froxy = account_flags(client_name)

                        msg = base_msg
                        is_short_group = is_short_ad_group(grup_name, entity)
                        if is_short_group:
                            msg = short_group_message(is_keyvadi, is_lisansarena, is_froxy)
                        elif grup_name.lower() == "kuponceking":
                            msg = msg.replace("bot", "sistem").replace("Bot", "Sistem") \
                                     .replace("🤖", "").strip() + "\n"
                        msg = parse_spintax(msg)
                        
                        # Pazarlama özellikleri (İndirim kodları, FOMO, Haftalık kampanya) ekle
                        msg = process_marketing_features(
                            msg, is_keyvadi, is_lisansarena, is_short=is_short_group
                        )
                        if is_short_group:
                            # Spintax sonrasinda da sert sinir uygula; bu gruba asla uzun
                            # normal-sablon veya ek kampanya blogu dusmez.
                            msg = short_group_message(is_keyvadi, is_lisansarena, is_froxy)
                        if is_spyforum_group(grup_name, entity):
                            # Grup filtresi "CC" ifadesini siliyor; yalnızca SpyForum'da
                            # urun adini Adobe olarak gonder.
                            msg = re.sub(r'(?i)\bAdobe\s+CC\b', 'Adobe', msg)
                        
                        # Görsel/Banner gönderimi (Grup yetki kontrolleri ve hata toleransı eklendi)
                        if is_keyvadi:
                            banner_file = "keyvadi_banner.png"
                        elif is_lisansarena:
                            banner_file = "lisansarena_banner.jpeg"
                        else:
                            banner_file = "froxy_banner.png"
                        allows_media = False
                        if os.path.exists("bot_config.json"):
                            try:
                                with open("bot_config.json", "r", encoding="utf-8") as f_cfg:
                                    cfg = json.load(f_cfg)
                                    allows_media = cfg.get("send_images", False)
                            except:
                                pass
                                
                        # Grup bazında görsel engeli var mı kontrol et
                        if allows_media:
                            try:
                                if hasattr(entity, 'default_banned_rights') and entity.default_banned_rights:
                                    if entity.default_banned_rights.send_media:
                                        print(f"[{client_name}] ⚠️ @{grup_name} grubunda görsel gönderimi yasaklı! Düz metin moduna geçiliyor.")
                                        allows_media = False
                            except Exception as e:
                                print(f"[{client_name}] ⚠️ @{grup_name} izin kontrol hatası: {e}")
                                
                        if is_short_group:
                            allows_media = False

                        if allows_media and os.path.exists(banner_file):
                            try:
                                if len(msg) <= 1024:
                                    await client.send_message(entity, msg, file=banner_file)
                                    chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                                    print(f"[{client_name}] 📸 @{grup_name} → Görselli Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                                else:
                                    # Karakter sınırı 1024'ü aşıyorsa görsel gönderme, sadece tek parça düz metin gönder
                                    await client.send_message(entity, msg)
                                    chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                                    print(f"[{client_name}] 📝 @{grup_name} → Karakter sınırı aşıldığı için görsel atlanarak Düz Metin Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                            except Exception as media_err:
                                print(f"[{client_name}] ⚠️ @{grup_name} grubuna görsel gönderilemedi ({media_err}). Düz metin olarak gönderiliyor...")
                                await client.send_message(entity, msg)
                                chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                                print(f"[{client_name}] ✅ @{grup_name} → Düz Metin Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                        else:
                            await client.send_message(entity, msg)
                            chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                            print(f"[{client_name}] ✅ @{grup_name} → Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                            
                        sent_count += 1
                        # Only mark the group after Telegram accepted the message.
                        set_cooldown(grup_name, client_name, entity)
                        sent_this_cycle.add(group_key)


                        update_stats(sent=1)
                        await reset_failure(grup_name)
                        async with state_lock:
                            save_to_list(grup_name, PROGRESS_FILE)
                    except FloodWaitError as e:
                        set_account_restriction(client_name, e.seconds, 'Telegram FloodWait', type(e).__name__, scope='send')
                        if e.seconds <= 300 and retry_count < 2:
                            retry_after = e.seconds + 2
                            print(
                                f"[{client_name}] ⏳ FloodWait {e.seconds}sn; "
                                f"@{grup_name} bekleme sonrası yeniden denenecek "
                                f"({retry_count + 1}/2)."
                            )
                        else:
                            record_group_failure(grup_name, client_name, 'FloodWait', e.seconds, entity)
                            print(f"[{client_name}] ⏳ FloodWait {e.seconds}sn; hesap duraklatıldı, grup kara listeye alınmadı.")
                            fail_count += 1
                    except (PeerFloodError, UserRestrictedError) as e:
                        restriction_seconds = 48 * 60 * 60
                        set_account_restriction(client_name, restriction_seconds, 'Telegram hesap/spam kısıtlaması', type(e).__name__, scope='send')
                        print(f"[{client_name}] 🚫 Hesap kısıtlaması algılandı ({type(e).__name__}); 48 saat duraklatıldı.")
                        fail_count += 1
                    except UserBannedInChannelError:
                        print(f"[{client_name}] ❌ @{grup_name} → Banlandık! Kara listeye ekleniyor...")
                        fail_count += 1
                        async with state_lock:
                            blacklist_group(grup_name, 'UserBannedInChannel', client_name)
                            record_group_failure(grup_name, client_name, 'UserBannedInChannel', 30 * 24 * 60 * 60, entity)
                        try:
                            if entity:
                                if is_group_protected(grup_name):
                                    print(f"⚠️ [Security] Korumalı/hedef grup @{grup_name} terk edilmesi engellendi!")
                                else:
                                    await client(LeaveChannelRequest(entity))
                                    print(f"[{client_name}] 🚪 @{grup_name} grubundan çıkıldı.")
                        except Exception as le:
                            print(f"[{client_name}] ⚠️ @{grup_name} grubundan çıkılırken hata: {le}")
                    except ChatWriteForbiddenError:
                        print(f"[{client_name}] 🔒 @{grup_name} → Yazma izni yok! Kara listeye ekleniyor...")
                        fail_count += 1
                        async with state_lock:
                            blacklist_group(grup_name, 'ChatWriteForbidden', client_name)
                            record_group_failure(grup_name, client_name, 'ChatWriteForbidden', 7 * 24 * 60 * 60, entity)
                        try:
                            if entity:
                                if is_group_protected(grup_name):
                                    print(f"⚠️ [Security] Korumalı/hedef grup @{grup_name} terk edilmesi engellendi!")
                                else:
                                    await client(LeaveChannelRequest(entity))
                                    print(f"[{client_name}] 🚪 @{grup_name} grubundan çıkıldı.")
                        except Exception as le:
                            print(f"[{client_name}] ⚠️ @{grup_name} grubundan çıkılırken hata: {le}")
                    except SlowModeWaitError as sme:
                        wait_sec = getattr(sme, 'seconds', 0) or 0
                        print(f"[{client_name}] 🐌 @{grup_name} → SlowMode aktif ({wait_sec}sn bekleme); geçici grup beklemesi yazıldı.")
                        record_group_failure(grup_name, client_name, 'SlowModeWait', wait_sec, entity)
                    except Exception as e:
                        err_type = type(e).__name__
                        print(f"[{client_name}] ⚠️ @{grup_name} → {err_type} (atlanıyor)")
                        fail_count += 1
                        if isinstance(e, (ConnectionError, TimeoutError)) or 'disconnected' in str(e).lower() or 'connection' in str(e).lower():
                            await ensure_telegram_connection(client, client_name, force=True)
                        record_group_failure(grup_name, client_name, err_type, 300, entity)
                    finally:
                        if lock_claimed:
                            async with state_lock:
                                release_send_lock(grup_name, client_name, entity)

                    if retry_after:
                        await asyncio.sleep(retry_after)
                        await blast_one(grup_name, retry_count + 1)

                # Gruplara sırayla ve aralarında 20-45 saniye rastgele bekleme (daha doğal)
                random.shuffle(blast_targets)  # Grup sırasını karıştır
                print(f"\n[{client_name}] 📤 Sırayla gönderim başlıyor ({len(blast_targets)} grup)...")
                for i, g in enumerate(blast_targets, 1):
                    await blast_one(g)
                    if i < len(blast_targets):
                        delay = random.randint(20, 45)
                        print(f"[{client_name}] ⏳ Sonraki grup için {delay} saniye bekleniyor...")
                        await asyncio.sleep(delay)
                
                # Mesaj geçmişini kaydet
                save_msg_history(msg_history)

                # Cooldown'lari hemen buluta yaz.  Periyodik senkron 5 dakikada
                # bir calisiyor; tur bitisi ile o senkron arasinda bir yeniden
                # baslatma olursa bu turun kayitlari kaybolur ve gruplara 1 saat
                # dolmadan tekrar mesaj gidebilir.
                try:
                    if os.path.exists(COOLDOWN_FILE):
                        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f_cd:
                            fs_set_state(cooldowns=f_cd.read())
                        print(f"[{client_name}] ☁️ Tur sonu cooldown kayıtları buluta yazıldı.")
                except Exception as e:
                    print(f"[{client_name}] ⚠️ Cooldown bulut yedeği alınamadı: {e}")

                update_ad_account_status(
                    client_name,
                    phase='completed',
                    target_groups=len(hedef_set),
                    sendable_groups=len(blast_targets),
                    sent_count=sent_count,
                    failed_count=fail_count,
                )
                
                print(f"\n[{client_name}] 📊 BLAST SONUÇ: {sent_count} başarılı, {fail_count} başarısız / {len(blast_targets)} toplam")

            # ═══════════════════════════════════════════════════
            # YENİ GRUPLARA KATILMA AŞAMASI (blast sonrası)
            # ═══════════════════════════════════════════════════
            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            not_joined = []
            for g in hedef_set:
                g_lower = g.lower()
                if g_lower not in joined_dialogs and g_lower not in blacklist_lower:
                    not_joined.append(g)
            
            if not_joined:
                join_count = 0
                print(f"\n[{client_name}] 🔍 {len(not_joined)} gruba henüz üye değiliz. Katılma başlıyor...")
                if is_account_restricted(client_name, scope='join'):
                    state = account_restriction_status(client_name, scope='join')
                    print(f"[{client_name}] ⏸️ Join kısıtı aktif; {state.get('until', 'belirsiz')} tarihine kadar yeni gruba katılım atlandı.")
                    not_joined = []
                for hedef_grup in not_joined:
                    if join_count >= 5:
                        print(f"[{client_name}] 🔒 Bu turda 5 gruba katılındı (limit), durduruluyor.")
                        break

                    # Kara listeyi katilim aninda tekrar oku.  Liste tur icinde
                    # degisebiliyor ve ban yedigimiz bir gruba yeniden girmek
                    # hesabin tekrar banlanmasina yol aciyor.  Karsilastirma
                    # kanonik anahtarla yapiliyor ki ID bicimi de yakalansin.
                    taze_engel = set()
                    for engelli in get_list(BLACKLIST_FILE):
                        taze_engel.update(
                            group_state_keys(engelli.lower(),
                                             joined_dialogs.get(engelli.lower())))
                    if taze_engel.intersection(
                            group_state_keys(hedef_grup, joined_dialogs.get(hedef_grup.lower()))):
                        print(f"[{client_name}] ⛔ @{hedef_grup} kara listede, katılım atlandı.")
                        continue

                    # Katilim istegi zaten gonderilmis ve admin onayi bekliyorsa
                    # tekrar isteme.  pending_invites dolduruluyordu ama hicbir
                    # yerde okunmuyordu: onay bekleyen tek bir grup her turda uc
                    # hesaptan yeni istek aliyordu (gunde ~72 istek), bu da hem
                    # grup yoneticisini rahatsiz ediyor hem PeerFlood riski.
                    if hedef_grup.lower() in pending_invites:
                        print(f"[{client_name}] ⏳ @{hedef_grup} katılım isteği zaten gönderilmiş, bekleniyor.")
                        continue

                    try:
                        is_hash = len(hedef_grup) == 16 and not hedef_grup.startswith('@') and not '/' in hedef_grup
                        
                        entity = None
                        if is_hash:
                            from telethon.tl.functions.messages import ImportChatInviteRequest
                            try:
                                updates = await client(ImportChatInviteRequest(hedef_grup))
                                if hasattr(updates, 'chats') and updates.chats:
                                    entity = updates.chats[0]
                                print(f"[{client_name}] ✅ Özel gruba katıldı: @{hedef_grup}")
                            except Exception as e_hash:
                                err_msg_hash = str(e_hash)
                                if 'UserAlreadyParticipant' in type(e_hash).__name__ or 'already' in err_msg_hash.lower():
                                    try:
                                        entity = await client.get_entity(hedef_grup)
                                    except:
                                        pass
                                else:
                                    raise e_hash
                        else:
                            entity = await client.get_entity(hedef_grup)
                            await client(JoinChannelRequest(entity))
                            print(f"[{client_name}] ✅ Gruba katıldı: @{hedef_grup}")
                            
                        if entity:
                            joined_dialogs[hedef_grup.lower()] = entity
                            join_count += 1
                            # Katılım isteği onaylandıysa/katılım sağlandıysa pending'den çıkar
                            if hedef_grup.lower() in pending_invites:
                                pending_invites.remove(hedef_grup.lower())
                                save_pending_invites(pending_invites)
                            await asyncio.sleep(random.randint(30, 90))
                            
                    except FloodWaitError as e:
                        set_account_restriction(client_name, e.seconds, 'Telegram katılım FloodWait', type(e).__name__, scope='join')
                        print(f"[{client_name}] ⚠️ Join flood {e.seconds}sn; hesap duraklatılıyor, grup kara listeye alınmadı.")
                        break
                    except (ChannelPrivateError,):
                        if hedef_grup.lower() not in protected_groups:
                            async with state_lock:
                                blacklist_group(hedef_grup, 'ChannelPrivate', client_name)
                            print(f"[{client_name}] ❌ @{hedef_grup} -> Kanal özel veya banlıyız, kara listeye alındı.")
                        else:
                            print(f"[{client_name}] ⚠️ Korumalı @{hedef_grup} özel/banlı, ancak korumalı olduğundan kara listeye ALINMADI.")
                    except Exception as e:
                        err_msg = str(e)
                        err_type = type(e).__name__
                        if 'UserBannedInChannel' in err_type or 'user_banned_in_channel' in err_msg.lower():
                            record_group_failure(hedef_grup, client_name, 'UserBannedInChannel', retry_after=86400)
                            print(f"[{client_name}] ⛔ @{hedef_grup} -> Bu hesap bu gruptan BANLANMIŞ. 24 saat boyunca denenmeyecek.")
                        elif 'ChannelsTooMuch' in err_type or 'channels_too_much' in err_msg.lower():
                            set_account_restriction(client_name, 86400, 'Telegram 500 kanal limitine ulaşıldı', err_type, scope='join')
                            print(f"[{client_name}] 🚨 Telegram 500 kanal/grup limitine ulaşıldı! Katılım aşaması durduruluyor.")
                            break
                        elif 'InviteRequestSent' in err_type or 'invite' in err_msg.lower():
                            pending_invites.add(hedef_grup.lower())
                            save_pending_invites(pending_invites)
                            print(f"[{client_name}] ⏳ @{hedef_grup} -> Katılım isteği gönderildi (onay bekleniyor).")
                        elif 'no user has' in err_msg.lower() or isinstance(e, (UsernameNotOccupiedError, UsernameInvalidError, ValueError)):
                            if hedef_grup.lower() not in protected_groups:
                                async with state_lock:
                                    blacklist_group(hedef_grup, err_type, client_name)
                                print(f"[{client_name}] ❌ @{hedef_grup} -> {err_type} (Kullanıcı/Grup yok), kara liste.")
                            else:
                                print(f"[{client_name}] ⚠️ Korumalı @{hedef_grup} bulunamadı, ancak korumalı olduğundan kara listeye ALINMADI.")
                        else:
                            print(f"[{client_name}] ⚠️ @{hedef_grup} -> {err_type} (Hata: {err_msg})")

            # Progress sıfırla (bir sonraki blast için)
            async with state_lock:
                if os.path.exists(PROGRESS_FILE):
                    os.remove(PROGRESS_FILE)
                try:
                    blacklist_content = ""
                    if os.path.exists(BLACKLIST_FILE):
                        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                            blacklist_content = f.read()
                    fs_set_state("", blacklist_content)
                except:
                    pass
            
            # TR Saatine göre bekleme süresi ayarı
            from datetime import datetime, timezone, timedelta
            tr_time = datetime.now(timezone(timedelta(hours=3)))
            hour = tr_time.hour
            
            grup_sayisi = len(blast_targets) if blast_targets else 0
            # Gece/gunduz ayrimindan once her tamamlanan turun kesin zamanini
            # yaz. Onceki kod gece dalinda hic kaydetmedigi icin dongu beklemeden
            # tekrar blast'a girebiliyordu.
            save_last_blast_time(client_name)
            # Gece (02:00 - 07:59) saat başı (3600 sn), diğer saatlerde 30 dakikada bir (1800 sn)
            if 2 <= hour <= 7:
                bekleme = 3600
                print(f"\n[{client_name}] 🌙 Gece modu aktif (TR {tr_time.strftime('%H:%M')}) → Sonraki blast 1 saat sonra")
            else:
                blast_min = 3600
                blast_max = 3600
                if os.path.exists("bot_config.json"):
                    try:
                        with open("bot_config.json", "r", encoding="utf-8") as f_cfg:
                            cfg = json.load(f_cfg)
                            blast_min = cfg.get("blast_wait_min", 3600)
                            blast_max = cfg.get("blast_wait_max", 3600)
                    except:
                        pass
                bekleme = random.randint(blast_min, blast_max)
                print(f"\n[{client_name}] 🎉 Blast turu başarıyla tamamlandı ({grup_sayisi} grup) → Sonraki blast 60 dakika sonra gerçekleşecek.")

    # Migrate legacy group decisions before syncing Firestore, otherwise the
    # old cloud blacklist could immediately reintroduce invalid entries.
    migrate_legacy_blacklist_once()

    # İlk çalıştırmada Firestore'dan verileri çek
    print("🔄 Firestore'dan güncel durum yükleniyor...")
    fs_prog, fs_black, fs_auto, fs_scraped, fs_cooldowns, fs_welcomed = fs_get_state()
    if fs_prog:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            f.write(fs_prog)
        print("📥 İlerleme durumu buluttan indirildi.")
    if fs_black:
        local_black = get_list(BLACKLIST_FILE)
        remote_black = set(x.strip() for x in fs_black.splitlines() if x.strip())
        merged_black = local_black if os.path.exists(BLACKLIST_MIGRATION_MARKER) else local_black.union(remote_black)
        merged_black = {g for g in merged_black if not is_group_protected(g)}
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_black) + '\n')
        print("📥 Kara liste buluttan indirildi, korumalılar filtrelendi ve birleştirildi.")
    if fs_auto:
        with open(AUTO_GROUPS_FILE, 'w', encoding='utf-8') as f:
            f.write(fs_auto)
        print("📥 Otomatik keşfedilen gruplar buluttan indirildi (onaylı listeye eklenmedi).")
    if fs_scraped:
        local_scraped = get_list("scraped_groups.txt")
        remote_scraped = set(x.strip() for x in fs_scraped.splitlines() if x.strip())
        merged_scraped = local_scraped.union(remote_scraped)
        with open("scraped_groups.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_scraped) + '\n')
        print("📥 Keşfedilen grup geçmişi buluttan indirildi ve birleştirildi.")
    if fs_cooldowns:
        with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
            f.write(fs_cooldowns)
        print("📥 Cooldown geçmişi buluttan indirildi.")
    if fs_welcomed:
        global welcomed_users
        try:
            remote_welcomed = set(x.strip() for x in fs_welcomed.splitlines() if x.strip())
            welcomed_users = welcomed_users.union(remote_welcomed)
            with open("welcomed_users.json", "w", encoding="utf-8") as f:
                json.dump(list(welcomed_users), f)
            print("📥 Karşılanan kullanıcılar geçmişi buluttan indirildi.")
        except Exception as e:
            print(f"⚠️ Karşılanan kullanıcı yükleme hatası: {e}")

    # Periyodik arka plan görevleri
    async def periodic_firestore_sync():
        print("🔄 [Firestore Sync] Periyodik senkronizasyon görevi başlatıldı (5 dk aralıklarla).")
        while True:
            await asyncio.sleep(300)
            try:
                print("🔄 [Firestore Sync] Firestore'dan güncel durum yükleniyor...")
                _, fs_black_new, fs_auto_new, fs_scraped_new, fs_cooldowns_new, fs_welcomed_new = fs_get_state()
                if fs_black_new:
                    local_black = get_list(BLACKLIST_FILE)
                    remote_black = set(x.strip() for x in fs_black_new.splitlines() if x.strip())
                    merged_black = local_black if os.path.exists(BLACKLIST_MIGRATION_MARKER) else local_black.union(remote_black)
                    # Korumali listeden dolayi kara liste BUDANMAZ.  Bir grubu
                    # hem hedef listesinde hem kara listede tutmak celiskidir ve
                    # cozumu kara listeyi silmek degil, hedeften cikarmaktir.
                    # Onceki davranis, elle eklenen haric tutmalari 5 dakikada
                    # bir sessizce siliyordu.
                    celiskili = {g for g in merged_black if is_group_protected(g)}
                    if celiskili:
                        print(f"⚠️ [Firestore Sync] Hem hedef hem kara listede olan gruplar "
                              f"kara listede BIRAKILDI: {sorted(celiskili)}")
                    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(sorted(merged_black)) + '\n')
                if fs_auto_new:
                    with open(AUTO_GROUPS_FILE, 'w', encoding='utf-8') as f:
                        f.write(fs_auto_new)
                if fs_scraped_new:
                    local_scraped = get_list("scraped_groups.txt")
                    remote_scraped = set(x.strip() for x in fs_scraped_new.splitlines() if x.strip())
                    merged_scraped = local_scraped.union(remote_scraped)
                    with open("scraped_groups.txt", 'w', encoding='utf-8') as f:
                        f.write('\n'.join(merged_scraped) + '\n')
                if fs_welcomed_new:
                    global welcomed_users
                    try:
                        remote_welcomed = set(x.strip() for x in fs_welcomed_new.splitlines() if x.strip())
                        welcomed_users = welcomed_users.union(remote_welcomed)
                        with open("welcomed_users.json", "w", encoding="utf-8") as f:
                            json.dump(list(welcomed_users), f)
                    except:
                        pass
                
                # Cooldown listesini buluta yedekle
                if os.path.exists(COOLDOWN_FILE):
                    with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
                        cooldowns_content = f.read()
                    fs_set_state(cooldowns=cooldowns_content)
                    print("🔄 [Firestore Sync] Cooldown geçmişi bulutla eşitlendi.")
            except Exception as e:
                print(f"⚠️ [Firestore Sync] Hata: {e}")

    async def periodic_scraper(client, client_name):
        if account_brand(client_name) == 'froxy':
            print(f"🔍 [{client_name}] Grup keşfi kapalı; Froxy yalnızca mevcut/onaylı hedefleri kullanacak.")
            return
        print("🔍 [Scraper Task] Periyodik grup tarama görevi başlatıldı (6 saat aralıklarla).")
        while True:
            # 6 saat bekle ama her 15 saniyede bir flag dosyasını kontrol et (acil tetikleyici)
            kalan = 21600  # 6 saat = 21600 saniye
            while kalan > 0:
                if os.path.exists("trigger_scraper.flag"):
                    print("⚡ [Scraper Task] TETİKLEYİCİ: 'trigger_scraper.flag' tespit edildi! Anlık tarama başlatılıyor...")
                    try:
                        os.remove("trigger_scraper.flag")
                    except:
                        pass
                    joined_usernames = set()
                    try:
                        async for dialog in client.iter_dialogs():
                            if dialog.is_group or dialog.is_channel:
                                username = getattr(dialog.entity, 'username', None)
                                if username:
                                    joined_usernames.add(username.lower())
                    except:
                        pass
                    await auto_scrape_groups(client, client_name, joined_usernames)
                await asyncio.sleep(15)
                kalan -= 15
            
            # Periyodik tarama
            print("🔄 [Scraper Task] 6 saat doldu, periyodik tarama başlıyor...")
            joined_usernames = set()
            try:
                async for dialog in client.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        username = getattr(dialog.entity, 'username', None)
                        if username:
                            joined_usernames.add(username.lower())
            except:
                pass
            await auto_scrape_groups(client, client_name, joined_usernames)

    async def run_startup_scraper(client, client_name):
        if account_brand(client_name) == 'froxy':
            print(f"🔍 [{client_name}] Başlangıç grup taraması kapalı; mevcut/onaylı hedefler kullanılacak.")
            return
        await asyncio.sleep(5)  # Let workers start and cache dialogs first
        print(f"🔍 [{client_name}] Başlangıç grup taraması arka planda başlatılıyor...")
        joined_usernames = set()
        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    username = getattr(dialog.entity, 'username', None)
                    if username:
                        joined_usernames.add(username.lower())
            print(f"✅ [{client_name}] {len(joined_usernames)} adet mevcut grup tespit edildi. Bunlar aramada es geçilecek.")
        except Exception as e:
            print(f"⚠️ [{client_name}] Startup Scraper: Mevcut gruplar alınırken hata: {e}")
        await auto_scrape_groups(client, client_name, joined_usernames)

    async def run_worker_supervisor(client, client_name, joined_dialogs):
        if "2" in client_name:
            await asyncio.sleep(2)
        elif "3" in client_name:
            await asyncio.sleep(5)
        while True:
            try:
                await run_worker(client, client_name, joined_dialogs)
            except Exception as e:
                import traceback
                print(f"🚨 [Supervisor] {client_name} çöktü: {e}")
                traceback.print_exc()
                print("⏳ [Supervisor] 60 saniye sonra worker yeniden başlatılıyor...")
                await asyncio.sleep(60)

    async def update_account_bios(client, name):
        if account_brand(name) == 'keyvadi' or '2' in name or 'keyvadi' in name.lower():
            try:
                from telethon.tl.functions.account import UpdateProfileRequest
                await client(UpdateProfileRequest(
                    about="Referanslar & Müşteri Yorumları: https://t.me/satisrefim/7287 | Sipariş: @KeyVadiSatisBot"
                ))
                print(f"✅ [{name}] KeyVadi hesabı biografisi güncellendi: https://t.me/satisrefim/7287")
            except Exception as e:
                print(f"⚠️ [{name}] Bio güncelleme uyarısı: {e}")

    # Workers ve arka plan görevlerini başlat
    tasks = []
    for client, name, j_dialogs in active_clients:
        register_admin_handler(client, name, j_dialogs)
        register_auto_reply_handler(client, name, our_user_ids)
        register_telegram_code_forwarder(client, name)
        tasks.append(update_account_bios(client, name))
        tasks.append(run_worker_supervisor(client, name, j_dialogs))
        tasks.append(connection_watchdog(client, name))
    
    # Scraper tasks disabled: All accounts strictly use their assigned target group lists.
    tasks.append(periodic_firestore_sync())
    
    # Tüm görevleri eşzamanlı olarak çalıştır
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
