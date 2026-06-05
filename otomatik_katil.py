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
    # Önbellekten bulunan satış grupları (üye sayısına göre sıralı)
    "dakikadoksan", "bayanaktuel", "mesutkupon",
    "sahibindenarabalar", "sicakfirsatveindirimler", "ikincieltr", "BuyukFirsat",
    "sicakfirsatlar", "aracalimsatim1", "indirimfirsatburada",
    "ticaretref", "TekstilPlatformu", "firsatspt",
    "ticaretmerkezi", "uzaktan_freelancee", "eticaretlab",
    "sultanbeyliikinciel0", "Gurcistanticaret", "freelancertoplulugu",
    "ticaretvarburada", "banggoodturkey", "neastronhesap",
    "smmpanelgrup", "izmirpazar", "hesapalimsatim12", "oemalsat", "pubgsatis",
    "Turkiye_telefon_pazari", "kuponsatislari0",
    "AyakkabiSanati", "Turkiyepazar", "reklama_bardankol",
    "toptankozmetik47", "BrawlStarsHesap1", "kuponceksatisi",
    "kendireklaminiyap", "dijitalpazarlamatr", "elektroniksigaradunyasi",
    "hesapsatistrsohbet", "smmpanelkur", "reklamvereferanssss",
    "ttingalimsatim", "trendyolsatkazan", "ucbosspubgHESAP", "reklamyap",
    "HESAPACCOUNT1", "ReklamYaptr", "hesapsatistr", "N_A_F_A_Smm",
    "kuponkodalsat", "svp_referans", "smsngsatis", "pazaryerialsat",
    "ticaretmeydani", "smmpanelturkiye", "freelancerturkiye",
    "trendyolsatici", "lisanspazari", "KorgPa2xPa800",
    "sharkvapetr", "ikincielkralligi",
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

# --- Auto-DM: Yanıt veren kullanıcıları takip et ---
replied_users = set()

# --- Auto-Scrape: Anahtar kelimeler ---
SCRAPE_KEYWORDS = [
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "ikinci el", "2.el satış", "alim satim",
    "e-ticaret satış", "trendyol satıcı", "freelance iş",
    "referans reklam", "satılık ilan", "epin satış",
]

