import asyncio
import aiohttp
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

async def test_meta():
    candidates = [
        "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm", "Kuponcekm",
        "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in candidates:
            url = f"https://t.me/{u}"
            async with session.get(url, timeout=7) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                og_title = soup.find("meta", property="og:title")
                og_desc = soup.find("meta", property="og:description")
                extra_el = soup.find("div", class_="tgme_page_extra")
                
                title = og_title["content"] if og_title and "content" in og_title.attrs else ""
                desc = og_desc["content"] if og_desc and "content" in og_desc.attrs else ""
                extra = extra_el.text.strip() if extra_el else ""
                print(f"@{u:20s} | Title: {title[:25]} | Extra: {extra}")

if __name__ == '__main__':
    asyncio.run(test_meta())
