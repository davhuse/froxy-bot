import asyncio
import json
import sys
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneNumberUnoccupiedError
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def complete_login(code, password=None):
    if not os.path.exists('pending_login_7384.json'):
        print("ERROR: pending_login_7384.json not found")
        return
    with open('pending_login_7384.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    phone = data['phone']
    phone_code_hash = data['phone_code_hash']
    session_string = data['session_string']

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            print("SIGN_IN_SUCCESSFUL")
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
                print("2FA_PASSWORD_SUCCESSFUL")
            else:
                print("2FA_PASSWORD_REQUIRED")
                return
        except PhoneNumberUnoccupiedError:
            print("ACCOUNT_DOES_NOT_EXIST_SIGNING_UP...")
            await client.sign_up(code=code, first_name="Reklam", last_name="Hesabi", phone_code_hash=phone_code_hash)
            print("SIGN_UP_SUCCESSFUL")

        me = await client.get_me()
        new_sess = StringSession.save(client.session)
        print("==================================================")
        print(f"✅ HESAP BAŞARIYLA BAĞLANDI!")
        print(f"ID: {me.id}")
        print(f"Name: {me.first_name} {me.last_name or ''} (@{me.username or 'yok'})")
        print(f"Phone: +{me.phone}")
        print("==================================================")
        
        with open("session_7384.txt", "w", encoding="utf-8") as out:
            out.write(new_sess)
            
        # Also save as local session file
        local_client = TelegramClient('account_7384', api_id, api_hash)
        await local_client.connect()
        # save string to bot_config / .env or session file
        print(f"STRING_SESSION_SAVED")
    except Exception as e:
        print("LOGIN_ERROR:", type(e).__name__, "-", e)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    if len(sys.argv) > 2:
        code_input = sys.argv[1]
        pwd_input = sys.argv[2]
        asyncio.run(complete_login(code_input, pwd_input))
    elif len(sys.argv) > 1:
        code_input = sys.argv[1]
        asyncio.run(complete_login(code_input))
    else:
        print("Usage: python login_7384.py <CODE> [2FA_PASSWORD]")
