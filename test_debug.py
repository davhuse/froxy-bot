import asyncio
import aiohttp
import os
import re
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

async def test_debug():
    candidates = ["kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm", "Kuponcekm"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in candidates:
            url = f"https://t.me/{u}"
            async with session.get(url, timeout=7) as resp:
                print(f"URL: {url} -> status: {resp.status}")
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                title_el = soup.find("div", class_="tgme_page_title")
                extra_el = soup.find("div", class_="tgme_page_extra")
                desc_el = soup.find("div", class_="tgme_page_description")
                title = title_el.text.strip() if title_el else ""
                extra = extra_el.text.strip() if extra_el else ""
                desc = desc_el.text.strip() if desc_el else ""
                print(f"Title: {title} | Extra: {extra}")

if __name__ == '__main__':
    asyncio.run(test_debug())
