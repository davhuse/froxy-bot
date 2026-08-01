import asyncio, sys, json
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = '+905056798875'
phone_code_hash = '1cdfbb0cf7454df557'

async def complete_login(code, password=None):
    client = TelegramClient('login_keyvadi_0505', api_id, api_hash)
    await client.connect()
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
            else:
                print("PASSWORD_REQUIRED")
                await client.disconnect()
                return False
        me = await client.get_me()
        print(f"SUCCESS:{me.id}:{me.first_name}:{me.phone}")
        return True
    except Exception as e:
        print(f"ERROR:{e}")
        return False
    finally:
        await client.disconnect()

if __name__ == "__main__":
    code_in = sys.argv[1] if len(sys.argv) > 1 else ""
    pass_in = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(complete_login(code_in, pass_in))
