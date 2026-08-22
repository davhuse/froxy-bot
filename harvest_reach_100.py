import asyncio
import aiohttp
import os
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# Load existing verified groups
with open("100_tam_dogrulanmis_kupon_kod_gruplari.json", "r", encoding="utf-8") as f:
    existing_verified = json.load(f).get("groups", [])

seen_usernames = {g["username"].lower() for g in existing_verified}
print(f"[*] Mevcut doğrulanmış kupon grubu: {len(seen_usernames)}")

# Generate rich variations for Turkish coupon, voucher, promo code, food discount, and digital code groups
KEYWORDS_POOL = [
    # Yemeksepeti
    "yemeksepeti", "yemeksepeti1", "yemeksepeti2", "yemeksepetitr", "yemeksepeti_tr",
    "yemeksepetiindirim", "yemeksepeti_indirim", "yemeksepeti_kupon", "yemeksepetikod",
    "yemeksepeti_kod", "yemeksepetifirsat", "yemeksepeti_firsat", "yemeksepetikampanya",
    "yemeksepeti_kampanya", "yemeksepetihesap", "yemeksepeti_hesap", "yemeksepetisohbet",
    "yemeksepeti_sohbet", "yemeksepeti_alsat", "yemeksepeti_pazar", "yemeksepetikupontr",
    "yemeksepetikodtr", "yemeksepetiindirimleri", "yemeksepetikayit", "yemeksepetiuye",
    
    # Migros & Market
    "migros", "migros1", "migros2", "migrostr", "migros_tr", "migrosindirim",
    "migros_indirim", "migroskod", "migros_kod", "migroscek", "migros_cek",
    "migrosmoney", "migros_money", "migrosfirsat", "migros_firsat", "migroskampanya",
    "migroshediyeceki", "migrosalsat", "migros_pazar", "migrossanalmarket", "sanalmarketkod",
    
    # Getir & Tıkla Gelsin & Yemek
    "tiklagelsin", "tiklagelsin1", "tiklagelsin_tr", "tiklagelsinkod", "tiklagelsin_kod",
    "tiklagelsinkupon", "tiklagelsin_kupon", "tiklagelsinindirim", "getir1", "getir2",
    "getirindirim", "getir_indirim", "getirkupon", "getir_kupon", "getiryemek",
    "getir_yemek", "getirfirsat", "getirkod", "getir_kod", "yemekkuponu", "yemek_kuponu",
    "yemekkodlari", "yemek_indirim", "indirimli_yemek", "aciktimkod", "dominoskupon",
    
    # Turna, Enuygun & Bilet
    "turna", "turna1", "turnatr", "turna_tr", "turnaucak", "turna_ucak", "turnabilet",
    "turna_bilet", "turnakupon", "turna_kupon", "turnakod", "turna_kod", "turnaindirim",
    "turna_indirim", "enuygun", "enuygun1", "enuyguntr", "enuygun_tr", "enuygunucak",
    "enuygun_ucak", "enuygunotobus", "enuygun_otobus", "enuygunbilet", "enuygun_bilet",
    "enuygunkupon", "enuygun_kupon", "enuygunkod", "enuygun_kod", "enuygunindirim",
    "obiletkupon", "obilet_kupon", "obiletindirim", "obilet_kod", "biletinialkod",
    "biletinial_kod", "biletinialkupon", "havaistkod", "havaist_indirim",
    
    # TV, Eğlence & Abonelik Kodları
    "todtv", "todtv1", "tod_tv", "todsuperlig", "tod_superlig", "todkod", "tod_kod",
    "todkupon", "tod_kupon", "todindirim", "tod_indirim", "ssportplus", "ssport_plus",
    "ssportkod", "ssport_kod", "exxenkod", "exxen_kod", "exxenkupon", "blutvkod",
    "blutv_kod", "gainkod", "storytelkod", "biletixkupon",
    
    # İnternet GB & Promosyon Kapak/Cips Kodları
    "dahadaha", "dahadahakod", "dahadaha_kod", "dahadahapuan", "dahadaha_puan",
    "dahadahahak", "dahadaha_hak", "kazandrio", "kazandriokod", "kazandrio_kod",
    "kazandriopuan", "kazandrio_puan", "kazandriocips", "kazandriokapak", "pepsikod",
    "pepsi_kod", "pepsikapak", "pepsi_kapak", "cipskod", "cips_kod", "cipsserit",
    "freebayt", "freebaytkod", "freebayt_kod", "freebaytinternet", "frebaytkod",
    "frebayt_kod", "frebaytpuan", "frebaytgb", "internetkod", "internet_kod",
    "gbkod", "gb_kod", "bedavagb", "internetpaketi", "hediyekod", "hediye_kod",
    
    # Kupon & Kod & Çek Pazarları
    "kuponsatis", "kupon_satis", "kuponalimsatim", "kupon_alim_satim", "kuponalsat",
    "kupon_al_sat", "kuponpazar", "kupon_pazar", "kuponpazari", "kupon_pazari",
    "kuponborsa", "kupon_borsa", "kuponborsasi", "kupon_borsasi", "kuponmarket",
    "kupon_market", "kuponmarketi", "kupon_marketi", "kupondepo", "kupon_depo",
    "kupondeposu", "kupon_deposu", "kuponmerkez", "kupon_merkez", "kuponmerkezi",
    "kupon_merkezi", "kupondunya", "kupondunyasi", "kuponvadisi", "kupondiyari",
    "kupondukkani", "kuponkulup", "kuponkulubu", "kuponhane", "kuponyeri",
    "kuponodasi", "kuponalemi", "kuponcu", "kuponcular", "kupon_tr", "kuponlar",
    
    # Çek Pazarları
    "ceksatis", "cek_satis", "cekalimsatim", "cek_alim_satim", "cekalsat", "cek_al_sat",
    "cekpazar", "cek_pazar", "cekpazari", "cek_pazari", "cekborsa", "cek_borsa",
    "cekborsasi", "cek_borsasi", "cekmarket", "cek_market", "cekmarketi", "cek_marketi",
    "cekdepo", "cek_depo", "cekdeposu", "cek_deposu", "cekmerkez", "cek_merkez",
    "cekmerkezi", "cek_merkezi", "cekdunya", "cekdunyasi", "cekvadisi", "cekdiyari",
    "cekdukkani", "cekkulup", "cekkulubu", "cekhane", "cekyeri", "cekodasi",
    "cekalemi", "cekci", "cekciler", "cek_tr", "cekler", "hediyeceki", "hediyecekleri",
    "marketceki", "marketcekleri", "alisverisceki", "alisveriscekleri", "cekbozdurma",
    
    # Kod Pazarları
    "kodsatis", "kod_satis", "kodalimsatim", "kod_alim_satim", "kodalsat", "kod_al_sat",
    "kodpazar", "kod_pazar", "kodpazari", "kod_pazari", "kodborsa", "kod_borsa",
    "kodborsasi", "kod_borsasi", "kodmarket", "kod_market", "kodmarketi", "kod_marketi",
    "koddepo", "kod_depo", "koddeposu", "kod_deposu", "kodmerkez", "kod_merkez",
    "kodmerkezi", "kod_merkezi", "koddunya", "koddunyasi", "kodvadisi", "koddiyari",
    "koddukkani", "kodkulup", "kodkulubu", "kodhane", "kodyeri", "kododasi",
    "kodalemi", "kodcu", "kodcular", "kod_tr", "kodlar", "indirimkod", "indirimkodlari",
    "promosyonkod", "promosyonkodlari", "kampanyakod", "kampanyakodlari", "firsatkod",
    "firsatkodlari", "avantajkod", "avantajkodlari"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "mining"
]

