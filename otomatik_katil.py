import asyncio
import random
import os
import json
import re
import requests
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
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
    # Kullanıcının onayladığı hedef gruplar (12 Haziran 2026 güncellemesi)
    "ticaretforumofficial",
    "sultanbeyliikinciel0",
    "tahaaslan11",
    "casinox_grup",
    "ReklamOnliene",
    "alimsatimmerkezii",
    "illegalalimsatimerkezi",
    "ilanticaret",
    "reklamreferans",
    "sosyalmedyaalimsatimticaret",
    "ReferansReklamYardimlasma",
    "sanalalimsatimticaret",
    "kuponsatisgrup",
    "referansreklam1",
    "referanslinkpaylasimigrup",
    "kuponsatislari0",
    "YuceKuponSatis",
    "letgoilanlari",
    "kuponkodalsat",
    "-1001572316417",  # Serbest Ticaret Grubu (1515 üye)
    "-3608209943",     # DERGAH (1582 üye)
    "ticar4t",
    "kuponhesapsatis",
    "reklamvereferanss",
    "kuponvekodsatisgrubu",
    "indirimkodusatis",
]

def get_all_protected_groups():
    protected = set(g.lower() for g in gruplar)
    if os.path.exists("auto_groups.txt"):
        try:
            with open("auto_groups.txt", "r", encoding="utf-8") as f:
                for line in f:
                    g = line.strip().lower()
                    if g:
                        protected.add(g)
        except:
            pass
    return protected

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



PROGRESS_FILE = 'progress.txt'
BLACKLIST_FILE = 'blacklist.txt'
AUTO_GROUPS_FILE = 'auto_groups.txt'
MESSAGES_DIR = 'messages'
MSG_HISTORY_FILE = 'msg_history.json'
COOLDOWN_FILE = 'group_cooldown.json'
GROUP_COOLDOWN_HOURS = 2  # Varsayılan: 2 saat ortak cooldown. Config'den ezilebilir.
if os.path.exists("bot_config.json"):
    try:
        with open("bot_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            GROUP_COOLDOWN_HOURS = cfg.get("group_cooldown_hours", 2)
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

def is_on_cooldown(grup_name):
    """Gruba son mesaj gönderilmesinden bu yana yeterince süre geçti mi (herhangi bir hesap tarafından)?"""
    from datetime import datetime
    cooldowns = load_cooldowns()
    key = grup_name.lower()
    if key not in cooldowns:
        return False
    try:
        last_sent = datetime.fromisoformat(cooldowns[key])
        elapsed = (datetime.now() - last_sent).total_seconds() / 3600
        return elapsed < GROUP_COOLDOWN_HOURS
    except:
        return False

def set_cooldown(grup_name):
    """Gruba mesaj gönderildi olarak işaretle"""
    from datetime import datetime
    cooldowns = load_cooldowns()
    cooldowns[grup_name.lower()] = datetime.now().isoformat()
    save_cooldowns(cooldowns)

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
    # Genel ticaret (Dijital Odaklı)
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "alim satim", "e-ticaret satış", "dijital satış",
    "referans reklam", "epin satış", "program satış",
    "yazılım ticaret", "dijital lisans", "reklam pazar",
    "reklam referans", "dijital pazar", "sosyal medya bayilik",
    # AI ve yazılım
    "yapay zeka", "chatgpt türkçe", "ai araçları", "ai tools",
    "adobe lisans", "canva pro", "premium hesap",
    "lisans satış", "yazılım indirim",
    # Kupon ve indirim
    "trendyol indirim", "trendyol kupon", "yemek kuponu",
    "indirim kodu", "promosyon kodu", "kampanya kodu",
    # Freelance ve dijital
    "dijital pazarlama", "sosyal medya yönetimi",
    "instagram takipçi", "youtube abone", "tiktok takipçi",
    # Oyun hesapları
    "pubg hesap", "brawl stars hesap", "valorant hesap",
    "oyun hesap satış", "game account",
    # Genel satış
    "pazar yeri"
]

