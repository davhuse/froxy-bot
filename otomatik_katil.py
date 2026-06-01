import asyncio
import random
import os
import json
import requests
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
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
    "dolapdestek0", "Nightsatis", "eticaretlab", "ticaretmerkezi", "bedavainternetssohbet",
    "ticaretmeydani", "ikincieltr", "BuyukClup", "DijitalPazarTR", "YazilimLisans",
    "PremiumHesapSatiss", "EticaretTR", "WebmasterTR", "SMMBayiTR", "firsattdiyari",
    "Turkishbazaar22", "firsatmarketi", "trendindirimler", "eticaret_tedarikcileri", "FreelancerTurkiye",
    "AITurkiye", "YazilimciGelistirme", "HesapSatisTR", "EpisSatis", "OyunHesapTR",
    "DijitalMarketim", "UcuzaLisans", "GirisimciGrup", "PazaryeriSaticilari", "DropshippingTR",
    "AmazonSellersTR", "WebmasterSatis", "SEO_Turkiye", "SosyalMedyaTicaret", "BotSatisTR",
    "AdsenseSatis", "DomainPazari", "YazilimDestek", "TeknolojiSohbet", "ikincieltelefon",
    "ikincielelektronik", "FreelanceIsIlani", "DesignerTR", "CoderTurkiye", "PythonTurkiye",
    "JavaScript_TR", "CyberSecurity_TR", "KriptoTicaret", "FinansHaberTR", "StartupTR",
    "YatirimciGrup", "ToptanUrun_TR", "UygunFiyatliUrunler", "KuponPaylasim", "TurkiyeReklamGrubu",
    "WebmasterYardimlasma", "SMMPanelTurkiye", "HesapSatisPazari", "LisansPazari", "Oyun_Hesap_Alim_Satim",
    "PremiumHesaplar_TR", "Canva_Pro_Yardimlasma", "Adobe_Creative_Cloud_TR", "Windows_Office_Key_Satis", "Yazilimci_Is_Ilanlari",
    "Freelance_Turkiye_Grup", "Girisimcilik_Sohbetleri", "E_Ticaret_Satis_Taktikleri", "Dropshipping_Turkiye_Sohbet", "Amazon_FBA_Turkiye",
    "Trendyol_Saticilari_Grubu", "Hepsiburada_Saticilari", "Shopify_Turkiye_Yardim", "Kripto_Para_Sohbet_TR", "Altcoin_Alim_Satim_Haber",
    "Airdrop_Firsatlari_TR", "Ekonomi_Gundem_TR", "Borsa_Istanbul_Sohbet", "Teknoloji_Dunyasi_Haber", "Donanim_Haber_Sohbet",
    "Yazilim_Kulu_Yardim", "Python_Turkiye_Gelistirici", "Java_Turkiye_Toplulugu", "PHP_Laravel_TR", "React_Vue_Turkiye",
    "Siber_Guvenlik_Platformu", "Hack_Haber_Turkiye", "Linux_Turkiye_Kullanicilari", "Oyun_Haber_Sohbet", "Steam_Indirimleri_TR",
    "Epic_Games_Firsatlari", "Netflix_Disney_Premium", "Spotify_Premium_Hizmet", "YouTube_Premium_TR", "Insta_Twitter_Takipci",
    "TikTok_Etkilesim_Grubu", "satilikilanlar", "ikincielarabailan", "sahibindenarabalar", "ShopifyUzmani",
    "stoksuzparakazan", "arabalar_ikinciel", "Gurcistanticaret", "magazanolsunbayi", "ticaretvarburada",
    "eticaretyardimlasmaa", "ilan_ver", "is_ilanlari_grubu", "FreelanceWorkTR", "kuponindirimsatis",
    "kuponsatisgrup", "kuponhesapsatis", "kuponsat", "KuponindirimPazari", "kuponceking",
    "kuponkodalsat", "kupongrupta", "satcek", "kuponceksatis", "yazilimci_grubu",
    "phpturkiye", "linux_turkiye", "cppturkiye", "seoyedek", "ikincielpazar",
    "smmbayim", "eticaretplatformu", "ikincielsatis", "freelanceyazilim", "oyunalisveris",
    "dijitalpazar", "kriptosohbet", "borsasohbet", "yardimlasmagrubu", "freelancertr",
    "teknolojihaber", "toptangrubu", "ucuzlisanslar", "premiumhesaplar", "smmhizmetleri",
    "sosyalmedyadestek", "tasarimciyardim", "yazilimciyardim", "dropshippingturkiye", "amazonfbatr",
    "trendyolsaticilar", "hepsiburadasaticilar", "spotifygenel", "youtubepremiumtr", "netflixpremiumtr",
    "oyunhesaplarisatis", "steamcuzdankodu", "KuponSatis", "SosyalMedyaPazari", "AdsenseTurkiye",
    "FreelancerYazilimci", "TeknolojiSohbetleri", "WebTasarimDestek", "SMMHizmeti", "KriptoSohbetTR",
    "EpinDestek", "OyunAlSat", "ikincielesya", "GirisimciToplulugu", "TrendyolDestekSohbet",
    "AmazonSellersTRGroup", "ShopifyDestek", "BorsaYardim", "EkonomiToplulugu", "DesignerTurkiye",
    "CoderDestekTR", "EpinPazari", "HesapSatisGenel", "LisansBayi", "SosyalMedyaTicaretGrubu",
    "EpinAlSat", "SMMPanelTurk", "AdsenseDestekTR", "FreelanceIsIlanlariTR", "KriptoKazan",
    "IndirimFirsat", "ToptanGiyimTR", "DropshippingTRyardim", "AmazonFBAyardim", "TrendyolPazaryeri",
    "WebmasterDestekTR", "PythonSohbet", "JavaYardimlasma", "ReactTR", "NodejsTR",
    "SiberGundem", "OyunPazariTR", "SteamOyunTR", "EpicGamesFirsatTR", "PremiumUyelikTR",
    "CanvaTasarimYardim", "AdobeTRYardim", "WindowsOfficeKey", "YazilimIsFirsatlari", "GirisimcilikSohbet",
    "ShopifyGirisim", "BorsaKriptoHaber", "FinansGundemTR", "GrafikTasarimDestek", "YazilimciSohbetleri",
    "EpinBayilik", "ZulaPazariTR", "WolfteamSatisTR", "MinecraftMacroTRGroup", "SpotifyDavet",
    "EpinKoduSatis", "WebTasarimYardim", "SMMPanelSatisGrubu", "AdsenseAlSat", "KriptoSohbetGrubu",
    "PremiumSatisTR", "SosyalMedyaDestekGrubu", "DropshippingTurk", "AmazonSellersYardim", "ShopifyDestekTR",
    "GrafikerDestekTR", "YazilimIlanTR", "EpinSatisPazari", "HesapAlimSatimTR", "ikincielalimsatimtr",
    "turkiyepazar", "turkcesmm", "sosyalmedyapazaritr", "dijitalpazaryeritr", "satisgrubu",
    "toptanvesatis", "ikincielalisveristr", "webmasteryardimlasmatr", "reklamgrubutr", "satiskanali",
    "dijitalurunsatis", "hesap_satis_tr", "epin_pazari", "lisans_alim_satim", "freelance_is_ilanlari_tr",
    "yazilimci_is_ilanlari_tr", "dropshipping_tr_destek", "amazon_satis_ortakligi", "trendyol_saticilari_tr", "hepsiburada_satis_toplulugu",
    "kriptosatistr", "borsa_sohbet_tr", "teknolojialimsatim", "donanimsatistr", "smmbayilertr",
    "smmhizmetleripazari", "sosyalmedyaalimsatim", "ikincieltelefontr", "ikincielelektroniktr", "freelancework_tr",
    "designer_is_ilanlari", "coder_is_ilanlari", "pythontr_satis", "javascripttr_satis", "siberguvenliktr_satis",
    "linux_kullanicilari_tr", "oyun_hesap_satis_pazari", "epicgames_firsatlari_tr", "premium_satis_pazari", "spotify_premium_tr",
    "youtube_premium_satis", "takipcialsat", "tiktok_hesap_satis", "satilik_domainler", "adsense_alim_satim",
    "dropshipping_turk", "eticaret_tedarik", "freelance_destek_tr", "ticaretmeydanitr", "kupon_satis_tr",
    "AmazonTrGenelSohbet", "AyakkabiSanati", "BuyukFirsat", "CasinoBeko", "ElitSohbettt",
    "Gardrops", "HESAPACCOUNT1", "IWEfTGD7OCBjY2I8", "KorgPa2xPa800", "KriptoSozlukTVPiyasaMuhabbeti",
    "N_A_F_A_Smm", "Panel_Member_Premium_Ban_buy", "Prof_Amazon8", "ReklamYaptr", "Saatlersi",
    "TAL0NE7SFiLAuNDf", "Turkiye_telefon_pazari", "VevoBahis_NgsBahis", "XushnudMFYreklama", "Yardimlasmag",
    "YouTuBeAboneKazan", "YuceKuponSatis", "amaev_pro", "amazon_fbauz1", "amazonfbasellers",
    "bayanaktuel", "borsao", "buy_Panel_Premium_Members_Adder", "buyukdolaplar", "dakikadoksan",
    "dijitalpazarlamatr", "diyarbakirikincielarac", "dolapa", "dolapdesteks", "dolapgardropsdestek",
    "dolaplink", "dolaplinkleri0", "dolapotomasyon", "dolaptakipbegeniteklif", "dolapxgardrops",
    "dolapyildizlari", "ekpssyardimlasma2026", "el_ikincim", "erdil_satis", "finansalpusula",
    "firsat0", "firsatbildirimi", "firsatcik", "firsatlarsizinle", "firsats",
    "firsatspt", "freelancertoplulugu", "gardrops23", "gardropslink", "guvenilirshowcularx",
    "h03244320222", "huuvelbagi", "icon_webmasters_cpa", "iddaatahmin_tr", "ikinciel01chat",
    "ikincielantalya", "ikincielkralligi", "ikincielotoalimsatimhizmeti", "ikincieltoptanalsat", "ikincii_el",
    "indirim363", "indirimc", "indirimcin", "indirimciyizbiz", "indirimdeal",
    "indirimfirsatburada", "indirimkodusatis", "indirimkurt3144", "indirimz", "iqostereaaa",
    "istanbultereavozol", "ithaltptan", "izmirpazar", "kampanyam", "kampanyaradari",
    "kendireklaminiyap", "kpss3", "kripto1", "kriptoe", "kuponceksatisi",
    "kuponl", "kuponsatislari0", "mehmet1uzun", "mesutkupon", "neastronhesap",
    "onemlifirsatlar", "otoemlakajans", "pazaryerialsat", "pegasusucakbileti", "referansreklam1",
    "refkasAxMxMA", "reklama_bardankol", "reklamvereferanssss", "reklamyap", "sanalpos3d",
    "satisrefim", "shawtysaha", "sistemcin", "smmpanelkur", "smsngsatis",
    "sosyalmedyaalimsatimticaret", "sultanbeyliikinciel0", "svp_referans", "tekstiltoptancilari", "temukazan",
    "temulinkpaylasimtemu", "tereaatr1", "testnet_aidrop_on_satis_kripto", "tevkil_yardimlasma", "ticar4t",
    "ticaretguvenilir", "ticaretsaha", "toptankozmetik47", "trendyol8", "trendyolsatkazan",
    "turkey_wholesale", "ucbosspubgHESAP", "ucuzaalisvers", "uye_ekleme_satis", "uzaktan_freelancee",
    "webmasterdestek", "webmasterscafe", "yazilimci_hanim", "yazilimcigencler", "yazilimciiiadam",
    "yazilimcilarburada", "yukseklisansdoktora", "zesetsyco", "zirvedekidolaplar",
]

