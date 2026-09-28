import asyncio
import sys
from telethon import TelegramClient, functions
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
TARGET = "universite_sohbet"

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    print(f"Connecting to @{TARGET}...")
    try:
        entity = await client.get_entity(TARGET)
        try:
            await client(functions.channels.JoinChannelRequest(channel=entity))
            print(f"✅ Gruba katılım sağlandı: @{TARGET}")
        except Exception as je:
            print(f"Katılım: {je}")
            
        msg = await client.send_message(entity, "Selamlar herkese, iyi çalışmalar")
        print(f"✅ MESAJ BAŞARIYLA GÖNDERİLDİ! Mesaj ID: {msg.id}")
    except Exception as e:
        print(f"❌ Gönderim hatası: {type(e).__name__}: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
