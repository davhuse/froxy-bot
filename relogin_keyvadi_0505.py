import asyncio, sys, os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
phone = '+905056798875'

async def main():
    # Always create a brand-new authorization key. Reusing the old file-backed
    # session would keep triggering AuthKeyDuplicatedError after two runtimes
    # used it from different IP addresses.
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        res = await client.send_code_request(phone)
        print(f"CODE_SENT:{res.phone_code_hash}", flush=True)
        
        code_file = "code_input_0505.txt"
        if os.path.exists(code_file):
            os.remove(code_file)
            
        print("WAITING_FOR_CODE...", flush=True)
        for _ in range(180): # Wait up to 3 minutes
            if os.path.exists(code_file):
                with open(code_file, "r") as f:
                    code = f.read().strip()
                if code:
                    print(f"RECEIVED_CODE:{code}", flush=True)
                    try:
                        await client.sign_in(phone=phone, code=code, phone_code_hash=res.phone_code_hash)
                        print("SIGN_IN_SUCCESSFUL", flush=True)
                        break
                    except SessionPasswordNeededError:
                        print("PASSWORD_REQUIRED", flush=True)
                        break
                    except Exception as err:
                        print(f"SIGN_IN_ERROR:{err}", flush=True)
                        await client.disconnect()
                        return
            await asyncio.sleep(1)
            
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"SUCCESS:{me.id}:{me.first_name}:{me.phone}", flush=True)
        
        # Export StringSession for Render without printing the secret.
        str_sess = StringSession.save(client.session)
        with open("keyvadi_session_output.txt", "w", encoding="utf-8") as f:
            f.write(str_sess)
        print("NEW_SESSION_SAVED", flush=True)

        # Restore profile settings
        try:
            await client(UpdateProfileRequest(
                first_name='KeyVadi',
                last_name='| Dijital Lisans & Yazılım',
                about='Referanslar: https://t.me/satisrefim/9615 | Bot: @KeyVadiSatisBot'
            ))
            print("UPDATED_PROFILE", flush=True)
        except Exception as e:
            print(f"PROFILE_UPDATE_NOTICE:{e}", flush=True)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