PROGRESS_FILE = 'progress.txt'
BLACKLIST_FILE = 'blacklist.txt'

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
    ad_sleep_min = 180
    ad_sleep_max = 300
    
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                string_session_key = cfg.get("ad_string_session", "")
                string_session_key_2 = cfg.get("ad_string_session_2", "")
                ad_sleep_min = cfg.get("ad_sleep_min", 180)
                ad_sleep_max = cfg.get("ad_sleep_max", 300)
        except:
            pass

    active_clients = []
    
    # Client 1
    if string_session_key:
        print("🔑 1. Hesap: StringSession kullanılarak bağlanılıyor...")
        from telethon.sessions import StringSession
        client1 = TelegramClient(StringSession(string_session_key), api_id, api_hash)
        await client1.connect()
        if await client1.is_user_authorized():
            active_clients.append((client1, "Hesap #1", {}))
            print("✅ 1. Hesap yetkilendirildi.")
        else:
            print("❌ HATA: 1. Hesap yetkilendirilmemiş!")
            
    # Client 2
    if string_session_key_2:
        print("🔑 2. Hesap: StringSession kullanılarak bağlanılıyor...")
        from telethon.sessions import StringSession
        client2 = TelegramClient(StringSession(string_session_key_2), api_id, api_hash)
        await client2.connect()
        if await client2.is_user_authorized():
            active_clients.append((client2, "Hesap #2", {}))
            print("✅ 2. Hesap yetkilendirildi.")
        else:
            print("❌ HATA: 2. Hesap yetkilendirilmemiş!")

    # Fallback to local session file if no string session is configured at all
    if not string_session_key and not string_session_key_2:
        print("📂 Yerel oturum dosyası kullanılarak bağlanılıyor...")
        client1 = TelegramClient(SESSION_NAME, api_id, api_hash)
        await client1.connect()
        if await client1.is_user_authorized():
            active_clients.append((client1, "Yerel Hesap", {}))
            print("✅ Yerel hesap yetkilendirildi.")
        else:
            print("❌ HATA: Yerel hesap yetkilendirilmemiş!")
            import sys
            sys.exit(1)
            
    if not active_clients:
        print("❌ HATA: Hiçbir aktif ve yetkili Telegram hesabı bulunamadı!")
        import sys
        sys.exit(1)

    state_lock = asyncio.Lock()
    active_jobs = set()

    async def run_worker(client, client_name, joined_dialogs):
        print(f"🚀 Worker {client_name} diyalogları önbelleğe alınıyor...")
        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    if dialog.entity.username:
                        joined_dialogs[dialog.entity.username.lower()] = dialog.entity
            print(f"✅ Worker {client_name}: {len(joined_dialogs)} diyalog önbelleğe alındı.")
        except Exception as e:
            print(f"⚠️ Worker {client_name} önbellek hatası: {e}")

        while True:
            hedef_grup = None
            
            async with state_lock:
                kullanilacak_gruplar = []
                blacklist = get_list(BLACKLIST_FILE)
                for g in gruplar:
                    if g not in blacklist:
                        kullanilacak_gruplar.append(g)
                        
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
                
                # Önbellekte varsa doğrudan entity al ve Join/GetFullChannel adımlarını atla
                if grup_lower in joined_dialogs:
                    entity = joined_dialogs[grup_lower]
                    print(f"[{client_name}] ✅ Zaten gruptayız (Önbellekten): @{hedef_grup}")
                else:
                    # Gruba katıl (Zaten varsan hata vermez)
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
                            continue
                            
                        print(f"[{client_name}] ✅ Gruba girildi: @{hedef_grup} ({member_count} üye)")
                        joined_dialogs[grup_lower] = entity
                    except FloodWaitError as e:
                        raise e
                    except Exception as join_err:
                        print(f"[{client_name}] ⚠️ Gruba girilemedi: {join_err}")
                        pass

                if not entity:
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    continue

                # Mesaj gönder
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
                        msg_to_send = msg_to_send.replace("🤖 **Sipariş & Canlı Destek Botumuz:** @KeyVadiSatisBot", "") \
                                                  .replace("bot", "sistem") \
                                                  .replace("Bot", "Sistem") \
                                                  .replace("🤖", "") \
                                                  .strip() + "\n"
                        print(f"[{client_name}] ✨ @{hedef_grup} için temizlenmiş mesaj kullanılıyor...")

                    await client.send_message(entity, msg_to_send)
                    print(f"[{client_name}] 📨 Mesaj gönderildi!")
                    async with state_lock:
                        save_to_list(hedef_grup, PROGRESS_FILE)
                    
                    # Dinamik bekleme
                    ad_sleep_min = 180
                    ad_sleep_max = 300
                    if os.path.exists("bot_config.json"):
                        try:
                            with open("bot_config.json", "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                                ad_sleep_min = cfg.get("ad_sleep_min", 180)
                                ad_sleep_max = cfg.get("ad_sleep_max", 300)
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
            except (UsernameNotOccupiedError, UsernameInvalidError):
                print(f"[{client_name}] ❌ @{hedef_grup} bulunamadı. Kara listeye ekleniyor...")
                async with state_lock:
                    save_to_list(hedef_grup, BLACKLIST_FILE)
            except Exception as e:
                print(f"[{client_name}] ⚠️ @{hedef_grup} genel hatası: {type(e).__name__}")
                async with state_lock:
                    save_to_list(hedef_grup, PROGRESS_FILE)
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
        
        await asyncio.sleep(3600) # 1 saat bekle ve baştan başla
    
    # Clean up (unreachable but formal)
    for client, name, _ in active_clients:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
