import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import os

def get_blacklist():
    bl = set()
    for fn in ["gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "master_known_blacklist.json"]:
        if os.path.exists(fn):
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                        bl.add(m.group(1).lower())
    return bl

async def search_duckduckgo():
    blacklist = get_blacklist()
    queries = [
        'site:t.me "kupon alım satım"',
        'site:t.me "çek alım satım"',
        'site:t.me "yemeksepeti indirim kuponu"',
        'site:t.me "migros hediye çeki"',
        'site:t.me "turna uçak bileti kodu"',
        'site:t.me "tıkla gelsin indirim"',
        'site:t.me "bedava internet kod alım satım"',
        'site:t.me "daha daha kod alım"',
        'site:t.me "kazandrio kapak kodu alım"',
        'site:t.me "hediye çeki alım satım"'
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    found_usernames = set()
    async with aiohttp.ClientSession(headers=headers) as session:
        for q in queries:
            url = f"https://html.duckduckgo.com/html/?q={aiohttp.helpers.quote(q)}"
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        for m in re.finditer(r"t\.me/(?:joinchat/)?([a-zA-Z0-9_]{4,32})", html):
                            u = m.group(1).lower()
                            if u not in blacklist and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                                found_usernames.add(u)
            except Exception:
                pass
            await asyncio.sleep(1.0)
            
    print(f"Web arama sonucu bulunan tekil username sayısı: {len(found_usernames)}")
    
    # Check each username on t.me
    approved = []
    for u in found_usernames:
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
                    
                    if "members" in extra.lower() or "üye" in extra.lower() or "online" in extra.lower():
                        num_m = re.search(r"([\d\s]+)\s*(?:members|üye)", extra.replace("\xa0", " "))
                        m_cnt = int(num_m.group(1).replace(" ", "")) if num_m else 0
                        if m_cnt >= 40:
                            approved.append({
                                "username": u,
                                "title": title,
                                "members": m_cnt,
                                "extra": extra,
                                "description": desc,
                                "url": url
                            })
                            print(f"🎯 ONAYLANDI: @{u:22s} | {title} | {extra}")
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
    with open("web_engine_found_groups.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    asyncio.run(search_duckduckgo())
