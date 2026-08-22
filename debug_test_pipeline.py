import asyncio
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

TEST_SAMPLES = ["kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm", "Kuponcekm"]

async def debug_test():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    for u in TEST_SAMPLES:
        try:
            print(f"\n--- Testing @{u} ---")
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            print(f"Entity retrieved: {type(entity)}")
            print(f"Megagroup: {getattr(entity, 'megagroup', False)}, Broadcast: {getattr(entity, 'broadcast', False)}")
            print(f"Participants: {getattr(full.full_chat, 'participants_count', 0)}")
            
            banned = getattr(full.full_chat, 'default_banned_rights', None)
            print(f"Banned rights: {banned}")
            
            msgs = await client.get_messages(entity, limit=20)
            print(f"Messages count: {len(msgs)}")
            if msgs:
                print(f"Latest msg date: {msgs[0].date}")
                now = datetime.now(timezone.utc)
                age = (now - msgs[0].date).total_seconds() / 3600.0
                print(f"Age in hours: {age}")
        except Exception as e:
            print(f"Error on @{u}: {e}")
            
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(debug_test())
