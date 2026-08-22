import asyncio
import aiohttp
import os
import re
import html as html_parser
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

# 120+ targeted Turkish coupon, voucher, promo code, food, and digital trade group candidates
TARGET_CANDIDATES = [
    # Ana Kupon & Çek & Kod Alım-Satım Grupları
    "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm",
    "kuponsatisgrup", "kuponsatimalim", "ceksatkupon", "Kuponcekm",
    "alimsatimmerkezii", "darktradehouse", "ticaretZ", "KodKuponMerkezi",
    "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis",
    "herkesibeklerimm", "kuponkodindirimilanlar", "bedavainternetkod",
    "alisverisforumuguncel", "kodkuponmarketi", "kuponsatislari0",
    "indirimkodusatis", "ticaretyapn", "ceksat", "kuponkodceksatis",
    "kuponkodhesapilan", "kuponindirimcek", "xAlimSatiim", "wishx_2",
    "satiskodtakasi", "kuponalsatgurup", "ceksatkupon2", "zeroticaret",
    "indirimkana", "indirim363", "kodmalf", "cek_kupon_kod_ilan",
    "kuponindirimkodalisveris", "kodalimsatim", "kodindirimsatis",
    "kuponkodalimsatim", "kuponhesap", "kuponkodalsat", "KuponindirimPazari",
    "ceksatistakasgrup", "kinseimedyaticaret", "kcksohbet", "dijitalticaretgrubu",
    "ketenpereticaret", "bedavainternetkralligigrubu", "kazandriiro",
    "kazandriokapakkodlari", "kodceksatismerkezi", "kodcek", "kuponceksatisi",
    "kuponkodualsat", "kuponkodmerkez", "kuponyaticaret", "kuponvekodsatisgrubu",
    "mukyemek", "uygunkod", "yucekuponsatis", "yemeksepeti_kupon_indirim",
    "trendyolkampanya5", "indirimruzgari1", "bedavainternetkodalimsatim",
    "bedavainternetyapilir", "baronalsatticaret", "dijitalilan",
    "eticaretlab", "gmailalimsatimg", "hepkazanhepkazan", "ilanticaret",
    "indirimdeal", "indirimcin", "indirimhep", "kupongrupta",
    "mailalimsatimticaret", "megapaylasimlar", "sterkpremium", "texasconfigchat",
    "ticaretcanavari", "ticar4t", "ticaretgrubuuu", "ticaretguvenilir",
    "ticaretvarburada", "tsmticaret", "ittingalimsatim", "pixerdo",
    "reklamreferans", "refkasaxmxma", "sanalalimsatimticaret", "sanalposticaret",
    "shopifyuzmani", "kod_promosyon", "kazandrio", "yemek_kuponu",
    "dahadaha", "pepsikod", "cipskod", "frebaytgb", "freebayt", "turnabilet",
    "enuygunbilet", "todtvkod", "ssportkod", "biletinialkod", "alisverisceki"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "iddaa", "bahis", "casino", "slot", "rulet", "bet",
    "gayrimenkul", "emlak", "oto alım", "araba alım", "mining", "papara"
]

async def compile_100():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    verified_groups = []
    seen = set()
    
    connector = aiohttp.TCPConnector(limit=30)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(15)
        
        async def check(u):
            u_clean = u.lower().lstrip("@")
            if u_clean in seen:
                return
            async with semaphore:
                url = f"https://t.me/{u_clean}"
                try:
                    async with session.get(url, timeout=7) as resp:
                        if resp.status == 200:
                            raw_html = await resp.text()
                            
                            title_match = re.search(r'property="og:title"\s+content="([^"]*)"', raw_html, re.IGNORECASE)
                            desc_match = re.search(r'property="og:description"\s+content="([^"]*)"', raw_html, re.IGNORECASE)
                            extra_match = re.search(r'class="tgme_page_extra">([^<]*)<', raw_html, re.IGNORECASE)
                            
                            title = html_parser.unescape(title_match.group(1)) if title_match else ""
                            desc = html_parser.unescape(desc_match.group(1)) if desc_match else ""
                            extra = extra_match.group(1).strip() if extra_match else ""
                            
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
                                    seen.add(u_clean)
                                    verified_groups.append({
                                        "username": u_clean,
                                        "title": title,
                                        "members": m_cnt,
                                        "extra": extra,
                                        "description": desc.replace("\n", " ")[:200],
                                        "link": f"https://t.me/{u_clean}"
                                    })
                                    print(f"[{len(verified_groups):03d}] 🎟️ DOĞRULANDI: @{u_clean:22s} | {title[:28]} | {m_cnt:5d} üye")
                except Exception:
                    pass
                    
        tasks = [check(u) for u in TARGET_CANDIDATES]
        await asyncio.gather(*tasks)

    # Sort descending by member count
    verified_groups.sort(key=lambda x: -x["members"])
    
    # Save output
    output = {
        "total_approved": len(verified_groups),
        "groups": verified_groups
    }
    
    with open("100_tam_test_edilmis_kupon_ve_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    with open("100_kupon_kod_gruplar_listesi.txt", "w", encoding="utf-8") as f:
        for g in verified_groups:
            f.write(f"@{g['username']}\n")
            
    print(f"\n=======================================================")
    print(f"✅ TOPLAM {len(verified_groups)} ADET AKTİF KUPON & KOD GRUBU BAŞARIYLA DOĞRULANDI VE KAYDEDİLDİ!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(compile_100())
