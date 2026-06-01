import asyncio
import random
import os
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
    "ticaretmeydani", "ikincieltr", "BuyukClup",
    "DijitalPazarTR", "YazilimLisans", "PremiumHesapSatiss", "EticaretTR",
    "WebmasterTR", "SMMBayiTR", "firsattdiyari", "Turkishbazaar22",
    "firsatmarketi", "trendindirimler", "eticaret_tedarikcileri",
    "FreelancerTurkiye", "AITurkiye", "YazilimciGelistirme", "HesapSatisTR",
    "EpisSatis", "OyunHesapTR", "DijitalMarketim", "UcuzaLisans",
    "GirisimciGrup", "PazaryeriSaticilari", "DropshippingTR", "AmazonSellersTR",
    "WebmasterSatis", "SEO_Turkiye", "SosyalMedyaTicaret", "BotSatisTR",
    "AdsenseSatis", "DomainPazari", "YazilimDestek", "TeknolojiSohbet",
    "ikincieltelefon", "ikincielelektronik", "FreelanceIsIlani", "DesignerTR",
    "CoderTurkiye", "PythonTurkiye", "JavaScript_TR", "CyberSecurity_TR",
    "KriptoTicaret", "FinansHaberTR", "StartupTR", "YatirimciGrup",
    "ToptanUrun_TR", "UygunFiyatliUrunler", "KuponPaylasim",
    "TurkiyeReklamGrubu", "WebmasterYardimlasma", "SMMPanelTurkiye",
    "HesapSatisPazari", "LisansPazari", "Oyun_Hesap_Alim_Satim", "PremiumHesaplar_TR",
    "Canva_Pro_Yardimlasma", "Adobe_Creative_Cloud_TR", "Windows_Office_Key_Satis",
    "Yazilimci_Is_Ilanlari", "Freelance_Turkiye_Grup", "Girisimcilik_Sohbetleri",
    "E_Ticaret_Satis_Taktikleri", "Dropshipping_Turkiye_Sohbet", "Amazon_FBA_Turkiye",
    "Trendyol_Saticilari_Grubu", "Hepsiburada_Saticilari", "Shopify_Turkiye_Yardim",
    "Kripto_Para_Sohbet_TR", "Altcoin_Alim_Satim_Haber", "Airdrop_Firsatlari_TR",
    "Ekonomi_Gundem_TR", "Borsa_Istanbul_Sohbet", "Teknoloji_Dunyasi_Haber",
    "Donanim_Haber_Sohbet", "Yazilim_Kulu_Yardim", "Python_Turkiye_Gelistirici",
    "Java_Turkiye_Toplulugu", "PHP_Laravel_TR", "React_Vue_Turkiye",
    "Siber_Guvenlik_Platformu", "Hack_Haber_Turkiye", "Linux_Turkiye_Kullanicilari",
    "Oyun_Haber_Sohbet", "Steam_Indirimleri_TR", "Epic_Games_Firsatlari",
    "Netflix_Disney_Premium", "Spotify_Premium_Hizmet", "YouTube_Premium_TR",
    "Insta_Twitter_Takipci", "TikTok_Etkilesim_Grubu",
    "satilikilanlar", "ikincielarabailan", "sahibindenarabalar", "ShopifyUzmani",
    "stoksuzparakazan", "arabalar_ikinciel", "Gurcistanticaret", "magazanolsunbayi",
    "ticaretvarburada", "eticaretyardimlasmaa", "ilan_ver", "is_ilanlari_grubu",
    "FreelanceWorkTR", "kuponindirimsatis", "kuponsatisgrup", "kuponhesapsatis",
    "kuponsat", "KuponindirimPazari", "kuponceking", "kuponkodalsat",
    "kupongrupta", "satcek", "kuponceksatis", "yazilimci_grubu", "phpturkiye",
    "linux_turkiye", "cppturkiye", "seoyedek", "ikincielpazar",
    "smmbayim", "eticaretplatformu", "ikincielsatis", "freelanceyazilim", "oyunalisveris",
    "dijitalpazar", "webmastersatis", "kriptosohbet", "borsasohbet", "yardimlasmagrubu",
    "freelancertr", "teknolojihaber", "toptangrubu", "ucuzlisanslar", "premiumhesaplar",
    "smmhizmetleri", "sosyalmedyadestek", "tasarimciyardim", "yazilimciyardim", "dropshippingturkiye",
    "amazonfbatr", "trendyolsaticilar", "hepsiburadasaticilar", "spotifygenel", "youtubepremiumtr",
    "netflixpremiumtr", "oyunhesaplarisatis", "steamcuzdankodu", "KuponSatis", "SosyalMedyaPazari",
    "AdsenseTurkiye", "FreelancerYazilimci", "TeknolojiSohbetleri", "WebTasarimDestek", "SMMHizmeti",
    "KriptoSohbetTR", "EpinDestek", "OyunAlSat", "ikincielesya", "GirisimciToplulugu",
    "TrendyolDestekSohbet", "AmazonSellersTRGroup", "ShopifyDestek", "BorsaYardim", "EkonomiToplulugu",
    "DesignerTurkiye", "CoderDestekTR", "EpinPazari", "HesapSatisGenel", "LisansBayi",
    "SosyalMedyaTicaretGrubu", "EpinAlSat", "SMMPanelTurk", "AdsenseDestekTR",
    "FreelanceIsIlanlariTR", "KriptoKazan", "IndirimFirsat", "ToptanGiyimTR",
    "DropshippingTRyardim", "AmazonFBAyardim", "TrendyolPazaryeri", "WebmasterDestekTR",
    "PythonSohbet", "JavaYardimlasma", "ReactTR", "NodejsTR",
    "SiberGundem", "OyunPazariTR", "SteamOyunTR", "EpicGamesFirsatTR",
    "PremiumUyelikTR", "CanvaTasarimYardim", "AdobeTRYardim", "WindowsOfficeKey",
    "YazilimIsFirsatlari", "GirisimcilikSohbet", "ShopifyGirisim", "BorsaKriptoHaber",
    "FinansGundemTR", "GrafikTasarimDestek", "YazilimciSohbetleri", "EpinBayilik",
    "ZulaPazariTR", "WolfteamSatisTR", "MinecraftMacroTRGroup", "SpotifyDavet",
    "EpinKoduSatis", "WebTasarimYardim", "SMMPanelSatisGrubu", "AdsenseAlSat",
    "KriptoSohbetGrubu", "PremiumSatisTR", "SosyalMedyaDestekGrubu", "DropshippingTurk",
    "AmazonSellersYardim", "ShopifyDestekTR", "GrafikerDestekTR", "YazilimIlanTR",
    "EpinSatisPazari", "HesapAlimSatimTR"
]

