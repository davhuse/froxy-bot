import asyncio
import random
import os
import json
import re
import requests
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest, SearchRequest
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, UsernameNotOccupiedError, 
    UsernameInvalidError, ChannelPrivateError, ChatWriteForbiddenError,
    SlowModeWaitError, UserBannedInChannelError
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
    # Kullanıcının verdiği gruplar
    "kuponceking", "kuponsatislari0", "sosyalmedyaalimsatimticaret", "ticaretguvenilir",
    "kuponsatisgrup", "dijitalilan", "kuponceksatis", "ticaretsaha", "IWEfTGD7OCBjY2I8",
    "satilikilanlar", "diyarbakirikincielarac", "smmpanelgrup", "kuponhesapsatis",
    "YuceKuponSatis", "ticaretforumofficial", "referansreklam1", "Nightsatis",
    "kuponsat", "indirimkodusatis", "dolapdestek0",
]


STATS_FILE = 'stats.json'

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

def process_marketing_features(msg, is_keyvadi):
    import datetime
    import random
    import os
    
    # 1. Haftalık Ürün Kampanyası (Sadece KeyVadi için)
    if is_keyvadi:
        weekly_campaigns = [
            {
                "message_addon": "🔥 **HAFTANIN DEV FIRSATI:** Adobe Creative Cloud (Tüm Uygulamalar) 1 Yıllık Yetkilendirme 149.99 TL yerine sadece **79.99 TL!**"
            },
            {
                "message_addon": "🎨 **HAFTANIN DEV FIRSATI:** Canva Pro Sınırsız Tasarım Yetkisi (1 Yıllık) 79.99 TL yerine sadece **39.99 TL!**"
            },
            {
                "message_addon": "🍔 **HAFTANIN FIRSATI:** Trendyol Yemek (700 TL'ye 250 TL İndirim Kuponu) 49.99 TL yerine sadece **24.99 TL!**"
            }
        ]
        
        try:
            week_no = datetime.datetime.now().isocalendar()[1]
            campaign = weekly_campaigns[week_no % len(weekly_campaigns)]
            addon = campaign["message_addon"]
            
            lines = msg.splitlines()
            if len(lines) >= 3:
                lines.insert(2, "\n" + addon + "\n")
                msg = "\n".join(lines)
            else:
                msg = addon + "\n\n" + msg
        except Exception as e:
            print(f"⚠️ Kampanya ekleme hatası: {e}")

    # 2. Promosyon Kodu ve FOMO (Aciliyet) Ekleme
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    bugun_no = datetime.datetime.now().weekday()
    bugun_adi = gunler[bugun_no]
    
    if is_keyvadi:
        kodlar = ["KEYVADI10", "KEY10", "FIRSAT10"]
        fomolar = [
            f"Bugün ({bugun_adi}) geçerli",
            "Kısa süreliğine geçerli",
            "Bu haftaya özel",
            "Sadece bugün geçerli",
        ]
    else:
        kodlar = ["FROXY20", "AI20", "REKLAM20"]
        fomolar = [
            f"Bugün ({bugun_adi}) geçerli",
            "Kısa süreliğine geçerli",
            "Bu haftaya özel",
            "Sadece bugün geçerli",
        ]
        
    chosen_kod = random.choice(kodlar)
    chosen_fomo = random.choice(fomolar)
    
    # Eger sablon icinde tag'ler varsa degistir
    has_tags = "{KOD}" in msg or "{FOMO}" in msg
    if has_tags:
        msg = msg.replace("{BUGUN}", bugun_adi)
        msg = msg.replace("{KOD}", chosen_kod)
        msg = msg.replace("{FOMO}", chosen_fomo)
    else:
        # Tag yoksa mesajın sonuna yeni bir satır olarak ekle
        discount = "10%" if is_keyvadi else "20%"
        promo_line = f"\n🎟️ **{chosen_fomo}:** `{chosen_kod}` koduyla **%{discount} indirim** fırsatını kaçırma!"
        lines = msg.splitlines()
        if len(lines) >= 2:
            lines.insert(-1, promo_line)
            msg = "\n".join(lines)
        else:
            msg += "\n" + promo_line
            
    return msg


# Auto discovered groups
if os.path.exists("auto_groups.txt"):
    with open("auto_groups.txt", "r", encoding="utf-8") as f:
        auto_g = [x.strip() for x in f.read().splitlines() if x.strip()]
        for g in auto_g:
            if g not in gruplar:
                gruplar.append(g)


PROGRESS_FILE = 'progress.txt'
BLACKLIST_FILE = 'blacklist.txt'
AUTO_GROUPS_FILE = 'auto_groups.txt'
MESSAGES_DIR = 'messages'
MSG_HISTORY_FILE = 'msg_history.json'
COOLDOWN_FILE = 'group_cooldown.json'
GROUP_COOLDOWN_HOURS = 24  # Bir gruba mesaj gönderdikten sonra kaç saat beklenecek

