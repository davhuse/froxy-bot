import asyncio
import sys
import json
from telethon import TelegramClient, functions
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

QUERIES = ["sohbet", "muhabbet", "kripto", "yazilim"]

BAD_WORDS = ["sikil", "sex", "escort", "kumar", "bahis", "porn", "sabaha kadar", "ifsa", "gay", "+18", "vip", "binomo"]

async def check_chat(client, chat, q, seen, found):
    uname = getattr(chat, 'username', None)
    if not uname or uname in seen:
        return
    seen.add(uname)
    
    # Must be a megagroup
    if getattr(chat, 'broadcast', False) and not getattr(chat, 'megagroup', False):
        return
    if not getattr(chat, 'megagroup', False):
        return
        
    banned = getattr(chat, 'default_banned_rights', None)
    if banned and banned.send_messages:
        return
        
    title = getattr(chat, 'title', '')
    if any(bw in title.lower() for bw in BAD_WORDS) or any(bw in uname.lower() for bw in BAD_WORDS):
        return
        
    try:
        full = await asyncio.wait_for(client(GetFullChannelRequest(chat)), timeout=4.0)
        members = full.full_chat.participants_count
    except Exception:
        members = getattr(chat, 'participants_count', 0) or 0
        
    if members < 200:
        return
        
    print(f"[{q}] 🌟 @{uname:<22} | {members:<6} üye | {title}")
    found.append({
        "category": q,
        "username": uname,
        "title": title,
        "members": members
    })

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    found = []
    seen = set()
    
    for q in QUERIES:
        print(f"\n=== ARAMA: '{q}' ===")
        try:
            res = await asyncio.wait_for(client(functions.contacts.SearchRequest(q=q, limit=15)), timeout=8.0)
            for chat in res.chats:
                try:
                    await check_chat(client, chat, q, seen, found)
                except Exception:
                    pass
        except Exception as e:
            print(f"Hata ({q}): {e}")
        await asyncio.sleep(1)
            
    await client.disconnect()
    
    with open("discovered_clean_groups.json", "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Toplam bulunan onaylı kaliteli grup: {len(found)}")

if __name__ == "__main__":
    asyncio.run(main())
