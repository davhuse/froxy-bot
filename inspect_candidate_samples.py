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

targets = [
    "dijitalticaretgrubu",
    "kazandrio",
    "kazandriokodalimsatimgrubu",
    "megapaylasimlar",
    "netflixblutvandb",
    "kuponhesap"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for uname in targets:
        print(f"\n{'='*20} @{uname} {'='*20}")
        try:
            ent = await client.get_entity(uname)
            banned = ent.default_banned_rights
            can_send = not (banned and banned.send_messages)
            print(f"Başlık: {ent.title} | Üye: {getattr(ent, 'participants_count', 0)} | Yazma: {can_send}")
            msgs = await client.get_messages(ent, limit=5)
            for m in msgs:
                if m.raw_text:
                    print(f"  - {m.raw_text.replace(chr(10), ' ')[:90]}")
        except Exception as e:
            print(f"  Hata: {e}")
        await asyncio.sleep(0.5)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
