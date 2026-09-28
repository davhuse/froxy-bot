import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    dialogs = await client.get_dialogs()
    print(f"Toplam diyalog sayısı: {len(dialogs)}")
    
    for d in dialogs:
        if d.is_group or d.is_channel:
            uname = getattr(d.entity, 'username', 'Yok')
            print(f"  • {d.name} (@{uname}) | ID: {d.id}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
