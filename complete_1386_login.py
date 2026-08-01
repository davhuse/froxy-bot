import asyncio, sys, json, os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest, GetUserPhotosRequest

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = '+13869914668'

phone_code_hash = ''
if os.path.exists('code_hash_1386.txt'):
    with open('code_hash_1386.txt', 'r') as f:
        phone_code_hash = f.read().strip()

async def complete_login(code, password=None):
    client = TelegramClient('login_temp_1386', api_id, api_hash)
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
        
        # Clear username & bio on old +13869914668 KeyVadi account
        try:
            await client(UpdateUsernameRequest(username=''))
            print("Cleared old username from +13869914668!")
        except Exception as e:
            print("Username clear notice:", e)
            
        try:
            await client(UpdateProfileRequest(first_name='Yedek', last_name='Hesap', about=''))
            print("Cleared name & bio from +13869914668!")
        except Exception as e:
            print("Profile clear notice:", e)

        try:
            photos = await client(GetUserPhotosRequest(user_id=me.id, offset=0, max_id=0, limit=100))
            if photos.photos:
                await client(DeletePhotosRequest(id=photos.photos))
                print(f"Deleted {len(photos.photos)} photos from +13869914668!")
        except Exception as e:
            print("Photos clear notice:", e)

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
