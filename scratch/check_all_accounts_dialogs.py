import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def check_client(session_str, name):
    if not session_str:
        print(f"{name}: Session not configured")
        return
        
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"{name}: NOT AUTHORIZED!")
        return
        
    me = await client.get_me()
    print(f"\n======================================")
    print(f"{name} - Logged in as: {me.first_name} (@{me.username or 'NoUsername'})")
    print(f"======================================")
    
    dialogs = await client.get_dialogs()
    joined_groups = []
    for d in dialogs:
        if d.is_group or d.is_channel:
            username = getattr(d.entity, 'username', '') or ''
            try:
                title = d.name.encode('utf-8', errors='replace').decode('utf-8')
            except:
                title = "???"
            joined_groups.append((d.id, title, username))
            
    print(f"Total joined groups/channels: {len(joined_groups)}")
    for idx, (gid, title, username) in enumerate(joined_groups):
        print(f"  {idx+1}. [{gid}] {title} (@{username})")
        
    await client.disconnect()

async def main():
    if not os.path.exists("bot_config.json"):
        print("bot_config.json not found!")
        return
        
    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    s1 = cfg.get("ad_string_session", "")
    s2 = cfg.get("ad_string_session2", cfg.get("ad_string_session_2", ""))
    s3 = cfg.get("ad_string_session3", cfg.get("ad_string_session_3", ""))
    
    await check_client(s1, "Account #1 (KeyVadi)")
    await check_client(s2, "Account #2 (Froxy)")
    await check_client(s3, "Account #3 (LisansArena)")

if __name__ == "__main__":
    asyncio.run(main())
