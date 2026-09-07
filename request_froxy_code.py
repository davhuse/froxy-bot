import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
PHONE = "+905015291021"

async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    print(f"Sending code to {PHONE}...")
    sent = await client.send_code_request(PHONE)
    
    # Save session state so we can complete login in the next step
    state = {
        "session_str": client.session.save(),
        "phone_code_hash": sent.phone_code_hash,
        "phone": PHONE
    }
    with open("temp_auth_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f)
        
    print("✅ Kod gönderildi! Telefonundaki Telegram uygulamasına gelen kodu bekle.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
