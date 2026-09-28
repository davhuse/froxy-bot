import asyncio
import sys
import json
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    with open("gruplar.txt", "r", encoding="utf-8") as f:
        unames = [line.strip().replace("@", "") for line in f if line.strip()]
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    print(f"Toplam {len(unames)} adet ticaret grubu denetleniyor...\n")
    
    verified_ticaret = []
    
    for u in unames:
        try:
            entity = await client.get_entity(u)
            if getattr(entity, 'broadcast', False) and not getattr(entity, 'megagroup', False):
                continue
            if not getattr(entity, 'megagroup', False):
                continue
            banned = getattr(entity, 'default_banned_rights', None)
            if banned and banned.send_messages:
                continue
            title = getattr(entity, 'title', '')
            try:
                full = await client(GetFullChannelRequest(entity))
                members = full.full_chat.participants_count
            except Exception:
                members = getattr(entity, 'participants_count', 0) or 0
                
            print(f"  ✅ @{u:<24} | {members:<6} üye | {title}")
            verified_ticaret.append({
                "username": u,
                "title": title,
                "members": members
            })
        except Exception:
            pass
        await asyncio.sleep(0.2)
        
    await client.disconnect()
    
    print(f"\nToplam Onaylanan Ticaret Grubu: {len(verified_ticaret)}")
    with open("verified_ticaret_groups.json", "w", encoding="utf-8") as f:
        json.dump(verified_ticaret, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
