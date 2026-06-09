import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    if len(sys.argv) < 4:
        print("Usage: python generate_session_noninteractive.py <phone> <password> <code>")
        return
        
    phone = sys.argv[1]
    password = sys.argv[2]
    code = sys.argv[3]
    
    print(f"Connecting to Telegram for {phone}...")
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.start(
            phone=phone,
            password=password,
            code_callback=lambda: code
        )
        print("\n✅ LOGIN SUCCESS!")
        print("🔑 SIZIN STRINGSESSION ANAHTARINIZ:")
        print(client.session.save())
    except Exception as e:
        print(f"❌ Error during login: {type(e).__name__} - {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
