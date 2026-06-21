import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
except:
    pass

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    print("StringSession Olusturucu")
    print("--------------------------------------")
    
    phone = input("Telefon numaranizi girin (ornek: +905xxxxxxxxx): ").strip()
    
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    result = await client.send_code_request(phone)
    code = input("Telegram'dan gelen dogrulama kodunu girin: ").strip()
    
    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "Two-steps verification" in str(e) or "password" in str(type(e).__name__).lower():
            pw = input("2FA sifresi girin: ").strip()
            await client.sign_in(password=pw)
        else:
            raise e
    
    session_str = client.session.save()
    print("\nGiris basarili!")
    print("--------------------------------------")
    print("STRINGSESSION ANAHTARINIZ:\n")
    print(session_str)
    print("\n--------------------------------------")
    
    # Also save to file for easy copy
    with open("session_key_output.txt", "w") as f:
        f.write(session_str)
    print("Anahtar ayrica session_key_output.txt dosyasina kaydedildi.")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
