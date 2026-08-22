import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

TEST_GROUPS = [
    "kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm",
    "kuponsatisgrup", "kuponsatimalim", "ceksatkupon", "Kuponcekm",
    "alimsatimmerkezii", "darktradehouse", "ticaretZ", "KodKuponMerkezi",
    "kodpazari", "YemekSepetiKuponu", "ceksatp8", "Minakuponkodsatis"
]

async def test_preview():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in TEST_GROUPS:
            url = f"https://t.me/s/{u}"
            async with session.get(url, timeout=10) as resp:
                print(f"@{u:20s} -> Status: {resp.status} (Final URL: {resp.url})")
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    title_el = soup.find("div", class_="tgme_channel_info_header_title")
                    count_el = soup.find("div", class_="tgme_channel_info_counter")
                    msgs = soup.find_all("div", class_="tgme_widget_message_text")
                    print(f"   Title: {title_el.text.strip() if title_el else 'None'}")
                    print(f"   Counter: {count_el.text.strip() if count_el else 'None'}")
                    print(f"   Messages loaded: {len(msgs)}")
                    if msgs:
                        print(f"   Sample: {msgs[-1].text.strip()[:60]}...")

if __name__ == '__main__':
    asyncio.run(test_preview())
