import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    with open('froxy_session_output.txt', 'r', encoding='utf-8') as f:
        s_str = f.read().strip()
    client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
    await client.connect()
    
    entity = await client.get_entity("gpt_nocard")
    print(f"Connected to @gpt_nocard")

    # Let's search participants for 'payshop' or letters
    print("Searching participants for 'payshop'...")
    payshop_users = await client.get_participants(entity, search='payshop')
    print(f"Found {len(payshop_users)} participants matching 'payshop' query.")
    for u in payshop_users:
        print(f"User: {u.first_name} (@{u.username}) ID: {u.id}")
        try:
            full = await client(GetFullUserRequest(u))
            print(f"Bio: {full.full_user.about}")
        except Exception as e:
            print(f"Bio error: {e}")

    print("\nSearching participants for 'netflix'...")
    nf_users = await client.get_participants(entity, search='netflix')
    print(f"Found {len(nf_users)} participants matching 'netflix' query.")
    for u in nf_users:
        print(f"User: {u.first_name} (@{u.username}) ID: {u.id}")
        try:
            full = await client(GetFullUserRequest(u))
            print(f"Bio: {full.full_user.about}")
        except Exception as e:
            print(f"Bio error: {e}")

    print("\nSearching participants for 'shop'...")
    shop_users = await client.get_participants(entity, search='shop')
    print(f"Found {len(shop_users)} participants matching 'shop' query.")
    for u in shop_users[:20]:
        print(f"User: {u.first_name} (@{u.username}) ID: {u.id}")
        try:
            full = await client(GetFullUserRequest(u))
            if full.full_user.about:
                print(f"Bio: {full.full_user.about}")
        except Exception as e:
            pass

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
