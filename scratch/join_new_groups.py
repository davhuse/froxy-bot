import sys
import os
import json
import asyncio
import ssl
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

# Load config
CONFIG_FILE = "bot_config.json"
if not os.path.exists(CONFIG_FILE):
    print("Error: bot_config.json not found")
    sys.exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
    config = json.load(f)

# API credentials
API_ID = 26543169
API_HASH = "8d1b11f0a20a48b5ab21356f9f25712f"

sessions = {
    "Hesap 2": config.get("ad_string_session2", ""),
    "Hesap 3": config.get("ad_string_session3", "")
}

usernames = [
    "Nightsatis",
    "ticaretguvenilir",
    "ceksatkupon",
    "kuponsatimalim",
    "alcaponesat",
    "KuponindirimPazari",
    "kuponceking",
    "TicaretGrubuuu",
    "kuponindirimsatis"
]

async def join_groups_for_account(acc_name, session_str):
    if not session_str:
        print(f"\n[{acc_name}] No session string found.")
        return
        
    print(f"\n[{acc_name}] Connecting to account...")
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print(f"[{acc_name}] Failed to authorize session.")
        await client.disconnect()
        return
        
    me = await client.get_me()
    print(f"[{acc_name}] Authorized as @{me.username or 'NoUsername'} (ID: {me.id})")
    
    for username in usernames:
        clean_user = username.strip().replace("@", "")
        print(f"[{acc_name}] Trying to join @{clean_user}...")
        try:
            # Clean username and join
            await client(JoinChannelRequest(clean_user))
            print(f"  [SUCCESS] Joined @{clean_user}")
        except FloodWaitError as e:
            print(f"  [FLOOD] Wait {e.seconds} seconds required.")
            print("  Skipping remaining groups for this account to avoid further flood.")
            break
        except Exception as e:
            print(f"  [FAILED] Error joining @{clean_user}: {e}")
        await asyncio.sleep(2)
        
    await client.disconnect()

async def main():
    for name, s_str in sessions.items():
        try:
            await join_groups_for_account(name, s_str)
        except Exception as e:
            print(f"Error executing for {name}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