async def auto_scrape_groups(client, client_name):
    """Telegram global aramasıyla yeni, aktif ve Türkçe satış grupları keşfeder."""
    print(f"\n🔍 [{client_name}] Akıllı Grup Keşfi (Auto-Scraper) başlıyor...")
    
    existing_groups = set(g.lower() for g in gruplar)
    blacklist = get_list(BLACKLIST_FILE)
    blacklist_lower = set(b.lower() for b in blacklist)
    new_found = 0
    
    keyword = random.choice(SCRAPE_KEYWORDS)
    print(f"🔎 [{client_name}] Aranan anahtar kelime: '{keyword}'")
    
    # Türkçe satış grubu olup olmadığını kontrol etmek için kelimeler
    sales_keywords = [
        "satış", "satis", "ticaret", "ilan", "reklam", "kupon", "indirim",
        "shopier", "hesap", "alım", "satım", "alim", "satim", "smm", "kod",
        "ucuz", "ref", "pazar", "ikinci el", "brawl", "pubg", "takipçi"
    ]
    
    try:
        from telethon.tl.types import Channel, Chat
        result = await client(SearchRequest(q=keyword, limit=50))
        
        for chat in result.chats:
            # 1. Yayın kanalı olmamalı (broadcast=True elenir), megagrup veya chat olmalı
            is_group = False
            if isinstance(chat, Channel):
                if not getattr(chat, 'broadcast', False):
                    is_group = True
            elif isinstance(chat, Chat):
                is_group = True
                
            if not is_group or not chat.username:
                # Yayın kanalıysa ve kullanıcı adı varsa kara listeye ekleyelim
                if isinstance(chat, Channel) and getattr(chat, 'broadcast', False) and chat.username:
                    username = chat.username.lower()
                    if username not in blacklist_lower:
                        save_to_list(chat.username, BLACKLIST_FILE)
                        blacklist_lower.add(username)
                        print(f"🚫 [Scraper] @{chat.username} -> Yayın kanalı olduğu için kara listeye alındı.")
                continue
                
            username = chat.username.lower()
            if username in existing_groups or username in blacklist_lower:
                continue
                
            # 2. Üye sayısı kontrolü (En az 50 üye olmalı)
            member_count = getattr(chat, 'participants_count', None)
            if member_count is not None and member_count < 50:
                if username not in blacklist_lower:
                    save_to_list(chat.username, BLACKLIST_FILE)
                    blacklist_lower.add(username)
                    print(f"🚫 [Scraper] @{chat.username} -> Üye sayısı az ({member_count}), kara listeye alındı.")
                continue
                
            # 3. Dil ve İçerik Kontrolü: Başlıkta satış kelimeleri veya Türkçe karakter geçmeli
            title = (chat.title or "").lower()
            has_sales_word = any(w in title for w in sales_keywords)
            has_tr_chars = bool(re.search(r"[ıışşğğççööüüıİİŞŞĞĞÇÇÖÖÜÜ]", title))
            
            if not (has_sales_word or has_tr_chars):
                if username not in blacklist_lower:
                    save_to_list(chat.username, BLACKLIST_FILE)
                    blacklist_lower.add(username)
                    print(f"🚫 [Scraper] @{chat.username} -> İçerik/Dil uyumsuz, kara listeye alındı.")
                continue
                
            # auto_groups.txt'ye kaydet
            with open(AUTO_GROUPS_FILE, 'a', encoding='utf-8') as f:
                f.write(chat.username + '\n')
            existing_groups.add(username)
            gruplar.append(chat.username)
            new_found += 1
            print(f"🆕 [{client_name}] Akıllı Scraper Yeni Grup Keşfetti: @{chat.username} (Üye: {member_count or 'Bilinmiyor'})")
            
        if new_found > 0:
            update_stats(discovered=new_found)
            print(f"✅ [{client_name}] Auto-Scraper: {new_found} yeni grup keşfedildi!")
        else:
            print(f"ℹ️ [{client_name}] Auto-Scraper: '{keyword}' için uygun yeni grup bulunamadı.")
            
    except FloodWaitError as e:
        print(f"⏳ [{client_name}] Auto-Scraper: Flood beklenecek ({e.seconds}s)...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"⚠️ [{client_name}] Auto-Scraper hatası: {type(e).__name__} - {e}")
        
    return new_found

DM_MESSAGE = (
    "Merhaba 👋\n\n"
    "Gruptaki mesajınıza istinaden yazıyorum.\n"
    "Sorularınız ve satın alım için ana botumuz olan "
    "@FroxyDestekBOT üzerinden iletişime geçebilirsiniz.\n\n"
    "İyi günler! 🙏"
)


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
            return progress, blacklist
    except Exception as e:
        print(f"⚠️ Firestore yükleme hatası: {e}")
    return "", ""

def fs_set_state(progress, blacklist):
    try:
        url = f"{BASE_URL}/reklam/state?key={API_KEY}"
        fields = {
            "progress_list": {"stringValue": progress},
            "blacklist_list": {"stringValue": blacklist}
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
        progress_content = ""
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                progress_content = f.read()
        
        blacklist_content = ""
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                blacklist_content = f.read()
                
        fs_set_state(progress_content, blacklist_content)
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
                active_clients.append((client1, "Hesap #1", {}))
                print("✅ 1. Hesap yetkilendirildi ve aktif edildi.")
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
                active_clients.append((client2, "Hesap #2", {}))
                print("✅ 2. Hesap yetkilendirildi.")
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
                active_clients.append((client1, "Yerel Hesap", {}))
                print("✅ Yerel hesap yetkilendirildi.")
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

    state_lock = asyncio.Lock()
    active_jobs = set()

    # --- AUTO-DM: KAPATILDI ---
    # Özel mesaj gönderme devre dışı
    print("ℹ️ Auto-DM kapalı.")

    # --- AUTO-SCRAPE: AKTİF ---
    first_client, first_name, _ = active_clients[0]
    scrape_count = await auto_scrape_groups(first_client, first_name)
    if scrape_count > 0:
        print(f"🎉 Auto-Scraper toplamda {scrape_count} yeni grup ekledi. Liste güncellendi!")

    async def run_worker(client, client_name, joined_dialogs):
        print(f"🚀 Worker {client_name} diyalogları önbelleğe alınıyor...")
        # Hedef grupları kara listeye ASLA atma
        protected_groups = set(g.lower() for g in gruplar)
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            new_blacklisted_groups = []
            all_groups_info = []
            
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    if hasattr(dialog.entity, 'username') and dialog.entity.username:
                        username_lower = dialog.entity.username.lower()
                        title = getattr(dialog.entity, 'title', '') or ''
                        member_count = getattr(dialog.entity, 'participants_count', None)
                        is_broadcast = getattr(dialog.entity, 'broadcast', False)
                        
                        # Hedef gruptaysa kara listeye yazmayacağız ama aktif değilse/boşsa yine de es geçeceğiz
                        is_protected = username_lower in protected_groups
                        
                        # 1. Üye sayısı kontrolü (boş grupları es geç)
                        if member_count is not None and member_count < 20:
                            if not is_protected:
                                new_blacklisted_groups.append(dialog.entity.username)
                            continue
                            
                        # 2. Aktiflik kontrolü ve Kendi Mesajlarımızla Dolan Grupların Temizlenmesi
                        days_inactive = 0
                        last_msg = dialog.message
                        
                        try:
                            # Son 3 mesajı alıp kontrol edelim
                            recent_messages = []
                            async for msg in client.iter_messages(dialog.entity, limit=3):
                                recent_messages.append(msg)
                            
                            # Eğer son 3 mesajın tamamı bizden ise (outgoing) grubu kalıcı olarak kara listeye alalım
                            if len(recent_messages) >= 3 and all(getattr(m, 'out', False) for m in recent_messages):
                                new_blacklisted_groups.append(dialog.entity.username)
                                print(f"🚫 [{client_name}] @{dialog.entity.username} -> Son 3 mesajın tamamı bizden, KARA LİSTEYE ALINDI!")
                                continue
                                
                            # Son mesaj bizim gönderdiğimizse geçmişe bakıp başkasının mesajını arayalım
                            if last_msg and getattr(last_msg, 'out', False):
                                found_other = False
                                async for msg in client.iter_messages(dialog.entity, limit=5):
                                    if not getattr(msg, 'out', False):
                                        last_msg = msg
                                        found_other = True
                                        break
                                if not found_other:
                                    last_msg = None
                        except Exception as history_err:
                            pass
                            
                        if last_msg and getattr(last_msg, 'date', None):
                            delta = now - last_msg.date
                            days_inactive = delta.days
                            if delta.days >= 7:
                                if not is_protected:
                                    new_blacklisted_groups.append(dialog.entity.username)
                                continue
                        else:
                            # Mesaj yoksa veya son 5 mesajın hepsi bizimse grubu inaktif sayıp es geç
                            continue
                                
                        joined_dialogs[username_lower] = dialog.entity
                        all_groups_info.append({
                            "username": dialog.entity.username,
                            "title": title,
                            "members": member_count,
                            "broadcast": is_broadcast,
                            "days_inactive": days_inactive
                        })
                        
            # Grup bilgilerini dosyaya kaydet
            groups_file = f"cached_groups_{client_name.replace(' ', '_').replace('#', '')}.json"
            try:
                with open(groups_file, 'w', encoding='utf-8') as f:
                    json.dump(all_groups_info, f, ensure_ascii=False, indent=2)
                print(f"[{client_name}] 📋 {len(all_groups_info)} grup bilgisi {groups_file} dosyasına kaydedildi.")
            except:
                pass
            
            if new_blacklisted_groups:
                print(f"[{client_name}] 💾 {len(new_blacklisted_groups)} inaktif/küçük grup kara listeye kaydediliyor...")
                async with state_lock:
                    with open(BLACKLIST_FILE, 'a', encoding='utf-8') as f:
                        for g in new_blacklisted_groups:
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
            
            print(f"[{client_name}] 📊 Hedef: {len(hedef_set)} | Önbellekte: {len(hedef_set)-debug_not_cached-debug_blacklisted} | Kara liste: {debug_blacklisted} | Üye değil: {debug_not_cached}")
            
            if not blast_targets:
                print(f"[{client_name}] ⚠️ Önbellekte mesaj atılacak grup yok. Yeni gruplara katılma aşamasına geçiliyor...")
            else:
                print(f"\n[{client_name}] 🚀 BLAST MODE: {len(blast_targets)} gruba aynı anda mesaj gönderiliyor!")
                
                # Mesajı oku
                msg_file = "message_2.txt" if "2" in client_name else "message.txt"
                try:
                    with open(msg_file, "r", encoding="utf-8") as fm:
                        base_msg = fm.read()
                except:
                    try:
                        with open("message.txt", "r", encoding="utf-8") as fm:
                            base_msg = fm.read()
                    except:
                        base_msg = "Merhaba! Detaylar için @FroxyDestekBOT"

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
                            
                            # 3 kez üst üste hata aldıysa kara listeye ekle
                            if failures[g_key] >= 3:
                                save_to_list(grup_name, BLACKLIST_FILE)
                                print(f"[{client_name}] 🚫 @{grup_name} -> 3 kez üst üste hata alındı, KARA LİSTEYE ALINDI!")
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
                    """Tek bir gruba mesaj gönder"""
                    nonlocal sent_count, fail_count
                    entity = joined_dialogs.get(grup_name.lower())
                    if not entity:
                        return
                    try:
                        # Mesajı spintax ile çeşitle
                        msg = base_msg
                        if grup_name.lower() == "kuponceking":
                            msg = msg.replace("🤖 **Sipariş & Canlı Destek Botumuz:** @FroxyDestekBOT", "") \
                                     .replace("🤖 **Sipariş & Canlı Destek Botumuz:** @KeyVadiSatisBot", "") \
                                     .replace("bot", "sistem").replace("Bot", "Sistem") \
                                     .replace("🤖", "").strip() + "\n"
                        msg = parse_spintax(msg)
                        
                        await client.send_message(entity, msg)
                        sent_count += 1
                        print(f"[{client_name}] ✅ @{grup_name} -> Gönderildi! ({sent_count})")
                        update_stats(sent=1)
                        await reset_failure(grup_name)
                        async with state_lock:
                            save_to_list(grup_name, PROGRESS_FILE)
                    except FloodWaitError as e:
                        if e.seconds <= 30:
                            await asyncio.sleep(e.seconds)
                            try:
                                msg = parse_spintax(base_msg)
                                await client.send_message(entity, msg)
                                sent_count += 1
                                print(f"[{client_name}] ✅ @{grup_name} -> Gönderildi (flood sonrası)!")
                                update_stats(sent=1)
                                await reset_failure(grup_name)
                            except:
                                fail_count += 1
                                await record_failure(grup_name)
                        else:
                            print(f"[{client_name}] ⏳ @{grup_name} -> Flood {e.seconds}sn, atlanıyor...")
                            fail_count += 1
                    except UserBannedInChannelError:
                        print(f"[{client_name}] ❌ @{grup_name} -> Banlandık!")
                        fail_count += 1
                        await record_failure(grup_name)
                    except ChatWriteForbiddenError:
                        print(f"[{client_name}] 🔒 @{grup_name} -> Yazma izni yok")
                        fail_count += 1
                        await record_failure(grup_name)
                    except SlowModeWaitError:
                        print(f"[{client_name}] 🐌 @{grup_name} -> SlowMode, atlanıyor.")
                        fail_count += 1
                    except Exception as e:
                        err_type = type(e).__name__
                        print(f"[{client_name}] ⚠️ @{grup_name} -> {err_type} (atlanıyor)")
                        fail_count += 1
                        await record_failure(grup_name)

                # Gruplara sırayla ve aralarında 10-20 saniye rastgele bekleme koyarak gönder!
                import random
                print(f"\n[{client_name}] 📤 Sırayla gönderim başlıyor ({len(blast_targets)} grup)...")
                for i, g in enumerate(blast_targets, 1):
                    await blast_one(g)
                    if i < len(blast_targets):
                        delay = random.randint(10, 20)
                        print(f"[{client_name}] ⏳ Sonraki grup için {delay} saniye bekleniyor...")
                        await asyncio.sleep(delay)

                
                print(f"\n[{client_name}] 📊 BLAST SONUÇ: {sent_count} başarılı, {fail_count} başarısız / {len(blast_targets)} toplam")

            # ═══════════════════════════════════════════════════
            # YENİ GRUPLARA KATILMA AŞAMASI (blast sonrası)
            # ═══════════════════════════════════════════════════
            blacklist = get_list(BLACKLIST_FILE)
            blacklist_lower = set(b.lower() for b in blacklist)
            not_joined = [g for g in gruplar if g.lower() not in blacklist_lower and g.lower() not in joined_dialogs]
            
            if not_joined:
                join_count = 0
                print(f"\n[{client_name}] 🔍 {len(not_joined)} gruba henüz üye değiliz. Katılma başlıyor...")
                for hedef_grup in not_joined:
                    if join_count >= 15:
                        print(f"[{client_name}] 🔒 Bu turda 15 gruba katılındı, durduruluyor.")
                        break
                    try:
                        entity = await client.get_entity(hedef_grup)
                        await client(JoinChannelRequest(entity))
                        
                        member_count = getattr(entity, 'participants_count', None)
                        if member_count is not None and member_count < 20:
                            if hedef_grup.lower() not in protected_groups:
                                async with state_lock:
                                    save_to_list(hedef_grup, BLACKLIST_FILE)
                            print(f"[{client_name}] 📉 @{hedef_grup} -> Üye az ({member_count}), es geçildi.")
                            continue
                        
                        joined_dialogs[hedef_grup.lower()] = entity
                        join_count += 1
                        print(f"[{client_name}] ✅ Yeni gruba katıldı: @{hedef_grup} ({join_count}/5)")
                        await asyncio.sleep(random.randint(5, 15))
                        
                    except FloodWaitError as e:
                        if e.seconds <= 60:
                            await asyncio.sleep(e.seconds)
                        else:
                            print(f"[{client_name}] ⚠️ Join flood {e.seconds}sn, katılma durduruluyor.")
                            break
                    except (ChannelPrivateError,):
                        async with state_lock:
                            save_to_list(hedef_grup, BLACKLIST_FILE)
                    except Exception as e:
                        err_msg = str(e)
                        err_type = type(e).__name__
                        if 'InviteRequestSent' in err_type or 'invite' in err_msg.lower() or \
                           'no user has' in err_msg.lower() or isinstance(e, (UsernameNotOccupiedError, UsernameInvalidError, ValueError)):
                            async with state_lock:
                                save_to_list(hedef_grup, BLACKLIST_FILE)
                            print(f"[{client_name}] ❌ @{hedef_grup} -> {err_type}, kara liste.")
                        else:
                            print(f"[{client_name}] ⚠️ @{hedef_grup} -> {err_type}")

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
            
            # Dinamik bekleme: grup sayısına göre otomatik ayarla
            grup_sayisi = len(blast_targets) if blast_targets else 0
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
                uyku = min(60, kalan)
                await asyncio.sleep(uyku)
                kalan -= uyku

    while True:
        # Başlangıçta Firestore'dan verileri çek
        print("🔄 Firestore'dan güncel durum yükleniyor...")
        fs_prog, fs_black = fs_get_state()
        if fs_prog:
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                f.write(fs_prog)
            print("📥 İlerleme durumu buluttan indirildi.")
        if fs_black:
            local_black = get_list(BLACKLIST_FILE)
            remote_black = set(x.strip() for x in fs_black.splitlines() if x.strip())
            merged_black = local_black.union(remote_black)
            # Hedef grupları kara listeden ÇIKAR
            protected = set(g.lower() for g in gruplar)
            cleaned = set(g for g in merged_black if g.lower() not in protected)
            removed = len(merged_black) - len(cleaned)
            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned) + '\n')
            if removed > 0:
                print(f"📥 Kara liste birleştirildi. {removed} hedef grup kara listeden çıkarıldı!")
            else:
                print("📥 Kara liste buluttan indirildi ve birleştirildi.")

        active_jobs.clear()
        
        # Run workers concurrently
        tasks = []
        for client, name, j_dialogs in active_clients:
            tasks.append(run_worker(client, name, j_dialogs))
            
        await asyncio.gather(*tasks)

        # Tüm liste bittiğinde
        print(f"\n✅ Tüm liste bitti! 1 SAAT ARA VERİLİYOR...")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        # Firestore progress temizleme
        try:
            blacklist_content = ""
            if os.path.exists(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                    blacklist_content = f.read()
            fs_set_state("", blacklist_content)
        except Exception as e:
            pass
        
        # Yeni döngü öncesi otomatik grup keşfi - AKTİF
        print(f"\n🔍 Yeni döngü için Auto-Scraper çalıştırılıyor...")
        await auto_scrape_groups(first_client, first_name)
        
        await asyncio.sleep(3600) # 1 saat bekle ve baştan başla
    
    # Clean up (unreachable but formal)
    for client, name, _ in active_clients:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
