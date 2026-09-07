import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    queries = ["kupon", "indirim", "yemeksepeti", "migros", "çek"]
    for q in queries:
        print(f"\n--- Search query: '{q}' ---")
        res = await client(SearchRequest(q=q, limit=20))
        print(f"Total chats returned: {len(res.chats)}")
        for c in res.chats:
            is_mg = isinstance(c, Channel) and c.megagroup
            is_ch = isinstance(c, Channel) and c.broadcast
            username = getattr(c, 'username', None)
            title = getattr(c, 'title', '')
            members = getattr(c, 'participants_count', 0)
            print(f"  Type={'SUPERGROUP' if is_mg else ('CHANNEL' if is_ch else 'CHAT')} | @{username} | Members: {members} | Title: {title}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
