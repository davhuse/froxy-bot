import asyncio
import urllib.request
import ssl
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.sessions import StringSession
import telethon.errors
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

async def main():
    # Only test the URL fetching to see if we can get the code without rate limiting
    url = 'https://jiema.didiapi.uk/getcode?id=f505373d-5219-4a60-bcea-96f473fe72f4'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            html = r.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            print(soup.get_text().strip())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