PROGRESS_FILE = 'progress.txt'
BLACKLIST_FILE = 'blacklist.txt'

def get_list(dosya):
    if os.path.exists(dosya):
        with open(dosya, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_list(grup, dosya):
    with open(dosya, 'a') as f:
        f.write(grup + '\n')

async def main():
    print("\n🚀 Habil Reklam Botu v2 - Akıllı Mod")
    print("-----------------------------------")

    import json
    string_session_key = ""
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                string_session_key = cfg.get("ad_string_session", "")
        except:
            pass

    if string_session_key:
        print("🔑 StringSession kullanılarak bağlanılıyor...")
        from telethon.sessions import StringSession
        client = TelegramClient(StringSession(string_session_key), api_id, api_hash)
    else:
        print("📂 Yerel oturum dosyası kullanılarak bağlanılıyor...")
        client = TelegramClient(SESSION_NAME, api_id, api_hash)
        
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ HATA: Oturum açılmamış! Lütfen önce web sitesini kapatıp terminal üzerinden 'python otomatik_katil.py' komutuyla bir kereliğe mahsus oturum açınız.")
        import sys
        sys.exit(1)

    while True:
        kullanilacak_gruplar = []
        blacklist = get_list(BLACKLIST_FILE)

        # Temiz grupları seç
        for g in gruplar:
            if g not in blacklist:
                kullanilacak_gruplar.append(g)

        if not kullanilacak_gruplar:
            print("⚠️ Listede mesaj atılabilecek aktif grup kalmadı!")
            break

        print(f"\n📢 Döngü başlıyor... Toplam {len(gruplar)} gruptan {len(kullanilacak_gruplar)} tanesine mesaj atılacak (Boş kanallar elendi).")
        
        done_groups = get_list(PROGRESS_FILE)
        if done_groups and len(done_groups) < len(kullanilacak_gruplar):
            print(f"🔄 Kaldığın yerden devam ediliyor ({len(done_groups)} grup geçildi)...")
        elif done_groups:
             # Eğer liste tamamsa ama döngü baştan başlayacaksa dosyayı temizle
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
            done_groups = set()

        for i, grup in enumerate(kullanilacak_gruplar, 1):
            if grup in done_groups:
                continue

            try:
                print(f"\n[{i}/{len(kullanilacak_gruplar)}] 🔍 @{grup} denetleniyor...")
                
                # Gruba katıl (Zaten varsan hata vermez)
                try:
                    from telethon.tl.functions.channels import GetFullChannelRequest
                    await client(JoinChannelRequest(grup))
                    
                    # Üye sayısını kontrol et
                    full_channel = await client(GetFullChannelRequest(grup))
                    member_count = full_channel.full_chat.participants_count
                    
                    if member_count < 20:
                        print(f"📉 @{grup} -> Üye sayısı çok az ({member_count}). Kara listeye alınıyor...")
                        save_to_list(grup, BLACKLIST_FILE)
                        continue
                        
                    print(f"✅ Gruba girildi: @{grup} ({member_count} üye)")
                except Exception as join_err:
                    pass

                # Mesaj gönder
                try:
                    try:
                        with open("message.txt", "r", encoding="utf-8") as fm:
                            msg_to_send = fm.read()
                    except:
                        msg_to_send = "⚠️ message.txt okunamadı!"
                    # Eğer kanal @kuponceking ise 'bot' kelimelerini temizle
                    if grup.lower() == "kuponceking":
                        # Bot sipariş linkini tamamen kaldır, sadece Destek kalsın
                        msg_to_send = msg_to_send.replace("🤖 Sipariş & Canlı Destek Botu: @FroxyDestekBOT", "") \
                                                  .replace("bot", "sistem") \
                                                  .replace("Bot", "Sistem") \
                                                  .replace("🤖", "") \
                                                  .strip() + "\n" # Fazla boşlukları temizle
                        print(f"✨ @{grup} için temizlenmiş (sadece destek) mesaj kullanılıyor...")

                    await client.send_message(grup, msg_to_send)
                    print(f"📨 Mesaj gönderildi!")
                    save_to_list(grup, PROGRESS_FILE)
                    
                    bekleme = random.randint(570, 630) # Anti-ban: 10 dakika aralıkla (570-630 saniye)
                    print(f"⏳ {bekleme // 60} dakika bekleniyor...")
                    await asyncio.sleep(bekleme)

                except SlowModeWaitError as e:
                    print(f"⏳ @{grup} -> Slow Mode aktif! {e.seconds} saniye beklemek gerekiyor. Bu döngüde pas geçiliyor...")
                    save_to_list(grup, PROGRESS_FILE)
                except UserBannedInChannelError:
                    print(f"❌ @{grup} -> Bu gruptan banlanmışız! Kara listeye ekleniyor...")
                    save_to_list(grup, BLACKLIST_FILE)
                except ChatWriteForbiddenError:
                    try:
                        entity = await client.get_entity(grup)
                        is_broadcast = getattr(entity, 'broadcast', False)
                    except Exception:
                        is_broadcast = False
                    
                    if is_broadcast:
                        print(f"📢 @{grup} -> KANAL (Yayın kanalı)! Sadece admin yazabilir. Kara listeye ekleniyor...")
                        save_to_list(grup, BLACKLIST_FILE)
                    else:
                        print(f"🔒 @{grup} -> Yazma izni yok (Grup geçici olarak kilitli veya susturulduk). Pas geçiliyor...")
                        save_to_list(grup, PROGRESS_FILE)
                except Exception as msg_err:
                    print(f"⚠️ Mesaj hatası: {msg_err}")
                    save_to_list(grup, PROGRESS_FILE)

            except FloodWaitError as e:
                print(f"🚨 Flood! {e.seconds}sn bekleniyor...")
                await asyncio.sleep(e.seconds)
            except (UsernameNotOccupiedError, UsernameInvalidError):
                print(f"❌ @{grup} bulunamadı. Kara listeye ekleniyor...")
                save_to_list(grup, BLACKLIST_FILE) # Artık bir daha bu gruba uğramayacak
            except Exception as e:
                print(f"⚠️ @{grup} genel hatası: {type(e).__name__}")
                save_to_list(grup, PROGRESS_FILE)

        print(f"\n✅ Tüm liste bitti! 1 SAAT ARA VERİLİYOR...")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        
        await asyncio.sleep(3600) # 1 saat bekle ve baştan başla
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
