import asyncio
import json
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

# Read session files
sessions = {}

def add_sess(label, filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            t = f.read().strip()
            if t.startswith("1") and len(t) > 300:
                sessions[label] = t

add_sess("Froxy (from froxy_session_output.txt)", "froxy_session_output.txt")
add_sess("KeyVadi (from keyvadi_session_output.txt)", "keyvadi_session_output.txt")
add_sess("KeyVadi 2 (from session_key_output.txt)", "session_key_output.txt")
add_sess("Search session (from search_session.txt)", "search_session.txt")
add_sess("LisansArena new (from session_lisansarena_new.txt)", "session_lisansarena_new.txt")

# Read pending login json if exists
for f in ["pending_login.json", "pending_login_27.json"]:
    if os.path.exists(f):
        try:
            d = json.load(open(f, 'r', encoding='utf-8'))
            for k, v in d.items():
                if isinstance(v, str) and v.startswith("1") and len(v) > 300:
                    sessions[f"{f}:{k}"] = v
        except Exception: pass

async def verify(label, s):
    client = TelegramClient(StringSession(s), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ {label} -> UNAUTHORIZED")
            return
        me = await client.get_me()
        print(f"✅ {label} -> Logged in as: {me.first_name} (@{me.username}) [Phone: +{me.phone}]")
    except Exception as e:
        print(f"❌ {label} -> Error: {e}")
    finally:
        await client.disconnect()

async def main():
    print(f"Testing {len(sessions)} sessions...")
    for l, s in sessions.items():
        await verify(l, s)

if __name__ == "__main__":
    asyncio.run(main())
