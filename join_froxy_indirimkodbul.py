import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    froxy_session = f.read().strip()

async def main():
    client = TelegramClient(StringSession(froxy_session), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Froxy auth failed!")
        return

    target = "indirimkodbul"
    print(f"Joining @{target} with Froxy...")
    try:
        entity = await client.get_entity(target)
        await client(JoinChannelRequest(entity))
        print(f"✅ Froxy successfully joined @{target} ({entity.title})!")
    except Exception as e:
        print(f"❌ Error joining @{target}: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
