import asyncio
import sys
from telethon import TelegramClient, functions
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
TARGET_GROUP = "turkcesohbetler"

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    print(f"Connecting to {TARGET_GROUP}...")
    try:
        entity = await client.get_entity(TARGET_GROUP)
        try:
            await client(functions.channels.JoinChannelRequest(channel=entity))
            print(f"✅ Gruba katılım sağlandı: {TARGET_GROUP}")
        except Exception as je:
            print(f"Katılım bilgisi: {je}")
            
        # Send greeting
        msg = await client.send_message(entity, "Selamlar herkese, iyi günler")
        print(f"✅ MESAJ GÖNDERİLDİ! Mesaj ID: {msg.id}")
    except Exception as e:
        print(f"❌ Gönderim hatası: {type(e).__name__}: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
