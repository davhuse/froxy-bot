import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
import re
import json

def get_master_blacklist():
    blacklist = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "known_groups_dump.json",
        "master_known_blacklist.json", "yeni_onayli_gruplar_raporu.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json"
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
                                blacklist.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    blacklist.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        blacklist.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        blacklist.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                blacklist.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            blacklist.add(m.group(1).lower())
            except Exception:
                pass
    return blacklist

BASE_WORDS = [
    "kupon", "indirim", "kod", "cek", "firsat", "yemeksepeti", "migros",
    "turna", "enuygun", "hediyeceki", "alisveris", "dijitalkod", "kapak", "promosyon"
]

MIDDLES = [
    "alsat", "alimsatim", "pazar", "pazari", "borsa", "borsasi", "market",
    "marketi", "depo", "deposu", "kulup", "kulubu", "vadisi", "diyari",
    "merkez", "merkezi", "dunyasi", "alemi", "paylasim", "yardimlasma", "ticaret"
]

SUFFIXES = [
    "", "tr", "turkiye", "official", "resmi", "grup", "grubu", "chat", "sohbet",
    "ilan", "ilanlar", "ilanlari", "1", "2", "vip"
]

CANDIDATES = set()
for b in BASE_WORDS:
    for m in MIDDLES:
        for s in SUFFIXES:
            c1 = f"{b}{m}{s}".lower()
            c2 = f"{b}_{m}_{s}".rstrip("_").lower()
            c3 = f"{b}_{m}".lower()
            CANDIDATES.add(c1)
            CANDIDATES.add(c2)
            CANDIDATES.add(c3)

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus"
]

async def scrape_candidates():
    blacklist = get_master_blacklist()
    filtered_candidates = [c for c in CANDIDATES if c not in blacklist and len(c) >= 5]
    print(f"[*] Taranacak aday sayısı: {len(filtered_candidates)}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    approved_groups = []
    
    connector = aiohttp.TCPConnector(limit=30)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(15)
        
        async def fetch(u):
            async with semaphore:
                url = f"https://t.me/{u}"
                try:
                    async with session.get(url, timeout=8) as resp:
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
                                
                            # Check if it is a group (has "members" or "online")
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
                                        
                                if m_cnt >= 50:
                                    approved_groups.append({
                                        "username": u,
                                        "title": title,
                                        "members": m_cnt,
                                        "extra": extra,
                                        "description": desc,
                                        "url": url
                                    })
                                    print(f"🔥 YENİ GRUP BULUNDU: @{u:24s} | {title} | {extra}")
                except Exception:
                    pass
                    
        tasks = [fetch(u) for u in filtered_candidates]
        await asyncio.gather(*tasks)
        
    approved_groups.sort(key=lambda x: x["members"], reverse=True)
    with open("derin_web_kesif_onayli.json", "w", encoding="utf-8") as f:
        json.dump(approved_groups, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Toplam Keşfedilen Yepyeni Kupon Grubu: {len(approved_groups)}")

if __name__ == '__main__':
    asyncio.run(scrape_candidates())
