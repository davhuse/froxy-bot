import asyncio
import json
import os
from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    if not os.path.exists("bot_config.json"):
        print("bot_config.json not found")
        return
        
    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    sessions = [
        ("Hesap #1", cfg.get("ad_string_session")),
        ("Hesap #2", cfg.get("ad_string_session_2")),
        ("Hesap #3", cfg.get("ad_string_session_3")),
    ]
    
    print("=" * 80)
    print("TELEGRAM ACCOUNT DETAILS:")
    print("=" * 80)
    
    for name, s_str in sessions:
        if not s_str:
            print(f"{name}: No session string found.")
            continue
            
        # Create a temporary client in memory
        from telethon.sessions import StringSession
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"{name} -> ID: {me.id} | Name: {me.first_name} {me.last_name or ''} | Username: @{me.username or 'None'}")
            else:
                print(f"{name} -> NOT AUTHORIZED")
            await client.disconnect()
        except Exception as e:
            print(f"{name} -> Error: {e}")
            
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
