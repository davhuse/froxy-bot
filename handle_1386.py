import asyncio, sys, os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest, GetUserPhotosRequest

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = '+13869914668'

async def main():
    client = TelegramClient('login_temp_1386', api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        res = await client.send_code_request(phone)
        print(f"NEW_CODE_SENT:{res.phone_code_hash}", flush=True)
        
        # Wait up to 120 seconds for code file
        code_file = "code_input.txt"
        if os.path.exists(code_file):
            os.remove(code_file)
            
        print("WAITING_FOR_CODE_FILE...", flush=True)
        for _ in range(120):
            if os.path.exists(code_file):
                with open(code_file, "r") as f:
                    code = f.read().strip()
                if code:
                    print(f"RECEIVED_CODE:{code}", flush=True)
                    try:
                        await client.sign_in(phone=phone, code=code, phone_code_hash=res.phone_code_hash)
                        print("SIGN_IN_SUCCESSFUL", flush=True)
                        break
                    except Exception as err:
                        print(f"SIGN_IN_ERROR:{err}", flush=True)
                        await client.disconnect()
                        return
            await asyncio.sleep(1)
            
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"AUTHORIZED_ACCOUNT:{me.id}:{me.first_name}:{me.phone}", flush=True)
        
        # Clear username & bio on old +13869914668 KeyVadi account
        try:
            await client(UpdateUsernameRequest(username=''))
            print("Cleared old username from +13869914668!", flush=True)
        except Exception as e:
            print(f"Username clear notice: {e}", flush=True)
            
        try:
            await client(UpdateProfileRequest(first_name='Yedek', last_name='Hesap', about=''))
            print("Cleared name & bio from +13869914668!", flush=True)
        except Exception as e:
            print(f"Profile clear notice: {e}", flush=True)

        try:
            photos = await client(GetUserPhotosRequest(user_id=me.id, offset=0, max_id=0, limit=100))
            if photos.photos:
                await client(DeletePhotosRequest(id=photos.photos))
                print(f"Deleted {len(photos.photos)} photos from +13869914668!", flush=True)
        except Exception as e:
            print(f"Photos clear notice: {e}", flush=True)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
