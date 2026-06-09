import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

# File IPC paths
CODE_INPUT = "code_input.txt"
PASSWORD_INPUT = "password_input.txt"

async def get_code():
    print("\n👉 WAITING FOR CODE! Please write the SMS code into code_input.txt...")
    # Clean up old file if exists
    if os.path.exists(CODE_INPUT):
        try: os.remove(CODE_INPUT)
        except: pass
        
    while True:
        if os.path.exists(CODE_INPUT):
            try:
                with open(CODE_INPUT, 'r', encoding='utf-8') as f:
                    code = f.read().strip()
                if code:
                    print(f"✅ Code read from file: {code}")
                    try: os.remove(CODE_INPUT)
                    except: pass
                    return code
            except Exception as e:
                pass
        await asyncio.sleep(1)

async def get_password():
    print("\n👉 WAITING FOR PASSWORD! Please write the 2FA password into password_input.txt...")
    if os.path.exists(PASSWORD_INPUT):
        try: os.remove(PASSWORD_INPUT)
        except: pass
        
    while True:
        if os.path.exists(PASSWORD_INPUT):
            try:
                with open(PASSWORD_INPUT, 'r', encoding='utf-8') as f:
                    password = f.read().strip()
                if password:
                    print("✅ Password read from file.")
                    try: os.remove(PASSWORD_INPUT)
                    except: pass
                    return password
            except Exception as e:
                pass
        await asyncio.sleep(1)

async def main():
    phone = "+18017381002"
    print(f"🚀 Starting file-IPC login flow for {phone}...")
    
    # Remove old output files
    for fpath in ["session_key_output.txt", CODE_INPUT, PASSWORD_INPUT]:
        if os.path.exists(fpath):
            try: os.remove(fpath)
            except: pass
            
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.start(
            phone=phone,
            code_callback=get_code,
            password=get_password
        )
        print("\n✅ LOGIN SUCCESS!")
        session_str = client.session.save()
        print("🔑 SIZIN STRINGSESSION ANAHTARINIZ:")
        print(session_str)
        with open("session_key_output.txt", "w", encoding="utf-8") as f:
            f.write(session_str)
        print("\nSaved output to session_key_output.txt")
    except Exception as e:
        print(f"❌ Error during login: {type(e).__name__} - {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