NEGATIVE_KEYWORDS = [
    "sigara", "vape", "puff", "tütün", "likit", "shisha", "nargile", "elektronik sigara", "elektroniksigara",
    "ayakkabı", "ayakkabi", "giyim", "butik", "moda", "elbise", "çanta", "canta",
    "brawl", "pubg", "valorant", "clash", "roblox", "free fire", "mobile legends", "metin2", "knight online",
    "korg", "pa800", "pa2x", "pa600", "pa900", "orgcu", "müzik", "muzik", "enstrüman",
    "gürcistan", "gurcistan", "batum", "tiflisi",
    "escort", "sex", "porno", "ifşa", "ifsa", "adult", "travesti",
    "film", "dizi", "izle", "sinema", "warez",
    "bahis", "iddaa", "casino", "kumar", "rulet", "bet", "kazan", "tahmin",
]

# --- Auto-DM: Yanıt veren kullanıcıları takip et ---
replied_users = set()
pending_invites = set() # Yeni: Katılım isteği gönderilen grupları takip etmek için
dm_count_today = 0
dm_last_reset = ""
MAX_DM_PER_DAY = 20

# --- Auto-DM: Anahtar kelimeler ---
DM_TRIGGER_KEYWORDS = [
    "yapay zeka", "chatgpt", "claude", "gemini", "ai ", " ai",
    "gpt", "deepseek", "canva", "adobe", "lisans", "premium hesap",
    "kupon", "indirim", "trendyol", "capcut",
]

# --- Grup Cooldown Sistemi ---
def load_cooldowns():
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cooldowns(data):
    try:
        with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def is_on_cooldown(grup_name, cooldowns):
    """Gruba son mesaj gönderilmesinden bu yana yeterince süre geçti mi?"""
    from datetime import datetime
    key = grup_name.lower()
    if key not in cooldowns:
        return False
    try:
        last_sent = datetime.fromisoformat(cooldowns[key])
        elapsed = (datetime.now() - last_sent).total_seconds() / 3600
        return elapsed < GROUP_COOLDOWN_HOURS
    except:
        return False

def set_cooldown(grup_name, cooldowns):
    """Gruba mesaj gönderildi olarak işaretle"""
    from datetime import datetime
    cooldowns[grup_name.lower()] = datetime.now().isoformat()

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
    os.path.join(MESSAGES_DIR, 'keyvadi_ai.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_kupon.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_adobe.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_ogrenci.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_deal.txt'),
    os.path.join(MESSAGES_DIR, 'keyvadi_genel.txt'),
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

def pick_message_for_group(grup_name, msg_files, history):
    """Grup için son gönderilen mesajdan farklı bir mesaj seç"""
    last_used = history.get(grup_name.lower(), "")
    available = [f for f in msg_files if f != last_used]
    if not available:
        available = msg_files  # Hepsi kullanıldıysa sıfırla
    chosen = random.choice(available)
    history[grup_name.lower()] = chosen
    return chosen

def is_active_hours():
    """TR saatlerinde aktif saatleri kontrol et (UTC+3)"""
    from datetime import datetime, timezone, timedelta
    tr_time = datetime.now(timezone(timedelta(hours=3)))
    hour = tr_time.hour
    # Peak saatler: 12:00-14:00 ve 19:00-23:59 (en yüksek etkileşim)
    # Normal saatler: 00:00-02:59 ve 07:00-11:59 ve 15:00-18:59
    # Ölü saatler: 03:00-06:59 (mesaj kaybolur, atılmaz)
    if (12 <= hour <= 14) or (19 <= hour <= 23):
        return 'peak'
    elif (3 <= hour <= 6):
        return 'dead'
    else:
        return 'normal'

def minutes_until_active():
    """Ölü saatlerden aktif saate kaç dakika kaldığını hesapla"""
    from datetime import datetime, timezone, timedelta
    tr_time = datetime.now(timezone(timedelta(hours=3)))
    hour = tr_time.hour
    minute = tr_time.minute
    # 07:00'a kaç dakika?
    if hour < 7:
        return (7 - hour) * 60 - minute
    return 0  # Zaten aktif

# --- Auto-Scrape: Anahtar kelimeler (genişletilmiş) ---
SCRAPE_KEYWORDS = [
    # Genel ticaret
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "ikinci el", "2.el satış", "alim satim",
    "e-ticaret satış", "trendyol satıcı", "freelance iş",
    "referans reklam", "satılık ilan", "epin satış",
    # AI ve yazılım
    "yapay zeka", "chatgpt türkçe", "ai araçları", "ai tools",
    "adobe lisans", "canva pro", "premium hesap",
    "lisans satış", "yazılım indirim",
    # Kupon ve indirim
    "trendyol indirim", "trendyol kupon", "yemek kuponu",
    "indirim kodu", "promosyon kodu", "kampanya kodu",
    # Freelance ve dijital
    "freelancer türkiye", "dijital pazarlama", "sosyal medya yönetimi",
    "instagram takipçi", "youtube abone", "tiktok takipçi",
    # Oyun hesapları
    "pubg hesap", "brawl stars hesap", "valorant hesap",
    "oyun hesap satış", "game account",
    # Genel satış
    "telefon satış", "elektronik satış", "kozmetik satış",
    "toptan satış türkiye", "pazar yeri",
]

