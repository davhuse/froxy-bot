import asyncio
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import DeletePhotosRequest

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

# Original sessions of the frozen accounts
sessions = {
    "Hesap #2 (KeyVadiSatis)": "1AZWarzgBu3nimycUJcGiTa-gMRXl1a_RG4dWoVJZpu3qchcjgH4zR5x2FnS8OFbRCXlZ1dTLjeCBP0rCepRDoLRLCbzoJBgMqAdMUb9EABFMzL8o2TNZxrnIFNQUI4m-pbdT3cHO5t9O7Ts4y4tZLEu9m9VmCh5g4K0vkqL0ezBs4H4OmiKq1pQUoE8Pxubh4X-NTe_rTlk76iaI524KXbuvxLiGnRqnqPIyjibvsMfGWFPBTb9WgoNynaMijjQAorNmHJl0nGpmwQIkCclvOk6iP0cMVlSqm6VBoluBnQ7DJMBmCHOZffyW-r2j6X_VepeJQCjNpTPuEgHMBLIZCYOfn0McO9g=",
    "Hesap #3 (LisansArena)": "1AZWarzMBuxf5pi0qnDE4m_X3vtvYy-Y_a-RRROPx3YfavIpQeDlhKerJ_RRcl1le7CJYwXNPWwJWWMxgE08cSwSxqvcDts_PhqsJeXjQvWo17xdzc5k11mY4_O99DA8VjufYYTMDd5Dhc4v6t3mR_dU1vHM_eEQGvWms4JkX6BcpwZz8Bp5MtXGUEGX8FpD3inFg12hkQt-HOOtoeXKqT096lTPN4Bo9qAfQmkVcTSqL4nMQY8W45sZP_VmoUcnNhhkNvaqD2PQaMleRKFNGx4Zlisbhp36TQQGJCKI28FuNLZ7WT85lijOypQ9XHtsCn0xx771kuqrcjnX7jkK3kC2Gdukl11g="
}

async def retire_account(name, s_str):
    print(f"Connecting to {name}...")
    from telethon.sessions import StringSession
    from telethon.tl.functions.account import UpdateUsernameRequest
    client = TelegramClient(StringSession(s_str), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[{name}] NOT AUTHORIZED")
            await client.disconnect()
            return
            
        # 1. Update Profile (Name -> ".", Bio -> "")
        print(f"[{name}] Updating profile name to '.' and clearing bio...")
        await client(UpdateProfileRequest(first_name=".", last_name="", about=""))
        
        # 2. Clear username
        print(f"[{name}] Clearing username...")
        try:
            await client(UpdateUsernameRequest(username=""))
            print(f"[{name}] Username cleared.")
        except Exception as ue:
            print(f"[{name}] Username clear skipped (may not have one): {ue}")
        
        # 3. Delete all profile photos
        print(f"[{name}] Fetching profile photos...")
        photos = await client.get_profile_photos('me')
        if photos:
            print(f"[{name}] Deleting {len(photos)} profile photos...")
            await client(DeletePhotosRequest(photos))
            print(f"[{name}] All profile photos deleted.")
        else:
            print(f"[{name}] No profile photos found.")
            
        print(f"✅ {name} retired successfully.")
        await client.disconnect()
    except Exception as e:
        print(f"[{name}] Error: {e}")

async def main():
    print("=" * 80)
    print("RETIRING FROZEN ACCOUNTS (CLEARING NAME, USERNAME AND PROFILE PHOTOS)")
    print("=" * 80)
    for name, s_str in sessions.items():
        await retire_account(name, s_str)
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main())
