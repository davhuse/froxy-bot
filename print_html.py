import asyncio
import aiohttp

async def print_html():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("https://t.me/kuponceksatis", timeout=7) as resp:
            text = await resp.text()
            print("Status:", resp.status)
            print("Len:", len(text))
            print("Snippet:", text[:1000])

if __name__ == '__main__':
    asyncio.run(print_html())
