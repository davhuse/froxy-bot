import sys
import os
import json
import asyncio
import ssl

sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession

CONFIG_FILE = "bot_config.json"
with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
    config = json.load(f)

API_ID = 26543169
API_HASH = "8d1b11f0a20a48b5ab21356f9f25712f"

sessions = {
    "Hesap 2": config.get("ad_string_session2", ""),
    "Hesap 3": config.get("ad_string_session3", "")
}

target_usernames = [
    "Nightsatis", "ticaretguvenilir", "ceksatkupon", "kuponsatimalim", 
    "alcaponesat", "KuponindirimPazari", "kuponceking", "TicaretGrubuuu", "kuponindirimsatis"
]

async def check_dialogs(acc_name, session_str):
    if not session_str:
        return
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return
        
    print(f"\n=== {acc_name} joined channels ===")
    dialogs = await client.get_dialogs()
    joined = []
    for d in dialogs:
        if d.is_channel or d.is_group:
            entity = d.entity
            if entity.username:
                joined.append(entity.username.lower())
                
    for username in target_usernames:
        clean = username.lower().strip()
        is_member = clean in joined
        print(f"@{username}: {'✅ Joined' if is_member else '❌ Not joined'}")
        
    await client.disconnect()

async def main():
    for name, s_str in sessions.items():
        await check_dialogs(name, s_str)

if __name__ == "__main__":
    asyncio.run(main())
