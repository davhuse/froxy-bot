import asyncio
import aiohttp

async def print_actual_html():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("https://t.me/kuponceksatis", timeout=7) as resp:
            text = await resp.text()
            for line in text.split("\n"):
                if "og:title" in line or "tgme_page_extra" in line or "og:description" in line:
                    print("Line:", line)

if __name__ == '__main__':
    asyncio.run(print_actual_html())
