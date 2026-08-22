import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json

TARGETS = [
    "KodDeposuCom", "KodDeposu", "KodVadisi", "koddiyari", "Kodmerkezichat",
    "indirimmerkezininyeri", "indirimmerkezim", "firsatmerkezigrup", "kuponindirimfirsatlari",
    "kuponcu_tr", "yemeksepeti_indirimleri", "yemek_kuponu", "migros_indirim_kodlari",
    "turna_ucak_bileti", "enuygun_bilet_kupon", "tod_tv_kupon", "daha_daha_kodlari",
    "kazandrio_kapak_kod", "hediye_ceki_pazari", "dijital_kod_pazari", "kampanya_vadisi"
]

async def scrape_web():
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in TARGETS:
            url = f"https://t.me/{u}"
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        title_el = soup.find("div", class_="tgme_page_title")
                        extra_el = soup.find("div", class_="tgme_page_extra")
                        desc_el = soup.find("div", class_="tgme_page_description")
                        
                        title = title_el.text.strip() if title_el else ""
                        extra = extra_el.text.strip() if extra_el else ""
                        desc = desc_el.text.strip() if desc_el else ""
                        
                        if "members" in extra.lower() or "subscribers" in extra.lower() or "üye" in extra.lower():
                            results.append({
                                "username": u,
                                "title": title,
                                "extra": extra,
                                "description": desc,
                                "url": url
                            })
                            print(f"✅ Bulundu: @{u:24s} | {title} | {extra}")
            except Exception as e:
                pass
            await asyncio.sleep(0.5)
            
    with open("web_scraped_candidates.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    asyncio.run(scrape_web())
