import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for item in ["Dolandiricikontrol", 1882280700, -1001882280700]:
        try:
            ent = await client.get_entity(item)
            is_mega = isinstance(ent, Channel) and ent.megagroup
            banned = ent.default_banned_rights if isinstance(ent, Channel) else None
            can_send = not (banned and banned.send_messages) if is_mega else False
            print(f"Entity: {item} -> Title: {ent.title} | Username: @{ent.username} | Mega: {is_mega} | Write: {can_send}")
        except Exception as e:
            print(f"Entity: {item} -> Error: {e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
