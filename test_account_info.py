import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print("✅ HESAP BAGLANTISI BASARILI:")
        print(f"  Ad: {me.first_name}")
        print(f"  Soyad: {me.last_name}")
        print(f"  Kullanici Adi: @{me.username}")
        print(f"  ID: {me.id}")
        print(f"  Telefon: +{me.phone}")
    else:
        print("❌ Hesap oturumu yetkili degil!")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
