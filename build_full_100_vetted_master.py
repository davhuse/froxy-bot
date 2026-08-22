import asyncio
import aiohttp
import os
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

def load_all_known_candidates():
    all_candidates = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "master_known_blacklist.json", "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json", "ultimate_approved_groups.json",
        "food_code_gems_approved.json", "aktif_saf_kupon_kod_gruplari.json",
        "freshly_discovered_niche_groups.json", "nihai_saf_ticaret_pazarlari.json",
        "expanded_pure_trade_groups.json", "100_kesin_onayli_kupon_kod_gruplari.json"
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
                                all_candidates.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    all_candidates.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        all_candidates.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        all_candidates.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                all_candidates.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                            all_candidates.add(m.group(1).lower())
            except Exception:
                pass
    return sorted(list(all_candidates))

EXCLUDE_WORDS = [
    # Oyun hesapları
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "wolfteam", "growtopia", "standoff",
    # Trendyol Koleksiyon
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    # Kumar / Bahis
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    # İlgisiz
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining", "papara"
]

TRADE_SIGNALS = [
    "kupon", "kod", "çek", "cek", "indirim", "fırsat", "firsat", "kampanya",
    "yemeksepeti", "migros", "turna", "enuygun", "tıkla gelsin", "tiklagelsin",
    "getir", "hediye çeki", "hediye ceki", "kapak", "cips", "pepsi", "bilet",
    "tod", "gb", "internet", "daha daha", "kazandrio", "freebayt", "money",
    "satılık", "satıyorum", "alınır", "alıyorum", "hesap", "lisans", "ticaret",
    "pazar", "market", "borsa", "ilan", "yardımlaşma", "yardimlasma", "sohbet",
    "bot", "panel", "smm", "sms", "onay", "numara", "takas", "devir", "yazılım"
]

async def build_top_100():
    candidates = load_all_known_candidates()
    print(f"[*] Taranacak toplam benzersiz grup adayı: {len(candidates)}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    verified_results = []
    seen = set()
    
    connector = aiohttp.TCPConnector(limit=40)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        semaphore = asyncio.Semaphore(25)
        
        async def verify(u):
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
                                    if any(ts in combined for ts in TRADE_SIGNALS) or any(ts in u.lower() for ts in ["kupon", "kod", "cek", "indirim", "firsat", "yemek", "migros", "turna", "bilet", "dijital", "ticaret", "pazar", "hesap"]):
                                        seen.add(u)
                                        verified_results.append({
                                            "username": u,
                                            "title": title,
                                            "members": m_cnt,
                                            "extra": extra,
                                            "description": desc.replace("\n", " ")[:200],
                                            "link": f"https://t.me/{u}"
                                        })
                                        print(f"[{len(verified_results):03d}] 💎 ONAYLANDI: @{u:22s} | {title[:28]} | {m_cnt:5d} üye")
                except Exception:
                    pass
                    
        tasks = [verify(u) for u in candidates]
        await asyncio.gather(*tasks)

    # Sort descending by member count
    verified_results.sort(key=lambda x: -x["members"])
    
    top_100 = verified_results[:100]
    
    output = {
        "total_approved": len(top_100),
        "groups": top_100
    }
    
    with open("100_tam_test_edilmis_kupon_ve_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    # Also save as plain txt list for bot import
    with open("100_kupon_kod_gruplar_listesi.txt", "w", encoding="utf-8") as f:
        for g in top_100:
            f.write(f"@{g['username']}\n")
            
    print(f"\n=======================================================")
    print(f"✅ 100 ADET KUPON, KOD VE TİCARET GRUBU TEST EDİLDİ VE KAYDEDİLDİ!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(build_top_100())