POSITIVE_SIGNALS = [
    "kupon", "kod", "çek", "cek", "indirim", "fırsat", "kampanya",
    "yemeksepeti", "migros", "turna", "enuygun", "tıkla gelsin", "tiklagelsin",
    "getir", "hediye çeki", "hediye ceki", "kapak", "cips", "pepsi", "bilet",
    "tod", "gb", "internet", "daha daha", "kazandrio", "freebayt", "money",
    "satılık", "satıyorum", "alınır", "alıyorum", "hesap", "lisans", "ticaret", "pazar"
]

async def harvest_full_100():
    all_target_usernames = set()
    for kw in KEYWORDS_POOL:
        all_target_usernames.add(kw.lower())
        all_target_usernames.add(f"{kw}tr".lower())
        all_target_usernames.add(f"{kw}_tr".lower())
        all_target_usernames.add(f"{kw}official".lower())
        all_target_usernames.add(f"{kw}_official".lower())
        all_target_usernames.add(f"{kw}grup".lower())
        all_target_usernames.add(f"{kw}_grup".lower())
        all_target_usernames.add(f"{kw}grubu".lower())
        all_target_usernames.add(f"{kw}_grubu".lower())
        all_target_usernames.add(f"{kw}chat".lower())
        all_target_usernames.add(f"{kw}_chat".lower())
        all_target_usernames.add(f"{kw}1".lower())
        all_target_usernames.add(f"{kw}2".lower())
        
    candidates_to_check = [u for u in all_target_usernames if u not in seen_usernames]
    print(f"[*] Taranacak potansiyel hedef kullanıcı adı: {len(candidates_to_check)}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    connector = aiohttp.TCPConnector(limit=40)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(20)
        
        async def verify_url(u):
            async with semaphore:
                url = f"https://t.me/{u}"
                try:
                    async with session.get(url, timeout=7) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            soup = BeautifulSoup(html, "html.parser")
                            title_el = soup.find("div", class_="tgme_page_title")
                            extra_el = soup.find("div", class_="tgme_page_extra")
                            desc_el = soup.find("div", class_="tgme_page_description")
                            
                            title = title_el.text.strip() if title_el else ""
                            extra = extra_el.text.strip() if extra_el else ""
                            desc = desc_el.text.strip() if desc_el else ""
                            
                            combined = f"{title}\n{desc}".lower()
                            if any(ew in combined for ew in EXCLUDE_WORDS):
                                return
                                
                            is_group = "members" in extra.lower() or "online" in extra.lower() or "üye" in extra.lower()
                            if is_group:
                                m_cnt = 0
                                num_match = re.search(r"([\d\s]+)\s*(?:members|üye)", extra.replace("\xa0", " "))
                                if num_match:
                                    try:
                                        m_cnt = int(num_match.group(1).replace(" ", ""))
                                    except:
                                        pass
                                        
                                if m_cnt >= 40:
                                    if any(pos in combined for pos in POSITIVE_SIGNALS) or any(pos in u.lower() for pos in ["kupon", "kod", "cek", "indirim", "firsat", "yemek", "migros", "turna", "bilet", "dijital"]):
                                        if u not in seen_usernames:
                                            seen_usernames.add(u)
                                            existing_verified.append({
                                                "username": u,
                                                "title": title,
                                                "members": m_cnt,
                                                "extra": extra,
                                                "description": desc.replace("\n", " ")[:200],
                                                "link": f"https://t.me/{u}"
                                            })
                                            print(f"[{len(existing_verified):03d}] 🎟️ BULUNDU: @{u:24s} | {title[:26]} | {m_cnt:5d} üye")
                except Exception:
                    pass
                    
        tasks = [verify_url(u) for u in candidates_to_check]
        await asyncio.gather(*tasks)

    # Sort descending by member count
    existing_verified.sort(key=lambda x: -x["members"])
    
    # Save the 100 validated groups
    output_100 = {
        "total_verified": len(existing_verified),
        "groups": existing_verified[:100]
    }
    
    with open("100_kesin_onayli_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output_100, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TOPLAM {len(existing_verified)} ADET KUPON & KOD GRUBU TAMAMLANDI!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(harvest_full_100())
