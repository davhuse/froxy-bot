# -*- coding: utf-8 -*-
"""Request login code for +18595173039 and save phone_code_hash."""

import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
PHONE = sys.argv[1] if len(sys.argv) > 1 else '+18595173039'

async def main():
    print(f"Telegram'a bağlanılıyor ve {PHONE} numarasına kod talep ediliyor...")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    try:
        sent = await client.send_code_request(PHONE)
        delivery_type = type(sent.type).__name__
        print(f"BAŞARILI! Kod gönderildi.")
        print(f"Teslimat Yöntemi: {delivery_type}")
        print(f"Phone Code Hash: {sent.phone_code_hash}")
        
        # Save temporary session and phone_code_hash
        data = {
            'phone': PHONE,
            'phone_code_hash': sent.phone_code_hash,
            'session': client.session.save(),
            'delivery_type': delivery_type
        }
        with open('temp_dp_auth.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print("Geçici oturum temp_dp_auth.json dosyasına kaydedildi.")
        
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
