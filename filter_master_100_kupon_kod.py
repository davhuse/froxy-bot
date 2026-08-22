import asyncio
import aiohttp
import os
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

def collect_all_real_database_groups():
    raw_dict = {}
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "yep_yeni_kupon_gruplari_kesif.json", "nihai_saf_ticaret_pazarlari.json",
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
                                raw_dict[item.lower().lstrip("@")] = item
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    raw_dict[u.lower().lstrip("@")] = item
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        raw_dict[item["username"].lower().lstrip("@")] = item
                                    elif isinstance(item, str):
                                        raw_dict[item.lower().lstrip("@")] = item
                            elif isinstance(k, str) and len(k) < 35:
                                raw_dict[k.lower().lstrip("@")] = v
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            u = m.group(1).lower()
                            if u not in raw_dict:
                                raw_dict[u] = u
            except Exception:
                pass
    return raw_dict

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining"
]

COUPON_WORDS = [
    "kupon", "kod", "çek", "cek", "indirim", "fırsat", "kampanya",
    "yemeksepeti", "migros", "turna", "enuygun", "tıkla gelsin", "tiklagelsin",
    "getir", "hediye çeki", "hediye ceki", "kapak", "cips", "pepsi", "bilet",
    "tod", "gb", "internet", "daha daha", "kazandrio", "freebayt", "money",
    "satılık", "satıyorum", "alınır", "alıyorum", "hesap", "lisans", "ticaret", "pazar"
]

async def verify_all():
    raw_groups = collect_all_real_database_groups()
    print(f"[*] İncelenecek toplam gerçek grup sayısı: {len(raw_groups)}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    verified_list = []
    seen = set()
    
    connector = aiohttp.TCPConnector(limit=35)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(20)
        
        async def check(u):
            if u in seen or len(u) < 4:
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
                                    if any(cw in combined for cw in COUPON_WORDS) or any(cw in u.lower() for cw in ["kupon", "kod", "cek", "indirim", "firsat", "yemek", "migros", "turna", "bilet", "dijital"]):
                                        seen.add(u)
                                        verified_list.append({
                                            "username": u,
                                            "title": title,
                                            "members": m_cnt,
                                            "extra": extra,
                                            "description": desc.replace("\n", " ")[:200],
                                            "link": f"https://t.me/{u}"
                                        })
                except Exception:
                    pass
                    
        tasks = [check(u) for u in raw_groups.keys()]
        await asyncio.gather(*tasks)

    verified_list.sort(key=lambda x: -x["members"])
    
    with open("100_tam_dogrulanmis_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_verified": len(verified_list),
            "groups": verified_list[:100]
        }, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Toplam Doğrulanan ve Test Edilen Kupon & Kod Grubu: {len(verified_list)}")

if __name__ == '__main__':
    asyncio.run(verify_all())
