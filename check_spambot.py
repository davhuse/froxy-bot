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
    
    print("Checking @SpamBot...")
    try:
        async with client.conversation("@SpamBot") as conv:
            await conv.send_message("/start")
            resp = await conv.get_response(timeout=5)
            print("SpamBot Yanıtı:")
            print(resp.raw_text)
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
