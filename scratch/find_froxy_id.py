import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 26772719
api_hash = "f11aab22ed30e1dfd49ba8e5470d0da8"
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    with open("bot_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    s2 = config.get("ad_string_session2", "")
    if not s2: return

    client = TelegramClient(StringSession(s2), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not authorized")
        return

    print("Searching for 'froxy' in recent dialogs...")
    async for dialog in client.iter_dialogs(limit=50):
        if dialog.is_user:
            user = dialog.entity
            fname = getattr(user, 'first_name', '') or ''
            uname = getattr(user, 'username', '') or ''
            if 'froxy' in fname.lower() or 'froxy' in uname.lower():
                print(f"Found user: {fname} (@{uname}) [ID: {user.id}]")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