async def auto_scrape_groups(client, client_name, joined_usernames=None):
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
    if joined_usernames:
        existing_groups.update(joined_usernames)
    blacklist = get_list(BLACKLIST_FILE)
    blacklist_lower = set(b.lower() for b in blacklist)
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
                username_attr = getattr(chat, 'username', None)
                if not is_group or not username_attr:
                    if isinstance(chat, Channel) and getattr(chat, 'broadcast', False) and username_attr:
                        username = username_attr.lower()
                        if username not in blacklist_lower:
                            save_to_list(username_attr, BLACKLIST_FILE)
                            blacklist_lower.add(username)
                            keyword_blacklisted += 1
                    continue
                    
                username = chat.username.lower()
                if username in existing_groups or username in blacklist_lower:
                    continue
                    
                member_count = getattr(chat, 'participants_count', None)
                title = (chat.title or "").lower()
                
                # === FİLTRE 1: Üye sayısı (500'den az = zaman kaybı) ===
                if member_count is not None and member_count < 100:
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
                
                # === FİLTRE 2.5: İstek/Onay kontrolü (Direkt katılım olmalı) ===
                if getattr(chat, 'join_request', False):
                    if username not in blacklist_lower:
                        save_to_list(chat.username, BLACKLIST_FILE)
                        blacklist_lower.add(username)
                        keyword_blacklisted += 1
                        print(f"  🚫 @{chat.username} → İstek/onay gerekiyor, kara liste")
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
                try:
                    with open("scraped_groups.txt", 'a', encoding='utf-8') as f:
                        f.write(chat.username + '\n')
                except:
                    pass

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
            print(f"⏳ [{client_name}] Auto-Scraper: Flood beklenecek ({e.seconds}s)...")
            await asyncio.sleep(e.seconds)
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
            
        if not fields:
            return
            
        mask_str = "&".join(mask_parts)
        url = f"{BASE_URL}/reklam/state?{mask_str}&key={API_KEY}"
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
    
    # Get currently joined group usernames to avoid finding them
    joined_usernames = set()
    print("🔄 Mevcut gruplarınız taranıyor (tekrar keşfetmemek için)...")
    try:
        async for dialog in first_client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                username = getattr(dialog.entity, 'username', None)
                if username:
                    joined_usernames.add(username.lower())
        print(f"✅ {len(joined_usernames)} adet mevcut grup tespit edildi. Bunlar aramada es geçilecek.")
    except Exception as e:
        print(f"⚠️ Mevcut gruplar alınırken hata: {e}")

    scrape_count = await auto_scrape_groups(first_client, first_name, joined_usernames)
    if scrape_count > 0:
        print(f"🎉 Auto-Scraper toplamda {scrape_count} yeni grup ekledi. Liste güncellendi!")

    async def run_worker(client, client_name, joined_dialogs):
        protected_groups = get_all_protected_groups()
        
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

                        # ⚡ WHITELIST MODU: Onaylı listede olmayan her grup = çık + kara liste
                        if not is_protected:
                            g_name = username_lower or dialog_id_str
                            print(f"[{client_name}] 🚫 @{g_name} → Onaylı listede yok! Kara listeye alınıp çıkılıyor...")
                            new_blacklisted_groups.append(g_name)
                            try:
                                await client(LeaveChannelRequest(dialog.entity))
                            except Exception as le:
                                print(f"[{client_name}] ⚠️ @{g_name} gruptan çıkılırken hata: {le}")
                            continue


                        # Filtreler (Korumalı gruplara uygulanmaz)
                        should_leave = False
                        leave_reason = ""
                        if not is_protected:
                            # FILTRE 1: Min 100 üye
                            if member_count is not None and member_count < 100:
                                should_leave = True
                                leave_reason = f"üye sayısı yetersiz ({member_count} < 100)"
                            elif member_count is None and not (hasattr(dialog.entity, 'username') and dialog.entity.username):
                                should_leave = True
                                leave_reason = "üye sayısı bilinmiyor ve username yok"
                            # FILTRE 2: Aktivite kontrolü — 10 farklı kişi yazmış mı?
                            if not should_leave:
                                g_key = username_lower or dialog_id_str
                                if g_key not in verified_groups:
                                    print(f"[{client_name}] 🔍 @{g_key} aktivite kontrolü yapılıyor...")
                                    is_active = await check_group_activity(dialog.entity, g_key)
                                    if is_active:
                                        verified_groups[g_key] = now.timestamp()
                                    else:
                                        should_leave = True
                                        leave_reason = f"inaktif grup (<{MIN_UNIQUE_SENDERS} farklı kişi yazmış)"
                                # else: zaten doğrulanmış, geç
                        
                        if should_leave:
                            g_name = dialog.entity.username or dialog_id_str
                            print(f"[{client_name}] 📉 @{g_name} -> {leave_reason}. Gruptan çıkılıyor...")
                            new_blacklisted_groups.append(g_name)
                            try:
                                await client(LeaveChannelRequest(dialog.entity))
                            except Exception as le:
                                print(f"[{client_name}] ⚠️ @{g_name} gruptan çıkılırken hata: {le}")
                            continue

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
                print(f"🚨 Worker {client_name} önbellek aşamasında Flood yedi! {e.seconds} saniye bekleniyor...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"⚠️ Worker {client_name} önbellek hatası: {e}")

        # ═══════════════════════════════════════════════════
        # BLAST MODE: Tüm gruplara aynı anda mesaj at
        # ═══════════════════════════════════════════════════
        while True:
            # Dinamik olarak korumalı listeyi güncelle
            protected_groups = get_all_protected_groups()
            
            # Her blast döngüsü başında diyalogları güncelle
            await cache_dialogs()
            
            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            
            # Hedef gruplar: Korumalı / Onaylı grupların hepsi
            hedef_set = protected_groups.copy()
            print(f"[{client_name}] 📌 Onaylı Hedef: {len(hedef_set)} grup")
            
            # Önbellekte olan + kara listede olmayan hedef gruplar
            blast_targets = []
            debug_blacklisted = 0
            debug_not_cached = 0
            small_groups_skipped = 0
            for username_lower in hedef_set:
                if username_lower in blacklist_lower:
                    debug_blacklisted += 1
                    continue
                if username_lower in joined_dialogs:
                    entity = joined_dialogs[username_lower]
                    if getattr(entity, 'broadcast', False):
                        continue
                    # Üye sayısı kontrolü: çok küçük grupları blast listesinden çıkar
                    member_count = getattr(entity, 'participants_count', None)
                    is_in_protected = username_lower in protected_groups
                    if not is_in_protected and member_count is not None and member_count < 100:
                        small_groups_skipped += 1
                        async with state_lock:
                            save_to_list(username_lower, BLACKLIST_FILE)
                        print(f"[{client_name}] 📉 @{username_lower} → {member_count} üye (<500), kara listeye eklendi.")
                        try:
                            await client(LeaveChannelRequest(entity))
                        except:
                            pass
                        continue
                    blast_targets.append(username_lower)
                else:
                    debug_not_cached += 1

            
            print(f"[{client_name}] 📊 Hedef: {len(hedef_set)} | Gönderilecek: {len(blast_targets)} | Kara liste: {debug_blacklisted} | Küçük grup çıkar: {small_groups_skipped} | Üye değil: {debug_not_cached}")
            
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
                
                # Sadece tek mesaj şablonu kullan (rotasyonu devre dışı bırak)
                is_keyvadi = "2" in client_name
                fallback = "message_2.txt" if is_keyvadi else "message.txt"
                available_files = [fallback] if os.path.exists(fallback) else []
                
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
                            
                            if failures[g_key] >= 5:
                                print(f"[{client_name}] ❌ @{grup_name} -> 5 kez üst üste hata alındı! Kara listeye ekleniyor...")
                                save_to_list(grup_name, BLACKLIST_FILE)
                                entity = joined_dialogs.get(g_key)
                                if entity:
                                    try:
                                        await client(LeaveChannelRequest(entity))
                                        print(f"[{client_name}] 🚪 @{grup_name} grubundan çıkıldı.")
                                    except Exception as le:
                                        print(f"[{client_name}] ⚠️ @{grup_name} grubundan çıkılırken hata: {le}")
                            elif failures[g_key] >= 3:
                                print(f"[{client_name}] ⚠️ @{grup_name} -> {failures[g_key]} kez üst üste hata alındı.")
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
                    
                    if is_on_cooldown(grup_name):
                        print(f"[{client_name}] ⏳ @{grup_name} cooldown süresinde, atlanıyor...")
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
                        
                        # Görsel/Banner gönderimi (Görseller kapatıldı)
                        banner_file = "keyvadi_banner.png" if is_keyvadi else "froxy_banner.png"
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
                        set_cooldown(grup_name)

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
                                set_cooldown(grup_name)

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
                        print(f"[{client_name}] ❌ @{grup_name} → Banlandık! Kara listeye ekleniyor...")
                        fail_count += 1
                        async with state_lock:
                            save_to_list(grup_name, BLACKLIST_FILE)
                        try:
                            if entity:
                                await client(LeaveChannelRequest(entity))
                                print(f"[{client_name}] 🚪 @{grup_name} grubundan çıkıldı.")
                        except Exception as le:
                            print(f"[{client_name}] ⚠️ @{grup_name} grubundan çıkılırken hata: {le}")
                    except ChatWriteForbiddenError:
                        print(f"[{client_name}] 🔒 @{grup_name} → Yazma izni yok! Kara listeye ekleniyor...")
                        fail_count += 1
                        async with state_lock:
                            save_to_list(grup_name, BLACKLIST_FILE)
                        try:
                            if entity:
                                await client(LeaveChannelRequest(entity))
                                print(f"[{client_name}] 🚪 @{grup_name} grubundan çıkıldı.")
                        except Exception as le:
                            print(f"[{client_name}] ⚠️ @{grup_name} grubundan çıkılırken hata: {le}")
                    except SlowModeWaitError as sme:
                        wait_sec = getattr(sme, 'seconds', 0) or 0
                        print(f"[{client_name}] 🐌 @{grup_name} → SlowMode ({wait_sec}sn bekleme), hata sayacı artıyor...")
                        fail_count += 1
                        await record_failure(grup_name)  # 5 kez slow mode → kara liste
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
            not_joined = []
            for g in hedef_set:
                g_lower = g.lower()
                if g_lower not in joined_dialogs and g_lower not in blacklist_lower:
                    not_joined.append(g)
            
            if not_joined:
                join_count = 0
                print(f"\n[{client_name}] 🔍 {len(not_joined)} gruba henüz üye değiliz. Katılma başlıyor...")
                for hedef_grup in not_joined:
                    if join_count >= 5:
                        print(f"[{client_name}] 🔒 Bu turda 5 gruba katılındı (limit), durduruluyor.")
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
                            is_protected = hedef_grup.lower() in protected_groups
                            
                            # Korumalı değilse ve üye sayısı 500'den azsa çık ve kara listeye al
                            if not is_protected and member_count is not None and member_count < 100:
                                print(f"[{client_name}] 📉 @{hedef_grup} -> Üye sayısı yetersiz ({member_count} < 100). Gruptan çıkılıyor ve kara listeye ekleniyor...")
                                async with state_lock:
                                    save_to_list(hedef_grup, BLACKLIST_FILE)
                                try:
                                    await client(LeaveChannelRequest(entity))
                                except Exception as le:
                                    print(f"[{client_name}] ⚠️ @{hedef_grup} gruptan çıkılırken hata: {le}")
                            else:
                                joined_dialogs[hedef_grup.lower()] = entity
                                join_count += 1
                            # Katılım isteği onaylandıysa/katılım sağlandıysa pending'den çıkar
                            if hedef_grup.lower() in pending_invites:
                                pending_invites.remove(hedef_grup.lower())
                            await asyncio.sleep(random.randint(30, 90))
                            
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
            
            # Sabit 30 dakika bekleme süresi
            grup_sayisi = len(blast_targets) if blast_targets else 0
            bekleme = 1800
            print(f"\n[{client_name}] ⏳ {grup_sayisi} gruba blast atıldı → Sonraki blast 30 dakika sonra")
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
        print("📥 Otomatik keşfedilen gruplar buluttan indirildi (onaylı listeye eklenmedi).")

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
            
            # Günlük periyodik tarama
            print("🔄 [Scraper Task] 24 saat doldu, günlük tarama başlıyor...")
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

    # Workers ve arka plan görevlerini başlat
    tasks = []
    for client, name, j_dialogs in active_clients:
        register_admin_handler(client, name, j_dialogs)
        tasks.append(run_worker(client, name, j_dialogs))
    
    # Scraper ve Firestore sync'i arka planda çalıştır
    first_client, first_name, _ = active_clients[0]
    tasks.append(periodic_scraper(first_client, first_name))
    tasks.append(periodic_firestore_sync())
    
    # Tüm görevleri eşzamanlı olarak çalıştır
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
