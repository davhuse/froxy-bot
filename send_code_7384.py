import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = '+12237587384'

async def send_code():
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        session_str = StringSession.save(client.session)
        data = {
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
            "session_string": session_str
        }
        with open("pending_login_7384.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("CODE_SENT_SUCCESSFULLY")
        print(f"Telefon: {phone}")
        print(f"Phone code hash: {sent.phone_code_hash}")
    except Exception as e:
        print("ERROR_SENDING_CODE:", type(e).__name__, "-", e)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(send_code())
