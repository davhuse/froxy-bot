import asyncio
import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

phones = [
    "+6285191728354",
    "+13412648927"
]

async def get_session(phone):
    print(f"\n{'='*50}")
    print(f"Hesap: {phone}")
    print(f"{'='*50}")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = input(f"[{phone}] Telegram'dan gelen kodu gir: ").strip()
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "2FA" in str(e) or "password" in str(e).lower() or "SessionPasswordNeeded" in str(type(e).__name__):
                password = input(f"[{phone}] 2FA şifresini gir: ").strip()
                await client.sign_in(password=password)
            else:
                print(f"Hata: {e}")
                await client.disconnect()
                return
    
    me = await client.get_me()
    session_str = client.session.save()
    print(f"\n[OK] Basarili! Hesap: {me.first_name} (@{me.username}) ID: {me.id}")
    print(f"\n[SESSION]:\n{session_str}\n")
    await client.disconnect()
    return session_str

async def main():
    sessions = {}
    for phone in phones:
        s = await get_session(phone)
        if s:
            sessions[phone] = s
    
    print("\n" + "="*80)
    print("TÜM SESSION'LAR:")
    print("="*80)
    for phone, s in sessions.items():
        print(f"\n{phone}:\n{s}\n")

if __name__ == "__main__":
    asyncio.run(main())
