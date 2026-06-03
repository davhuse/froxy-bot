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
    "Nightsatis", "eticaretlab", "ticaretmerkezi", "bedavainternetssohbet", "ticaretmeydani", 
    "DijitalPazarTR", "YazilimLisans", "PremiumHesapSatiss", "EticaretTR", "WebmasterTR", 
    "SMMBayiTR", "eticaret_tedarikcileri", "FreelancerTurkiye", "AITurkiye", "YazilimciGelistirme", 
    "HesapSatisTR", "EpisSatis", "OyunHesapTR", "DijitalMarketim", "UcuzaLisans", 
    "PazaryeriSaticilari", "AmazonSellersTR", "WebmasterSatis", "SEO_Turkiye", "SosyalMedyaTicaret", 
    "BotSatisTR", "AdsenseSatis", "DomainPazari", "YazilimDestek", "TeknolojiSohbet", 
    "FreelanceIsIlani", "CoderTurkiye", "PythonTurkiye", "JavaScript_TR", "CyberSecurity_TR", 
    "KriptoTicaret", "StartupTR", "KuponPaylasim", "TurkiyeReklamGrubu", "WebmasterYardimlasma", 
    "SMMPanelTurkiye", "HesapSatisPazari", "LisansPazari", "Oyun_Hesap_Alim_Satim", "PremiumHesaplar_TR", 
    "Canva_Pro_Yardimlasma", "Adobe_Creative_Cloud_TR", "Windows_Office_Key_Satis", "Yazilimci_Is_Ilanlari", "Freelance_Turkiye_Grup", 
    "E_Ticaret_Satis_Taktikleri", "Amazon_FBA_Turkiye", "Trendyol_Saticilari_Grubu", "Hepsiburada_Saticilari", "Shopify_Turkiye_Yardim", 
    "Kripto_Para_Sohbet_TR", "Airdrop_Firsatlari_TR", "Borsa_Istanbul_Sohbet", "Teknoloji_Dunyasi_Haber", "Yazilim_Kulu_Yardim", 
    "Python_Turkiye_Gelistirici", "Java_Turkiye_Toplulugu", "PHP_Laravel_TR", "Oyun_Haber_Sohbet", "Netflix_Disney_Premium", 
    "Spotify_Premium_Hizmet", "YouTube_Premium_TR", "TikTok_Etkilesim_Grubu", "satilikilanlar", "ShopifyUzmani", 
    "Gurcistanticaret", "ticaretvarburada", "eticaretyardimlasmaa", "ilan_ver", "is_ilanlari_grubu", 
    "FreelanceWorkTR", "kuponindirimsatis", "kuponsatisgrup", "kuponhesapsatis", "kuponsat", 
    "KuponindirimPazari", "kuponceking", "kuponkodalsat", "kupongrupta", "kuponceksatis", 
    "yazilimci_grubu", "phpturkiye", "seoyedek", "smmbayim", "eticaretplatformu", 
    "freelanceyazilim", "oyunalisveris", "dijitalpazar", "kriptosohbet", "borsasohbet", 
    "freelancertr", "teknolojihaber", "ucuzlisanslar", "premiumhesaplar", "smmhizmetleri", 
    "tasarimciyardim", "yazilimciyardim", "amazonfbatr", "trendyolsaticilar", "hepsiburadasaticilar", 
    "spotifygenel", "youtubepremiumtr", "netflixpremiumtr", "oyunhesaplarisatis", "KuponSatis", 
    "SosyalMedyaPazari", "AdsenseTurkiye", "FreelancerYazilimci", "TeknolojiSohbetleri", "WebTasarimDestek", 
    "SMMHizmeti", "KriptoSohbetTR", "EpinDestek", "OyunAlSat", "TrendyolDestekSohbet", 
    "AmazonSellersTRGroup", "ShopifyDestek", "BorsaYardim", "CoderDestekTR", "EpinPazari", 
    "HesapSatisGenel", "LisansBayi", "SosyalMedyaTicaretGrubu", "EpinAlSat", "SMMPanelTurk", 
    "AdsenseDestekTR", "FreelanceIsIlanlariTR", "KriptoKazan", "AmazonFBAyardim", "TrendyolPazaryeri", 
    "WebmasterDestekTR", "PythonSohbet", "JavaYardimlasma", "OyunPazariTR", "SteamOyunTR", 
    "PremiumUyelikTR", "CanvaTasarimYardim", "AdobeTRYardim", "WindowsOfficeKey", "YazilimIsFirsatlari", 
    "ShopifyGirisim", "BorsaKriptoHaber", "GrafikTasarimDestek", "YazilimciSohbetleri", "EpinBayilik", 
    "ZulaPazariTR", "WolfteamSatisTR", "SpotifyDavet", "EpinKoduSatis", "WebTasarimYardim", 
    "SMMPanelSatisGrubu", "AdsenseAlSat", "KriptoSohbetGrubu", "PremiumSatisTR", "AmazonSellersYardim", 
    "ShopifyDestekTR", "YazilimIlanTR", "EpinSatisPazari", "HesapAlimSatimTR", "turkiyepazar", 
    "turkcesmm", "sosyalmedyapazaritr", "dijitalpazaryeritr", "satisgrubu", "webmasteryardimlasmatr", 
    "reklamgrubutr", "satiskanali", "dijitalurunsatis", "hesap_satis_tr", "epin_pazari", 
    "lisans_alim_satim", "freelance_is_ilanlari_tr", "yazilimci_is_ilanlari_tr", "amazon_satis_ortakligi", "trendyol_saticilari_tr", 
    "hepsiburada_satis_toplulugu", "kriptosatistr", "borsa_sohbet_tr", "teknolojialimsatim", "donanimsatistr", 
    "smmbayilertr", "smmhizmetleripazari", "freelancework_tr", "designer_is_ilanlari", "coder_is_ilanlari", 
    "pythontr_satis", "javascripttr_satis", "siberguvenliktr_satis", "oyun_hesap_satis_pazari", "premium_satis_pazari", 
    "spotify_premium_tr", "youtube_premium_satis", "tiktok_hesap_satis", "satilik_domainler", "adsense_alim_satim", 
    "eticaret_tedarik", "freelance_destek_tr", "ticaretmeydanitr", "kupon_satis_tr", "AmazonTrGenelSohbet", 
    "HESAPACCOUNT1", "KriptoSozlukTVPiyasaMuhabbeti", "N_A_F_A_Smm", "Panel_Member_Premium_Ban_buy", "Prof_Amazon8", 
    "ReklamYaptr", "Turkiye_telefon_pazari", "XushnudMFYreklama", "YouTuBeAboneKazan", "YuceKuponSatis", 
    "amazon_fbauz1", "amazonfbasellers", "borsao", "buy_Panel_Premium_Members_Adder", "dijitalpazarlamatr", 
    "erdil_satis", "freelancertoplulugu", "icon_webmasters_cpa", "indirimkodusatis", "izmirpazar", 
    "kendireklaminiyap", "kripto1", "kriptoe", "kuponceksatisi", "kuponl", 
    "kuponsatislari0", "mesutkupon", "neastronhesap", "pazaryerialsat", "referansreklam1", 
    "reklama_bardankol", "reklamvereferanssss", "reklamyap", "satisrefim", "smmpanelkur", 
    "smsngsatis", "sosyalmedyaalimsatimticaret", "testnet_aidrop_on_satis_kripto", "ticaretguvenilir", "ticaretsaha", 
    "trendyol8", "trendyolsatkazan", "ucbosspubgHESAP", "uye_ekleme_satis", "uzaktan_freelancee", 
    "webmasterdestek", "webmasterscafe", "yazilimci_hanim", "yazilimcigencler", "yazilimciiiadam", 
    "yazilimcilarburada", "yukseklisansdoktora", "turkiyesatispazari", "dijitalpazarkey", "reklampazaritr", 
    "hesaplisansmarket", "uygunlisanssatis", "satis_ilanlari_tr", "freelance_dijital", "premium_market_tr", 
    "kupon_pazari", "telegram_reklam_tr", "dijital_tedarikci", "dijitalalisveris", "turkiyereklamsohbet", 
    "smm_bayi_ticaret", "r10_com", "r10_forum", "yazilimci_sohbeti", "freelance_ilanlari", 
    "freelancer_tr", "hesap_alsat", "eticaret_sohbet", "smm_panel_rehberi", "smm_bayileri", 
    "epin_alsat_tr", "kupon_yardimlasmasi", "tasarimcilar_kulubu", "coder_turkiye_sohbet"
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
    "yazılım", "hesap satış", "kripto", "smm panel",
    "freelance", "e-ticaret", "sosyal medya", "bot",
    "reklam", "dijital pazarlama", "epin", "oyun hesap",
    "spotify", "netflix", "vpn", "hosting"
]

