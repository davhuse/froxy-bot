import asyncio
import aiohttp
import os
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# 1. Collect all candidates discovered across all files, searches, and sources
def get_all_raw_candidates():
    candidates = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "known_groups_dump.json",
        "master_known_blacklist.json", "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "freshly_discovered_niche_groups.json", "nihai_saf_ticaret_pazarlari.json",
        "expanded_pure_trade_groups.json"
    ]
    for fn in files:
        if not os.path.exists(fn):
            continue
        if fn.endswith(".json"):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        for item in d:
                            if isinstance(item, str):
                                candidates.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    candidates.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        candidates.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        candidates.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                candidates.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            candidates.add(m.group(1).lower())
            except Exception:
                pass
                
    # Also add combinatorial patterns of coupon/code groups
    prefixes = ["kupon", "kod", "cek", "indirim", "firsat", "yemeksepeti", "migros", "turna", "enuygun", "dijital"]
    middles = ["sat", "alsat", "alimsatim", "pazar", "pazari", "borsa", "borsasi", "market", "marketi", "merkez", "merkezi", "depo", "deposu", "kulup", "kulubu", "vadisi", "diyari", "ilan", "ilanlari", "paylasim", "yardimlasma", "ticaret"]
    suffixes = ["", "tr", "turkiye", "official", "resmi", "grup", "grubu", "chat", "1", "2", "vip"]
    
    for p in prefixes:
        for m in middles:
            for s in suffixes:
                candidates.add(f"{p}{m}{s}".lower())
                candidates.add(f"{p}_{m}_{s}".rstrip("_").lower())
                
    return sorted(list(candidates))

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining"
]

POSITIVE_SIGNALS = [
    "kupon", "kod", "çek", "cek", "indirim", "fırsat", "firsat", "kampanya",
    "yemeksepeti", "migros", "turna", "enuygun", "tıkla gelsin", "tiklagelsin",
    "getir", "hediye çeki", "hediye ceki", "kapak", "cips", "pepsi", "bilet",
    "tod", "gb", "internet", "daha daha", "kazandrio", "freebayt", "money",
    "satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "hesap",
    "lisans", "ticaret", "pazar", "market", "borsa", "ilan", "yardımlaşma"
]

async def test_and_compile_100():
    candidates = get_all_raw_candidates()
    print(f"[*] Toplam taranacak ham aday havuzu: {len(candidates)} adet")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    vetted_groups = []
    seen_usernames = set()
    
    connector = aiohttp.TCPConnector(limit=35)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(15)
        
        async def verify_candidate(u):
            if u in seen_usernames or len(u) < 4:
                return
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
                            
                            # Exclude gaming, betting, trendyol collection spam
                            if any(ew in combined for ew in EXCLUDE_WORDS):
                                return
                                
                            # Check if it is an active group (has "members" / "online")
                            is_group = "members" in extra.lower() or "online" in extra.lower() or "üye" in extra.lower()
                            if is_group:
                                # Extract member count
                                m_cnt = 0
                                num_match = re.search(r"([\d\s]+)\s*(?:members|üye)", extra.replace("\xa0", " "))
                                if num_match:
                                    try:
                                        m_cnt = int(num_match.group(1).replace(" ", ""))
                                    except:
                                        pass
                                        
                                if m_cnt >= 40:
                                    # Must match coupon/code/food/trade signals
                                    if any(pos in combined for pos in POSITIVE_SIGNALS) or any(pos in u.lower() for pos in ["kupon", "kod", "cek", "indirim", "firsat", "yemek", "migros", "turna", "bilet", "dijital"]):
                                        seen_usernames.add(u)
                                        rec = {
                                            "username": u,
                                            "title": title,
                                            "members": m_cnt,
                                            "extra": extra,
                                            "description": desc.replace("\n", " ")[:200],
                                            "link": f"https://t.me/{u}"
                                        }
                                        vetted_groups.append(rec)
                                        print(f"[{len(vetted_groups):03d}] 🎟️ ONAYLANDI: @{u:22s} | {title[:28]} | {m_cnt:5d} üye")
                except Exception:
                    pass
                    
        tasks = [verify_candidate(u) for u in candidates]
        await asyncio.gather(*tasks)

    # Sort by member count descending
    vetted_groups.sort(key=lambda x: -x["members"])
    
    # Save the 100+ vetted groups
    output = {
        "total_approved": len(vetted_groups),
        "groups": vetted_groups[:100]
    }
    
    with open("100_onayli_test_edilmis_kupon_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ 100 ADET KUPON & KOD GRUBU BAŞARIYLA DOĞRULANDI VE KAYDEDİLDİ!")
    print(f"Toplam Onaylanan: {len(vetted_groups)} grup")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(test_and_compile_100())