async def auto_scrape_groups(client, client_name):
    """Telegram global aramasıyla yeni, aktif ve kaliteli Türkçe satış grupları keşfeder."""
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
                if custom_kw and len(custom_kw) > 0:
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
    blacklist = get_list(BLACKLIST_FILE)
    blacklist_lower = set(b.lower() for b in blacklist)
    new_found = 0
    blacklisted_count = 0
    
    # Türkçe satış grubu olup olmadığını kontrol etmek için kelimeler
    sales_keywords = [
        "satış", "satis", "ticaret", "ilan", "reklam", "kupon", "indirim",
        "shopier", "hesap", "alım", "satım", "alim", "satim", "smm", "kod",
        "ucuz", "ref", "pazar", "ikinci el", "brawl", "pubg", "takipçi",
        "lisans", "premium", "freelance", "dijital", "adobe", "canva",
        "trendyol", "kampanya", "fırsat", "firsat", "oyun", "epin",
        "kozmetik", "toptan", "e-ticaret", "yapay zeka", "ai",
    ]
    
    # Günde 1 kez çalıştığı için TÜM keyword'leri tara (karıştırarak)
    DAILY_GROUP_LIMIT = 50  # Günlük maksimum yeni grup sayısı
    selected_keywords = keywords_list.copy()
    random.shuffle(selected_keywords)
    print(f"🔎 [{client_name}] Günlük tarama: {len(selected_keywords)} anahtar kelime, max {DAILY_GROUP_LIMIT} yeni grup hedefi")
    
    from telethon.tl.types import Channel, Chat
    
    for keyword in selected_keywords:
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
                    
                # Yayın kanallarını kara listeye al
                if not is_group or not chat.username:
                    if isinstance(chat, Channel) and getattr(chat, 'broadcast', False) and chat.username:
                        username = chat.username.lower()
                        if username not in blacklist_lower:
                            save_to_list(chat.username, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                    continue
                    
                username = chat.username.lower()
                if username in existing_groups or username in blacklist_lower:
                    continue
                    
                member_count = getattr(chat, 'participants_count', None)
                title = (chat.title or "").lower()
                
                # === FİLTRE 1: Üye sayısı (500'den az = zaman kaybı) ===
                if member_count is not None and member_count < 500:
                    if username not in blacklist_lower:
                        save_to_list(chat.username, BLACKLIST_FILE)
                        blacklist_lower.add(username)
                        keyword_blacklisted += 1
                        print(f"  🚫 @{chat.username} → Üye az ({member_count}), kara liste")
                    continue
                
                # === FİLTRE 2: Başlık dil/alaka/negatif kontrolü ===
                has_sales_word = any(w in title for w in sales_keywords)
                has_negative = any(w in title for w in NEGATIVE_KEYWORDS)
                
                if has_negative or not has_sales_word:
                    if username not in blacklist_lower:
                        save_to_list(chat.username, BLACKLIST_FILE)
                        blacklist_lower.add(username)
                        keyword_blacklisted += 1
                        print(f"  🚫 @{chat.username} → Alakasız/yabancı/negatif ('{chat.title}'), kara liste")
                    continue
                
                # === FİLTRE 3: Derin kalite taraması (son 5 mesaj) ===
                try:
                    recent_msgs = await client.get_messages(chat, limit=5)
                    
                    if not recent_msgs or len(recent_msgs) == 0:
                        if username not in blacklist_lower:
                            save_to_list(chat.username, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                            print(f"  🚫 @{chat.username} → Boş grup (mesaj yok), kara liste")
                        continue
                    
                    # İnaktiflik kontrolü (5 gün)
                    from datetime import datetime, timezone
                    now_utc = datetime.now(timezone.utc)
                    last_msg_date = recent_msgs[0].date
                    delta_days = (now_utc - last_msg_date).days
                    if delta_days >= 5:
                        if username not in blacklist_lower:
                            save_to_list(chat.username, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                            print(f"  🚫 @{chat.username} → İnaktif ({delta_days} gün), kara liste")
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
                            save_to_list(chat.username, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                            print(f"  🗑️ @{chat.username} → Spam çöplüğü ({bot_mention_count}/5 bot reklamı), kara liste")
                        continue
                    
                    # Son 5 mesajda sadece 1-2 unique gönderen → ölü grup
                    if len(recent_msgs) >= 5 and len(unique_senders) <= 2:
                        if username not in blacklist_lower:
                            save_to_list(chat.username, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                            print(f"  💀 @{chat.username} → Ölü grup ({len(unique_senders)} kişi aktif), kara liste")
                        continue
                    
                except Exception:
                    pass
                    
                # === TÜM FİLTRELERİ GEÇTİ — KALİTELİ GRUP ===
                with open(AUTO_GROUPS_FILE, 'a', encoding='utf-8') as f:
                    f.write(chat.username + '\n')
                existing_groups.add(username)
                gruplar.append(chat.username)
                new_found += 1
                keyword_found += 1
                print(f"  🆕 KALİTELİ GRUP: @{chat.username} (Üye: {member_count or '?'}, Başlık: '{chat.title}')")
                
            summary = f"'{keyword}': +{keyword_found} yeni"
            if keyword_blacklisted > 0:
                summary += f", {keyword_blacklisted} kara listeye alındı"
            print(f"  📊 [{client_name}] {summary}")
            blacklisted_count += keyword_blacklisted
            await asyncio.sleep(3)
                
        except FloodWaitError as e:
            print(f"⏳ [{client_name}] Auto-Scraper: Flood beklenecek ({e.seconds}s)...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ [{client_name}] Auto-Scraper hatası ('{keyword}'): {type(e).__name__} - {e}")
            
    if new_found > 0:
        update_stats(discovered=new_found)
    
    print(f"\n📊 [{client_name}] Scraper Sonuç: {new_found} yeni kaliteli grup eklendi, {blacklisted_count} çöp grup kara listeye alındı.")
        
    return new_found

# Akıllı DM Mesaj Şablonları (anahtar kelimeye göre)
DM_TEMPLATES = {
    "ai": (
        "Merhaba 👋\n\n"
        "Yapay zeka ile ilgili mesajınızı gördüm. "
        "ChatGPT, Claude, Gemini ve 400+ AI modelini tek panelden kullanabilirsiniz — "
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
            return progress, blacklist, auto_groups
    except Exception as e:
        print(f"⚠️ Firestore yükleme hatası: {e}")
    return "", "", ""

def fs_set_state(progress=None, blacklist=None, auto_groups=None):
    try:
        if progress is None:
            progress = ""
            if os.path.exists(PROGRESS_FILE):
                with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    progress = f.read()
                    
        if blacklist is None:
            blacklist = ""
            if os.path.exists(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                    blacklist = f.read()
                    
        if auto_groups is None:
            auto_groups = ""
            if os.path.exists(AUTO_GROUPS_FILE):
                with open(AUTO_GROUPS_FILE, 'r', encoding='utf-8') as f:
                    auto_groups = f.read()
                    
        url = f"{BASE_URL}/reklam/state?key={API_KEY}"
        fields = {
            "progress_list": {"stringValue": progress},
            "blacklist_list": {"stringValue": blacklist},
            "auto_groups_list": {"stringValue": auto_groups}
        }
        requests.patch(url, json={"fields": fields}, timeout=10)
    except Exception as e:
        print(f"⚠️ Firestore kaydetme hatası: {e}")

def get_list(dosya):
    if os.path.exists(dosya):
        with open(dosya, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_list(grup, dosya):
    with open(dosya, 'a', encoding='utf-8') as f:
        f.write(grup + '\n')
    
    # Firestore durum eşitlemesi
    try:
        fs_set_state()
    except Exception as e:
        print(f"⚠️ Firestore güncelleme hatası: {e}")

async def main():
    print("\n🚀 Habil Reklam Botu v2 - Akıllı Mod")
    print("-----------------------------------")

    string_session_key = ""
    string_session_key_2 = ""
    ad_sleep_min = 600
    ad_sleep_max = 1200
    
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                string_session_key = cfg.get("ad_string_session", "")
                string_session_key_2 = cfg.get("ad_string_session_2", "")
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
            client1 = TelegramClient(StringSession(string_session_key), api_id, api_hash)
            await client1.connect()
            if await client1.is_user_authorized():
                me = await client1.get_me()
                active_clients.append((client1, "Hesap #1", {"id": me.id}))
                print(f"✅ 1. Hesap yetkilendirildi ve aktif edildi. ID: {me.id}")
            else:
                print("❌ HATA: 1. Hesap yetkilendirilmemiş!")
        except Exception as e:
            print(f"❌ HATA: 1. Hesap bağlanırken hata oluştu: {type(e).__name__} - {e}")
            
    # Client 2
    if string_session_key_2:
        print("🔑 2. Hesap: StringSession kullanılarak bağlanılıyor...")
        try:
            from telethon.sessions import StringSession
            client2 = TelegramClient(StringSession(string_session_key_2), api_id, api_hash)
            await client2.connect()
            if await client2.is_user_authorized():
                me = await client2.get_me()
                active_clients.append((client2, "Hesap #2", {"id": me.id}))
                print(f"✅ 2. Hesap yetkilendirildi. ID: {me.id}")
            else:
                print("❌ HATA: 2. Hesap yetkilendirilmemiş!")
        except Exception as e:
            print(f"❌ HATA: 2. Hesap bağlanırken hata oluştu: {type(e).__name__} - {e}")

    # Fallback to local session file if no string session is configured at all
    if not string_session_key and not string_session_key_2:
        print("📂 Yerel oturum dosyası kullanılarak bağlanılıyor...")
        try:
            client1 = TelegramClient(SESSION_NAME, api_id, api_hash)
            await client1.connect()
            if await client1.is_user_authorized():
                me = await client1.get_me()
                active_clients.append((client1, "Yerel Hesap", {"id": me.id}))
                print(f"✅ Yerel hesap yetkilendirildi. ID: {me.id}")
            else:
                print("❌ HATA: Yerel hesap yetkilendirilmemiş!")
        except Exception as e:
            print(f"❌ HATA: Yerel hesap bağlanırken hata oluştu: {type(e).__name__} - {e}")
            import sys
            sys.exit(1)
            
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
            
    # bot_config.json dosyasından bot id'lerini ayıkla
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for key in ["bot_token", "froxy_bot_token"]:
                token = cfg.get(key, "")
                if token and ":" in token:
                    bot_id = int(token.split(":")[0])
                    our_user_ids.add(bot_id)
            print(f"🔒 Sistem Hesap ve Bot Kimlikleri Kaydedildi: {list(our_user_ids)}")
        except Exception as e:
            print(f"⚠️ Bot ID'leri ayıklanırken hata: {e}")

    state_lock = asyncio.Lock()
    active_jobs = set()

    # Auto-DM: KALDIRILDI (sadece gruplara mesaj gönderilecek)

    # --- AUTO-SCRAPE: AKTİF ---
    first_client, first_name, _ = active_clients[0]
    scrape_count = await auto_scrape_groups(first_client, first_name)
    if scrape_count > 0:
        print(f"🎉 Auto-Scraper toplamda {scrape_count} yeni grup ekledi. Liste güncellendi!")

    async def run_worker(client, client_name, joined_dialogs):
        protected_groups = set(g.lower() for g in gruplar)
        
        async def cache_dialogs():
            print(f"🚀 [{client_name}] Diyaloglar önbelleğe alınıyor...")
            try:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                new_blacklisted_groups = []
                all_groups_info = []
                
                # 'id' değerini koruyarak geri kalan anahtarları temizle
                me_id = joined_dialogs.get("id")
                joined_dialogs.clear()
                if me_id is not None:
                    joined_dialogs["id"] = me_id
                
                async for dialog in client.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        if hasattr(dialog.entity, 'username') and dialog.entity.username:
                            username_lower = dialog.entity.username.lower()
                            title = getattr(dialog.entity, 'title', '') or ''
                            member_count = getattr(dialog.entity, 'participants_count', None)
                            is_broadcast = getattr(dialog.entity, 'broadcast', False)
                            
                            is_protected = username_lower in protected_groups
                            
                            # Korumalı grupları (sabit hedef listesi) doğrudan önbelleğe ekle ve geç
                            if is_protected:
                                joined_dialogs[username_lower] = dialog.entity
                                # Katılım isteği onaylandıysa bekleme listesinden temizle
                                if username_lower in pending_invites:
                                    pending_invites.remove(username_lower)
                                all_groups_info.append({
                                    "username": dialog.entity.username,
                                    "title": title,
                                    "members": member_count,
                                    "broadcast": is_broadcast,
                                    "days_inactive": 0
                                })
                                continue
                            
                            # Otomatik Çıkma/Kara Liste Mantığı Kaldırıldı. Tüm grupları direkt ekle.
                            joined_dialogs[username_lower] = dialog.entity
                            all_groups_info.append({
                                "username": dialog.entity.username,
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
                print(f"🚨 Worker {client_name} önbellek aşamasında Flood yedi! {e.seconds} saniye bekleniyor...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"⚠️ Worker {client_name} önbellek hatası: {e}")

        # ═══════════════════════════════════════════════════
        # BLAST MODE: Tüm gruplara aynı anda mesaj at
        # ═══════════════════════════════════════════════════
        while True:
            # Dinamik olarak korumalı listeyi güncelle
            protected_groups = set(g.lower() for g in gruplar)
            
            # Her blast döngüsü başında diyalogları güncelle
            await cache_dialogs()
            
            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            
            # Hedef gruplar: gruplar listesi + auto_groups.txt
            hedef_set = set(g.lower() for g in gruplar)
            if os.path.exists("auto_groups.txt"):
                try:
                    with open("auto_groups.txt", "r", encoding="utf-8") as f:
                        for line in f:
                            g = line.strip()
                            if g:
                                hedef_set.add(g.lower())
                except:
                    pass
            
            # Önbellekte olan + kara listede olmayan hedef gruplar
            blast_targets = []
            debug_blacklisted = 0
            debug_not_cached = 0
            for username_lower in hedef_set:
                if username_lower in blacklist_lower:
                    debug_blacklisted += 1
                    continue
                if username_lower in joined_dialogs:
                    entity = joined_dialogs[username_lower]
                    if getattr(entity, 'broadcast', False):
                        continue
                    blast_targets.append(username_lower)
                else:
                    debug_not_cached += 1
            
            print(f"[{client_name}] 📊 Hedef: {len(hedef_set)} | Gönderilecek: {len(blast_targets)} | Kara liste: {debug_blacklisted} | Üye değil: {debug_not_cached}")
            
            if not blast_targets:
                print(f"[{client_name}] ⚠️ Önbellekte mesaj atılacak grup yok. Yeni gruplara katılma aşamasına geçiliyor...")
            else:
                print(f"\n[{client_name}] 🚀 BLAST MODE: {len(blast_targets)} gruba mesaj gönderiliyor!")
                
                # Aktif saat kontrolü
                from datetime import datetime, timezone, timedelta
                tr_time = datetime.now(timezone(timedelta(hours=3)))
                saat_durumu = is_active_hours()
                
                if saat_durumu == 'dead':
                    bekle_dk = minutes_until_active()
                    print(f"[{client_name}] 🌙 TR saati {tr_time.strftime('%H:%M')} — ölü saat. Mesaj kaybolur, {bekle_dk} dk sonra (07:00'da) blast başlayacak.")
                    await asyncio.sleep(bekle_dk * 60)
                    continue  # Döngü başına dön, saati tekrar kontrol et
                elif saat_durumu == 'peak':
                    print(f"[{client_name}] 🔥 TR saati {tr_time.strftime('%H:%M')} — PEAK SAAT! Maksimum etkileşim bekleniyor.")
                elif saat_durumu == 'normal':
                    print(f"[{client_name}] 📤 TR saati {tr_time.strftime('%H:%M')} — normal saat, gönderim devam ediyor.")
                
                # Mesaj rotasyonu: hangi hesap için hangi şablonlar?
                is_keyvadi = "2" in client_name
                msg_files = KEYVADI_MESSAGES if is_keyvadi else FROXY_MESSAGES
                
                # Mevcut şablonları kontrol et, yoksa eski dosyaya fallback
                available_files = [f for f in msg_files if os.path.exists(f)]
                if not available_files:
                    # Fallback: eski mesaj dosyası
                    fallback = "message_2.txt" if is_keyvadi else "message.txt"
                    if os.path.exists(fallback):
                        available_files = [fallback]
                    else:
                        available_files = []
                
                msg_history = load_msg_history()

                sent_count = 0
                fail_count = 0
                
                async def record_failure(grup_name):
                    async with state_lock:
                        try:
                            failures = {}
                            if os.path.exists("group_failures.json"):
                                with open("group_failures.json", "r", encoding="utf-8") as f:
                                    failures = json.load(f)
                            g_key = grup_name.lower()
                            failures[g_key] = failures.get(g_key, 0) + 1
                            with open("group_failures.json", "w", encoding="utf-8") as f:
                                json.dump(failures, f, indent=4)
                            
                            # 3 kez üst üste hata aldıysa uyar ama kara listeye alma ve gruptan çıkma
                            if failures[g_key] >= 3:
                                print(f"[{client_name}] ⚠️ @{grup_name} -> 3 kez üst üste hata alındı, ancak gruptan çıkılmadı ve kara listeye alınmadı.")
                        except Exception as fe:
                            print(f"⚠️ Hata sayacı güncelleme hatası: {fe}")

                async def reset_failure(grup_name):
                    async with state_lock:
                        try:
                            failures = {}
                            if os.path.exists("group_failures.json"):
                                with open("group_failures.json", "r", encoding="utf-8") as f:
                                    failures = json.load(f)
                            g_key = grup_name.lower()
                            if g_key in failures and failures[g_key] > 0:
                                failures[g_key] = 0
                                with open("group_failures.json", "w", encoding="utf-8") as f:
                                    json.dump(failures, f, indent=4)
                        except:
                            pass

                async def blast_one(grup_name):
                    """Tek bir gruba rotasyonlu mesaj gönder"""
                    nonlocal sent_count, fail_count
                    entity = joined_dialogs.get(grup_name.lower())
                    if not entity:
                        return
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
                        
                        msg = base_msg
                        if grup_name.lower() == "kuponceking":
                            msg = msg.replace("bot", "sistem").replace("Bot", "Sistem") \
                                     .replace("🤖", "").strip() + "\n"
                        msg = parse_spintax(msg)
                        
                        # Pazarlama özellikleri (İndirim kodları, FOMO, Haftalık kampanya) ekle
                        is_keyvadi = "2" in client_name
                        msg = process_marketing_features(msg, is_keyvadi)
                        
                        # Görsel/Banner gönderimi (Grup izin veriyorsa)
                        banner_file = "keyvadi_banner.png" if is_keyvadi else "froxy_banner.png"
                        allows_media = True
                        if hasattr(entity, 'default_banned_rights') and entity.default_banned_rights:
                            if getattr(entity.default_banned_rights, 'send_media', False):
                                allows_media = False
                                
                        if allows_media and os.path.exists(banner_file) and len(msg) <= 1024:
                            await client.send_message(entity, msg, file=banner_file)
                            chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                            print(f"[{client_name}] 📸 @{grup_name} → Görselli Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                        else:
                            await client.send_message(entity, msg)
                            chosen_name = os.path.basename(chosen_file) if available_files else "fallback"
                            print(f"[{client_name}] ✅ @{grup_name} → Gönderildi! ({sent_count+1}) [Şablon: {chosen_name}]")
                            
                        sent_count += 1

                        update_stats(sent=1)
                        await reset_failure(grup_name)
                        async with state_lock:
                            save_to_list(grup_name, PROGRESS_FILE)
                    except FloodWaitError as e:
                        if e.seconds <= 30:
                            await asyncio.sleep(e.seconds)
                            try:
                                if allows_media and os.path.exists(banner_file) and len(msg) <= 1024:
                                    await client.send_message(entity, msg, file=banner_file)
                                else:
                                    await client.send_message(entity, msg)
                                sent_count += 1

                                print(f"[{client_name}] ✅ @{grup_name} → Gönderildi (flood sonrası)!")
                                update_stats(sent=1)
                                await reset_failure(grup_name)
                            except:
                                fail_count += 1
                                await record_failure(grup_name)
                        else:
                            print(f"[{client_name}] ⏳ @{grup_name} → Flood {e.seconds}sn, atlanıyor...")
                            fail_count += 1
                    except UserBannedInChannelError:
                        print(f"[{client_name}] ❌ @{grup_name} → Banlandık!")
                        fail_count += 1
                        await record_failure(grup_name)
                    except ChatWriteForbiddenError:
                        print(f"[{client_name}] 🔒 @{grup_name} → Yazma izni yok")
                        fail_count += 1
                        await record_failure(grup_name)
                    except SlowModeWaitError:
                        print(f"[{client_name}] 🐌 @{grup_name} → SlowMode, atlanıyor.")
                        fail_count += 1
                    except Exception as e:
                        err_type = type(e).__name__
                        print(f"[{client_name}] ⚠️ @{grup_name} → {err_type} (atlanıyor)")
                        fail_count += 1
                        await record_failure(grup_name)

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
                
                print(f"\n[{client_name}] 📊 BLAST SONUÇ: {sent_count} başarılı, {fail_count} başarısız / {len(blast_targets)} toplam")

            # ═══════════════════════════════════════════════════
            # YENİ GRUPLARA KATILMA AŞAMASI (blast sonrası)
            # ═══════════════════════════════════════════════════
            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            not_joined = [g for g in gruplar if g.lower() not in blacklist_lower and g.lower() not in joined_dialogs and g.lower() not in pending_invites]
            
            if not_joined:
                join_count = 0
                print(f"\n[{client_name}] 🔍 {len(not_joined)} gruba henüz üye değiliz. Katılma başlıyor...")
                for hedef_grup in not_joined:
                    if join_count >= 15:
                        print(f"[{client_name}] 🔒 Bu turda 15 gruba katılındı, durduruluyor.")
                        break
                    
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
                            member_count = getattr(entity, 'participants_count', None)
                            # Üye sayısı limit kontrolü (Gruptan çıkma/kara listeye alma devre dışı bırakıldı)
                            if member_count is not None and member_count < 50:
                                print(f"[{client_name}] 📉 @{hedef_grup} -> Üye az ({member_count}), ancak gruptan çıkılmadı.")
                                
                            joined_dialogs[hedef_grup.lower()] = entity
                            join_count += 1
                            # Katılım isteği onaylandıysa/katılım sağlandıysa pending'den çıkar
                            if hedef_grup.lower() in pending_invites:
                                pending_invites.remove(hedef_grup.lower())
                            await asyncio.sleep(random.randint(5, 15))
                            
                    except FloodWaitError as e:
                        if e.seconds <= 60:
                            await asyncio.sleep(e.seconds)
                        else:
                            print(f"[{client_name}] ⚠️ Join flood {e.seconds}sn, katılma durduruluyor.")
                            break
                    except (ChannelPrivateError,):
                        if hedef_grup.lower() not in protected_groups:
                            async with state_lock:
                                save_to_list(hedef_grup, BLACKLIST_FILE)
                            print(f"[{client_name}] ❌ @{hedef_grup} -> Kanal özel veya banlıyız, kara listeye alındı.")
                        else:
                            print(f"[{client_name}] ⚠️ Korumalı @{hedef_grup} özel/banlı, ancak korumalı olduğundan kara listeye ALINMADI.")
                    except Exception as e:
                        err_msg = str(e)
                        err_type = type(e).__name__
                        if 'InviteRequestSent' in err_type or 'invite' in err_msg.lower():
                            pending_invites.add(hedef_grup.lower())
                            print(f"[{client_name}] ⏳ @{hedef_grup} -> Katılım isteği gönderildi (onay bekleniyor).")
                        elif 'no user has' in err_msg.lower() or isinstance(e, (UsernameNotOccupiedError, UsernameInvalidError, ValueError)):
                            if hedef_grup.lower() not in protected_groups:
                                async with state_lock:
                                    save_to_list(hedef_grup, BLACKLIST_FILE)
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
            
            # Dinamik bekleme: grup sayısı + saat dilimine göre
            grup_sayisi = len(blast_targets) if blast_targets else 0
            saat_durumu = is_active_hours()
            
            if saat_durumu == 'peak':
                # Peak saatlerde daha sık blast (etkileşim yüksek)
                if grup_sayisi <= 10:
                    bekleme = random.randint(480, 600)      # 8-10 dk
                elif grup_sayisi <= 30:
                    bekleme = random.randint(540, 720)       # 9-12 dk
                elif grup_sayisi <= 50:
                    bekleme = random.randint(600, 900)       # 10-15 dk
                else:
                    bekleme = random.randint(900, 1200)       # 15-20 dk
                print(f"\n[{client_name}] 🔥 PEAK SAAT — {grup_sayisi} gruba blast atıldı → Sonraki blast {bekleme // 60} dk sonra")
            else:
                # Normal saatlerde standart aralık
                if grup_sayisi <= 10:
                    bekleme = random.randint(600, 720)      # 10-12 dk
                elif grup_sayisi <= 30:
                    bekleme = random.randint(600, 900)       # 10-15 dk
                elif grup_sayisi <= 50:
                    bekleme = random.randint(900, 1200)      # 15-20 dk
                else:
                    bekleme = random.randint(1200, 1500)      # 20-25 dk
                print(f"\n[{client_name}] ⏳ {grup_sayisi} gruba blast atıldı → Sonraki blast {bekleme // 60} dk sonra")
            # Geri sayım (her dakika yazdır)
            kalan = bekleme
            while kalan > 0:
                dakika = kalan // 60
                saniye = kalan % 60
                if kalan == bekleme or kalan % 60 == 0:
                    print(f"[{client_name}] ⏱️ Kalan: {dakika}dk {saniye}sn")
                uyku = min(15, kalan)
                await asyncio.sleep(uyku)
                kalan -= uyku

    # İlk çalıştırmada Firestore'dan verileri çek
    print("🔄 Firestore'dan güncel durum yükleniyor...")
    fs_prog, fs_black, fs_auto = fs_get_state()
    if fs_prog:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            f.write(fs_prog)
        print("📥 İlerleme durumu buluttan indirildi.")
    if fs_black:
        # Sadece birleştirip kaydediyoruz, sabit grupları silme mantığı KALDIRILDI
        local_black = get_list(BLACKLIST_FILE)
        remote_black = set(x.strip() for x in fs_black.splitlines() if x.strip())
        merged_black = local_black.union(remote_black)
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_black) + '\n')
        print("📥 Kara liste buluttan indirildi ve birleştirildi.")
    if fs_auto:
        with open(AUTO_GROUPS_FILE, 'w', encoding='utf-8') as f:
            f.write(fs_auto)
        print("📥 Otomatik keşfedilen gruplar buluttan indirildi.")
        auto_g = [x.strip() for x in fs_auto.splitlines() if x.strip()]
        for g in auto_g:
            if g not in gruplar:
                gruplar.append(g)

    # Periyodik arka plan görevleri
    async def periodic_firestore_sync():
        print("🔄 [Firestore Sync] Periyodik senkronizasyon görevi başlatıldı (5 dk aralıklarla).")
        while True:
            await asyncio.sleep(300)
            try:
                print("🔄 [Firestore Sync] Firestore'dan güncel durum yükleniyor...")
                _, fs_black_new, fs_auto_new = fs_get_state()
                if fs_black_new:
                    local_black = get_list(BLACKLIST_FILE)
                    remote_black = set(x.strip() for x in fs_black_new.splitlines() if x.strip())
                    merged_black = local_black.union(remote_black)
                    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(merged_black) + '\n')
                if fs_auto_new:
                    auto_g = [x.strip() for x in fs_auto_new.splitlines() if x.strip()]
                    new_added = 0
                    for g in auto_g:
                        if g not in gruplar:
                            gruplar.append(g)
                            new_added += 1
                    if new_added > 0:
                        print(f"📥 [Firestore Sync] Buluttan {new_added} yeni otomatik grup eklendi.")
                        with open(AUTO_GROUPS_FILE, 'w', encoding='utf-8') as f:
                            f.write(fs_auto_new)
            except Exception as e:
                print(f"⚠️ [Firestore Sync] Hata: {e}")

    async def periodic_scraper(client, client_name):
        print("🔍 [Scraper Task] Günlük grup tarama görevi başlatıldı (24 saat aralıklarla).")
        while True:
            # 24 saat bekle ama her 15 saniyede bir flag dosyasını kontrol et (acil tetikleyici)
            kalan = 86400  # 24 saat = 86400 saniye
            while kalan > 0:
                if os.path.exists("trigger_scraper.flag"):
                    print("⚡ [Scraper Task] TETİKLEYİCİ: 'trigger_scraper.flag' tespit edildi! Anlık tarama başlatılıyor...")
                    try:
                        os.remove("trigger_scraper.flag")
                    except:
                        pass
                    await auto_scrape_groups(client, client_name)
                await asyncio.sleep(15)
                kalan -= 15
            
            # Günlük periyodik tarama
            print("🔄 [Scraper Task] 24 saat doldu, günlük tarama başlıyor...")
            await auto_scrape_groups(client, client_name)

    # Workers ve arka plan görevlerini başlat
    tasks = []
    for client, name, j_dialogs in active_clients:
        tasks.append(run_worker(client, name, j_dialogs))
    
    # Scraper ve Firestore sync'i arka planda çalıştır
    first_client, first_name, _ = active_clients[0]
    tasks.append(periodic_scraper(first_client, first_name))
    tasks.append(periodic_firestore_sync())
    
    # Tüm görevleri eşzamanlı olarak çalıştır
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
