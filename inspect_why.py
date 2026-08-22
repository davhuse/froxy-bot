import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

async def inspect_why():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    test_queries = [
        "yemeksepeti", "migros sanal market", "tabii kod", "gratis kupon",
        "koddeposu", "kodvadisi", "koddiyari", "kodmerkezi", "indirimmerkezi", "firsatmerkezi"
    ]
    
    for q in test_queries:
        res = await client(SearchRequest(q=q, limit=20))
        for chat in res.chats:
            u = getattr(chat, 'username', '')
            if not u:
                continue
            is_broad = getattr(chat, 'broadcast', False)
            is_mega = getattr(chat, 'megagroup', False)
            title = getattr(chat, 'title', '')
            print(f"Chat: @{u:24s} | Title: {title[:25]} | Broadcast: {is_broad} | Megagroup: {is_mega}")
            
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(inspect_why())
