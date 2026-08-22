import asyncio
import aiohttp
from bs4 import BeautifulSoup
import sys
import re

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
                
                # Method 1: Regex on meta tag
                title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
                desc_match = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html)
                extra_match = re.search(r'<div\s+class="tgme_page_extra">([^<]*)</div>', html)
                
                title = title_match.group(1) if title_match else ""
                desc = desc_match.group(1) if desc_match else ""
                extra = extra_match.group(1).strip() if extra_match else ""
                
                print(f"@{u:20s} | Title: {title[:25]} | Extra: {extra}")

if __name__ == '__main__':
    asyncio.run(test_meta())