async def auto_scrape_groups(client, client_name):
    """Telegram global aramasıyla yeni gruplar keşfeder ve auto_groups.txt'ye kaydeder."""
    print(f"\n🔍 [{client_name}] Otomatik Grup Keşfi (Auto-Scraper) başlıyor...")
    
    existing_groups = set(g.lower() for g in gruplar)
    blacklist = get_list(BLACKLIST_FILE)
    new_found = 0
    
    keyword = random.choice(SCRAPE_KEYWORDS)
    print(f"🔎 [{client_name}] Aranan anahtar kelime: '{keyword}'")
    
    try:
        from telethon.tl.types import Channel
        result = await client(SearchRequest(q=keyword, limit=50))
        
        for chat in result.chats:
            if isinstance(chat, Channel) and chat.username:
                username = chat.username.lower()
                if username not in existing_groups and username not in blacklist:
                    # auto_groups.txt'ye kaydet
                    with open(AUTO_GROUPS_FILE, 'a', encoding='utf-8') as f:
                        f.write(chat.username + '\n')
                    existing_groups.add(username)
                    gruplar.append(chat.username)
                    new_found += 1
                    print(f"🆕 [{client_name}] Yeni grup keşfedildi: @{chat.username}")
        
        if new_found > 0:
            update_stats(discovered=new_found)
            print(f"✅ [{client_name}] Auto-Scraper: {new_found} yeni grup keşfedildi ve listeye eklendi!")
        else:
            print(f"ℹ️ [{client_name}] Auto-Scraper: '{keyword}' için yeni grup bulunamadı.")
            
    except FloodWaitError as e:
        print(f"⏳ [{client_name}] Auto-Scraper: Flood bekleniyor ({e.seconds}s)...")
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
                print("✅ 1. Hesap yetkilendirildi.")
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

    # --- AUTO-DM: Mesajlarımıza yanıt veren kullanıcılara otomatik DM ---
    for client, client_name, _ in active_clients:
        my_id = (await client.get_me()).id
        
        @client.on(events.NewMessage(func=lambda e: e.is_reply and e.is_group))
        async def auto_dm_handler(event, _client=client, _name=client_name, _my_id=my_id):
            try:
                replied_msg = await event.get_reply_message()
                if replied_msg and replied_msg.sender_id == _my_id:
                    sender_id = event.sender_id
                    if sender_id in replied_users or sender_id == _my_id:
                        return
                    
                    replied_users.add(sender_id)
                    try:
                        await _client.send_message(sender_id, DM_MESSAGE)
                        print(f"📩 [{_name}] Auto-DM: Kullanıcı {sender_id} mesajımıza yanıt verdi. DM gönderildi!")
                        update_stats(sent=0)  # Sadece log amaçlı
                    except Exception as dm_err:
                        print(f"⚠️ [{_name}] Auto-DM: DM gönderilemedi ({sender_id}): {type(dm_err).__name__}")
            except Exception as e:
                pass  # Sessiz hata - event loop'u bozmamalı
        
        print(f"🎯 [{client_name}] Auto-DM dinleyicisi aktifleştirildi.")

    # --- AUTO-SCRAPE: İlk çalıştırmada grup keşfi yap ---
    first_client, first_name, _ = active_clients[0]
    scrape_count = await auto_scrape_groups(first_client, first_name)
    if scrape_count > 0:
        print(f"🎉 Auto-Scraper toplamda {scrape_count} yeni grup ekledi. Liste güncellendi!")

    async def run_worker(client, client_name, joined_dialogs):
        print(f"🚀 Worker {client_name} diyalogları önbelleğe alınıyor...")
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            new_blacklisted_groups = []
            
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    if hasattr(dialog.entity, 'username') and dialog.entity.username:
                        username_lower = dialog.entity.username.lower()
                        
                        # 1. Üye sayısı kontrolü (Önceden üye olduklarımızı filtreler)
                        member_count = getattr(dialog.entity, 'participants_count', None)
                        if member_count is not None and member_count < 20:
                            print(f"[{client_name}] 📉 Önbellek: @{dialog.entity.username} üye sayısı çok az ({member_count}). Kara listeye alınıyor...")
                            new_blacklisted_groups.append(dialog.entity.username)
                            continue
                            
                        # 2. Aktiflik (Son mesaj tarihi) kontrolü (Örn: Son 3 gündür mesaj atılmamış ölü grupları eler)
                        if dialog.message and dialog.message.date:
                            delta = now - dialog.message.date
                            if delta.days >= 30:
                                print(f"[{client_name}] 💤 Önbellek: @{dialog.entity.username} son mesaj {delta.days} gün önce atılmış (Çok İnaktif). Kara listeye alınıyor...")
                                new_blacklisted_groups.append(dialog.entity.username)
                                continue
                                
                        joined_dialogs[username_lower] = dialog.entity
                        
            if new_blacklisted_groups:
                print(f"[{client_name}] 💾 {len(new_blacklisted_groups)} inaktif/küçük grup toplu olarak kara listeye kaydediliyor...")
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

        join_count = 0
        while True:
            hedef_grup = None
            
            async with state_lock:
                kullanilacak_gruplar = []
                blacklist = get_list(BLACKLIST_FILE)
                for g in gruplar:
                    if g not in blacklist:
                        kullanilacak_gruplar.append(g)
                update_stats(active=len(kullanilacak_gruplar), blacklisted=len(blacklist))
                        
                if not kullanilacak_gruplar:
                    print(f"⚠️ Worker {client_name}: Atılacak aktif grup kalmadı!")
                    break
                    
                done_groups = get_list(PROGRESS_FILE)
                
                # Check if all groups are done
                if done_groups and len(done_groups) >= len(kullanilacak_gruplar):
                    break
                    
                # Find the first available group not done and not actively processed
                for g in kullanilacak_gruplar:
                    if g not in done_groups and g not in active_jobs:
                        hedef_grup = g
                        active_jobs.add(g)
                        break
            
            if not hedef_grup:
                # No groups available right now (others might be processed), sleep a bit
                await asyncio.sleep(5)
                # Check if we should exit because all are done
                async with state_lock:
                    done_groups = get_list(PROGRESS_FILE)
                    if done_groups and len(done_groups) >= len(kullanilacak_gruplar):
                        break
                continue
                
            try:
                print(f"\n[{client_name}] 🔍 @{hedef_grup} denetleniyor...")
                grup_lower = hedef_grup.lower()
                entity = None
                
                # ═══════════════════════════════════════════
                # ADIM 1: Entity'yi bul (Önbellek veya Join)
                # ═══════════════════════════════════════════
                if grup_lower in joined_dialogs:
                    entity = joined_dialogs[grup_lower]
                    print(f"[{client_name}] ✅ Zaten gruptayız (Önbellekten): @{hedef_grup}")
                    
                    # Önbellekteki üye sayısı kontrolü (< 20 = değersiz grup)
                    member_count = getattr(entity, 'participants_count', None)
                    if member_count is not None and member_count < 20:
                        print(f"[{client_name}] 📉 @{hedef_grup} -> Üye sayısı çok az ({member_count} < 20). Kara listeye alınıyor...")
                        async with state_lock:
                            save_to_list(hedef_grup, BLACKLIST_FILE)
                        entity = None
                else:
                    # Join limiti: 3 gruba katıldıktan sonra 10dk bekle, sayacı sıfırla
                    if join_count >= 3:
                        cooldown = random.randint(300, 600)  # 5-10 dk
                        print(f"[{client_name}] 🔒 3 gruba katılındı. Güvenlik için {cooldown // 60}dk bekleniyor ve sayaç sıfırlanıyor...")
                        await asyncio.sleep(cooldown)
                        join_count = 0
                    
                    # Gruba katıl
                    try:
                        from telethon.tl.functions.channels import GetFullChannelRequest
                        entity = await client.get_entity(hedef_grup)
                        await client(JoinChannelRequest(entity))
                        
                        # Üye sayısını kontrol et
                        full_channel = await client(GetFullChannelRequest(entity))
                        member_count = full_channel.full_chat.participants_count
                        
                        if member_count < 20:
                            print(f"[{client_name}] 📉 @{hedef_grup} -> Üye sayısı çok az ({member_count}). Kara listeye alınıyor...")
                            async with state_lock:
                                save_to_list(hedef_grup, BLACKLIST_FILE)
                            entity = None
                        else:
                            # Son mesaj tarihini kontrol et (Aktiflik)
                            try:
                                messages = await client.get_messages(entity, limit=1)
                                if messages:
                                    last_msg = messages[0]
                                    from datetime import datetime, timezone
                                    now = datetime.now(timezone.utc)
                                    delta = now - last_msg.date
                                    if delta.days >= 30:
                                        print(f"[{client_name}] 💤 @{hedef_grup} -> Son mesaj {delta.days} gün önce atılmış (İnaktif). Kara listeye alınıyor...")
                                        async with state_lock:
                                            save_to_list(hedef_grup, BLACKLIST_FILE)
                                        entity = None
                            except Exception as msg_check_err:
                                print(f"[{client_name}] ⚠️ Son mesaj kontrol edilemedi: {msg_check_err}")
                                
                            if entity:
                                join_count += 1
                                print(f"[{client_name}] ✅ Gruba girildi: @{hedef_grup} ({member_count} üye). Bu turda katılım: {join_count}/3")
                                joined_dialogs[grup_lower] = entity
                                    
                                # Anti-spam delay after joining a new group
                                join_sleep = random.randint(30, 60)
                                print(f"[{client_name}] ⏳ Yeni gruba girildi. Güvenlik için {join_sleep} saniye bekleniyor...")
                                await asyncio.sleep(join_sleep)
                    except FloodWaitError as e:
                        if e.seconds <= 300:
                            print(f"[{client_name}] ⏳ Katılma limiti (Flood). {e.seconds} saniye bekleniyor...")
                            await asyncio.sleep(e.seconds)
                            # Flood bittikten sonra devam et, tamamen durma
                        else:
                            print(f"[{client_name}] ⚠️ Katılma limiti yüksek ({e.seconds}sn). {e.seconds}sn bekleniyor...")
                            await asyncio.sleep(e.seconds)
                        entity = None
                    except (ChannelPrivateError,):
                        print(f"[{client_name}] 🔒 @{hedef_grup} -> Özel kanal/grup. Kara listeye ekleniyor...")
                        async with state_lock:
                            save_to_list(hedef_grup, BLACKLIST_FILE)
                        entity = None
                    except Exception as join_err:
                        err_msg = str(join_err)
                        err_type = type(join_err).__name__
                        # Var olmayan, geçersiz veya bulunamayan grupları kara listeye al
                        if any(x in err_msg.lower() for x in ['no user has', 'no username', 'not found', 'invalid']) or isinstance(join_err, (UsernameNotOccupiedError, UsernameInvalidError, ValueError)):
                            print(f"[{client_name}] ❌ @{hedef_grup} -> Bulunamadı/Geçersiz ({err_type}). Kara listeye ekleniyor...")
                            async with state_lock:
                                save_to_list(hedef_grup, BLACKLIST_FILE)
                        else:
                            print(f"[{client_name}] ⚠️ Gruba girilemedi (@{hedef_grup}): {err_type} - {join_err}")
                        entity = None

                if not entity:
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    continue

                # ═══════════════════════════════════════════
                # ADIM 2: Online kontrolü (HER GRUP İÇİN)
                # ═══════════════════════════════════════════
                online_ok = False
                try:
                    from telethon.tl.functions.channels import GetFullChannelRequest
                    full_channel = await client(GetFullChannelRequest(entity))
                    online_count = getattr(full_channel.full_chat, 'online_count', None)
                    
                    # Ayrıca member_count'u da güncelle (önbellek eski olabilir)
                    fresh_member_count = getattr(full_channel.full_chat, 'participants_count', None)
                    if fresh_member_count is not None and fresh_member_count < 20:
                        print(f"[{client_name}] 📉 @{hedef_grup} -> Güncel üye sayısı çok az ({fresh_member_count} < 20). Kara listeye alınıyor...")
                        async with state_lock:
                            save_to_list(hedef_grup, BLACKLIST_FILE)
                        continue
                    
                    if online_count is not None:
                        if online_count < 10:
                            print(f"[{client_name}] 📉 @{hedef_grup} -> Anlık online: {online_count} kişi (< 10). Kara listeye alınıyor...")
                            async with state_lock:
                                save_to_list(hedef_grup, BLACKLIST_FILE)
                            continue
                        else:
                            print(f"[{client_name}] 👥 @{hedef_grup} -> Online: {online_count} kişi ✓")
                            online_ok = True
                    else:
                        # Telegram online sayısını vermedi (gizli veya grup tipi desteklemiyor)
                        # Güvenli tarafta kal: üye sayısı yeterliyse gönder
                        if fresh_member_count and fresh_member_count >= 50:
                            print(f"[{client_name}] ℹ️ @{hedef_grup} -> Online sayısı gizli ama {fresh_member_count} üyeli. Mesaj gönderiliyor...")
                            online_ok = True
                        else:
                            print(f"[{client_name}] ⚠️ @{hedef_grup} -> Online sayısı gizli ve üye sayısı düşük ({fresh_member_count}). Atlanıyor...")
                            async with state_lock:
                                save_to_list(hedef_grup, PROGRESS_FILE)
                            continue
                            
                except FloodWaitError as e:
                    print(f"[{client_name}] ⏳ Online kontrol flood: {e.seconds}sn bekleniyor...")
                    await asyncio.sleep(e.seconds)
                    # Flood sonrası bu grubu atla, sonraki turda tekrar denenecek
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    continue
                except Exception as oc_err:
                    print(f"[{client_name}] ⚠️ @{hedef_grup} online kontrol hatası: {type(oc_err).__name__}. Atlanıyor...")
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    continue

                if not online_ok:
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    continue

                # ═══════════════════════════════════════════
                # ADIM 3: Mesaj gönder (Sadece tüm kontrollerden geçen gruplara)
                # ═══════════════════════════════════════════
                try:
                    msg_file = "message_2.txt" if "2" in client_name else "message.txt"
                    try:
                        with open(msg_file, "r", encoding="utf-8") as fm:
                            msg_to_send = fm.read()
                    except:
                        try:
                            with open("message.txt", "r", encoding="utf-8") as fm:
                                msg_to_send = fm.read()
                        except:
                            msg_to_send = f"⚠️ {msg_file} okunamadı!"
                        
                    if hedef_grup.lower() == "kuponceking":
                        msg_to_send = msg_to_send.replace("🤖 **Sipariş & Canlı Destek Botumuz:** @FroxyDestekBOT", "") \
                                                  .replace("🤖 **Sipariş & Canlı Destek Botumuz:** @KeyVadiSatisBot", "") \
                                                  .replace("bot", "sistem") \
                                                  .replace("Bot", "Sistem") \
                                                  .replace("🤖", "") \
                                                  .strip() + "\n"
                        print(f"[{client_name}] ✨ @{hedef_grup} için temizlenmiş mesaj kullanılıyor...")

                    # Spintax Uygula
                    msg_to_send = parse_spintax(msg_to_send)

                    await client.send_message(entity, msg_to_send)
                    print(f"[{client_name}] 📨 Mesaj gönderildi! @{hedef_grup}")
                    update_stats(sent=1)
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    
                    # Dinamik bekleme
                    ad_sleep_min = 600
                    ad_sleep_max = 1200
                    if os.path.exists("bot_config.json"):
                        try:
                            with open("bot_config.json", "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                                ad_sleep_min = cfg.get("ad_sleep_min", 600)
                                ad_sleep_max = cfg.get("ad_sleep_max", 1200)
                        except:
                            pass
                    
                    bekleme = random.randint(ad_sleep_min, ad_sleep_max)
                    print(f"[{client_name}] ⏳ {bekleme // 60} dakika {bekleme % 60} saniye bekleniyor...")
                    await asyncio.sleep(bekleme)

                except FloodWaitError as e:
                    raise e
                except SlowModeWaitError as e:
                    print(f"[{client_name}] ⏳ @{hedef_grup} -> Slow Mode aktif! {e.seconds} saniye beklemek gerekiyor. Pas geçiliyor...")
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                except UserBannedInChannelError:
                    print(f"[{client_name}] ❌ @{hedef_grup} -> Bu gruptan banlanmışız! Kara listeye ekleniyor...")
                    async with state_lock:
                        save_to_list(hedef_grup, BLACKLIST_FILE)
                except ChatWriteForbiddenError:
                    try:
                        is_broadcast = getattr(entity, 'broadcast', False)
                    except Exception:
                        is_broadcast = False
                    
                    if is_broadcast:
                        print(f"[{client_name}] 📢 @{hedef_grup} -> KANAL! Sadece admin yazabilir. Kara listeye ekleniyor...")
                        async with state_lock:
                            save_to_list(hedef_grup, BLACKLIST_FILE)
                    else:
                        print(f"[{client_name}] 🔒 @{hedef_grup} -> Yazma izni yok. Pas geçiliyor...")
                        async with state_lock:
                            save_to_list(hedef_grup, PROGRESS_FILE)
                except Exception as msg_err:
                    print(f"[{client_name}] ⚠️ Mesaj hatası: {msg_err}")
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)

            except FloodWaitError as e:
                print(f"[{client_name}] 🚨 Flood! {e.seconds}sn bekleniyor...")
                await asyncio.sleep(e.seconds)
            except (UsernameNotOccupiedError, UsernameInvalidError, ValueError):
                print(f"[{client_name}] ❌ @{hedef_grup} bulunamadı/geçersiz. Kara listeye ekleniyor...")
                async with state_lock:
                    save_to_list(hedef_grup, BLACKLIST_FILE)
            except Exception as e:
                err_msg = str(e)
                if 'no user has' in err_msg.lower() or 'not found' in err_msg.lower():
                    print(f"[{client_name}] ❌ @{hedef_grup} -> {type(e).__name__}: Bulunamadı. Kara listeye ekleniyor...")
                    async with state_lock:
                        save_to_list(hedef_grup, BLACKLIST_FILE)
                else:
                    print(f"[{client_name}] ⚠️ @{hedef_grup} genel hatası: {type(e).__name__} - {e}")
                    async with state_lock:
                        save_to_list(hedef_grup, BLACKLIST_FILE)
            finally:
                async with state_lock:
                    if hedef_grup in active_jobs:
                        active_jobs.remove(hedef_grup)

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
            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(merged_black) + '\n')
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
        
        # Yeni döngü öncesi otomatik grup keşfi
        print(f"\n🔍 Yeni döngü için Auto-Scraper çalıştırılıyor...")
        await auto_scrape_groups(first_client, first_name)
        
        await asyncio.sleep(3600) # 1 saat bekle ve baştan başla
    
    # Clean up (unreachable but formal)
    for client, name, _ in active_clients:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
