import asyncio
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 26772719
api_hash = "f11aab22ed30e1dfd49ba8e5470d0da8"

async def check_session(name, session_string):
    print(f"\nChecking {name}...")
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"{name} is NOT authorized.")
            return

        me = await client.get_me()
        print(f"{name} logged in as: {me.first_name} (+{me.phone})")

        # Get last message from 777000
        async for message in client.iter_messages(777000, limit=3):
            print(f"[{message.date}] {message.text}")

        await client.disconnect()
    except Exception as e:
        print(f"Error checking {name}: {e}")

async def main():
    with open("bot_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    s2 = config.get("ad_string_session2", "")
    s3 = config.get("ad_string_session3", "")
    
    if s2:
        await check_session("Account 2", s2)
    if s3:
        await check_session("Account 3", s3)

if __name__ == "__main__":
    asyncio.run(main())
