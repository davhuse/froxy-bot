import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
PHONE = "+13255674614"

async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    print(f"Sending code to {PHONE}...")
    try:
        sent = await client.send_code_request(PHONE)
        state = {
            "session_str": client.session.save(),
            "phone_code_hash": sent.phone_code_hash,
            "phone": PHONE,
            "password": "habil2121"
        }
        with open("temp_jarvis_auth.json", "w", encoding="utf-8") as f:
            json.dump(state, f)
            
        print("✅ KOD BAŞARIYLA GÖNDERİLDİ! Telegram uygulamasına gelen kodu bekliyoruz.")
    except Exception as e:
        print(f"❌ Kod gönderme hatası: {type(e).__name__}: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
