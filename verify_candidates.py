"""
Verify the 3 candidate groups by checking their actual content.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import GetFullChannelRequest

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open(r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\froxy_session_output.txt", "r") as f:
    SESSION_STRING = f.read().strip()

GROUPS_TO_CHECK = ["cepstokduyuru", "bonussaatisohbet", "kuponceksatisi"]

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    print("Connected!\n")

    for group_username in GROUPS_TO_CHECK:
        print(f"{'='*80}")
        print(f"CHECKING: @{group_username}")
        print(f"{'='*80}")
        
        try:
            entity = await client.get_entity(group_username)
            title = getattr(entity, 'title', '?')
            mega = getattr(entity, 'megagroup', False)
            bcast = getattr(entity, 'broadcast', False)
            members = getattr(entity, 'participants_count', None)
            
            print(f"  Title: {title}")
            print(f"  Megagroup: {mega}, Broadcast: {bcast}")
            print(f"  Members: {members}")
            
            # Get full info
            try:
                full = await client(GetFullChannelRequest(entity))
                about = getattr(full.full_chat, 'about', '') or ''
                print(f"  About: {about[:300]}")
                online = getattr(full.full_chat, 'online_count', None)
                print(f"  Online: {online}")
            except Exception as e:
                print(f"  Full info error: {e}")
            
            # Get recent messages
            print(f"\n  RECENT MESSAGES:")
            history = await client(GetHistoryRequest(
                peer=entity,
                limit=30,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            users = {u.id: u for u in history.users}
            
            unique_senders = set()
            for msg in history.messages:
                sender_uid = None
                if hasattr(msg, 'from_id') and msg.from_id:
                    if hasattr(msg.from_id, 'user_id'):
                        sender_uid = msg.from_id.user_id
                
                sender_uname = None
                sender_name = None
                if sender_uid and sender_uid in users:
                    u = users[sender_uid]
                    sender_uname = getattr(u, 'username', None) or ''
                    first = getattr(u, 'first_name', '') or ''
                    last = getattr(u, 'last_name', '') or ''
                    sender_name = f"{first} {last}".strip()
                    unique_senders.add(sender_uname or sender_name)
                
                text = getattr(msg, 'message', '') or ''
                date = getattr(msg, 'date', '')
                
                sender_display = f"@{sender_uname}" if sender_uname else (sender_name or str(sender_uid))
                print(f"    [{date}] {sender_display}: {text[:150]}")
            
            print(f"\n  Unique senders in last 30 msgs: {len(unique_senders)}")
            print(f"  Senders: {unique_senders}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print()
        await asyncio.sleep(2)
    
    await client.disconnect()

asyncio.run(main())
