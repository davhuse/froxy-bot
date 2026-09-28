import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("jarvis_session_string.txt", "r") as f:
    s = f.read().strip()

groups = ["kuponcekm", "kuponkodualsat", "kuponsatimalim", "letgoilanlari"]

async def main():
    c = TelegramClient(StringSession(s), API_ID, API_HASH)
    await c.connect()
    for g in groups:
        try:
            ent = await c.get_entity(g)
            title = getattr(ent, "title", "")
            mg = getattr(ent, "megagroup", False)
            bc = getattr(ent, "broadcast", False)
            banned = getattr(ent, "default_banned_rights", None)
            send_allowed = not (banned and banned.send_messages) if banned else True
            print(f"@{g:<18} | title='{title}' | megagroup={mg} | broadcast={bc} | send_messages={send_allowed}")
        except Exception as e:
            print(f"@{g:<18} | ERROR: {type(e).__name__}: {e}")
    await c.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
