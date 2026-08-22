"""Check cepstokduyuru group content"""
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

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    
    entity = await client.get_entity("cepstokduyuru")
    title = getattr(entity, 'title', '?')
    mega = getattr(entity, 'megagroup', False)
    bcast = getattr(entity, 'broadcast', False)
    members = getattr(entity, 'participants_count', None)
    
    print(f"Title: {title}")
    print(f"Megagroup: {mega}, Broadcast: {bcast}, Members: {members}")
    
    try:
        full = await client(GetFullChannelRequest(entity))
        about = getattr(full.full_chat, 'about', '') or ''
        print(f"About: {about[:500]}")
        print(f"Online: {getattr(full.full_chat, 'online_count', None)}")
    except Exception as e:
        print(f"Full info error: {e}")
    
    # Get last 40 messages
    history = await client(GetHistoryRequest(
        peer=entity, limit=40,
        offset_date=None, offset_id=0, max_id=0, min_id=0,
        add_offset=0, hash=0
    ))
    
    users = {u.id: u for u in history.users}
    
    print(f"\nRECENT {len(history.messages)} MESSAGES:")
    unique_senders = set()
    for msg in history.messages:
        sender_uid = None
        if hasattr(msg, 'from_id') and msg.from_id:
            if hasattr(msg.from_id, 'user_id'):
                sender_uid = msg.from_id.user_id
        
        sender_uname = ''
        sender_name = ''
        if sender_uid and sender_uid in users:
            u = users[sender_uid]
            sender_uname = getattr(u, 'username', '') or ''
            first = getattr(u, 'first_name', '') or ''
            last = getattr(u, 'last_name', '') or ''
            sender_name = f"{first} {last}".strip()
            unique_senders.add(sender_uname or sender_name)
        
        text = getattr(msg, 'message', '') or ''
        date = getattr(msg, 'date', '')
        sender_display = f"@{sender_uname}" if sender_uname else sender_name
        print(f"  [{date}] {sender_display}: {text[:200]}")
    
    print(f"\nUnique senders: {len(unique_senders)}: {unique_senders}")
    
    # Check if target traders are among senders
    target_unames = {'auradijital', 'cano31m', 'ventaru1234567890', 'ferhatbey47'}
    found_traders = set()
    for s in unique_senders:
        if s.lower() in target_unames:
            found_traders.add(s)
    print(f"Target traders in recent messages: {found_traders}")
    
    await client.disconnect()

asyncio.run(main())
