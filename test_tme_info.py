import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json

TEST_GROUPS = [
    "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm",
    "kuponsatisgrup", "kuponsatimalim", "ceksatkupon", "Kuponcekm",
    "alimsatimmerkezii", "darktradehouse", "ticaretZ", "KodKuponMerkezi",
    "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis"
]

async def test_tme():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in TEST_GROUPS:
            url = f"https://t.me/{u}"
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
                    print(f"@{u:20s} | Title: {title[:25]} | Extra: {extra}")

if __name__ == '__main__':
    asyncio.run(test_tme())
