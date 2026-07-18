import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = "7ba4072dcf0a05a7ccf80e570866b6d8"

old_sessions = [
    ("Hesap #2 (Eski KeyVadiSatis)", "1AZWarzgBu3nimycUJcGiTa-gMRXl1a_RG4dWoVJZpu3qchcjgH4zR5x2FnS8OFbRCXlZ1dTLjeCBP0rCepRDoLRLCbzoJBgMqAdMUb9EABFMzL8o2TNZxrnIFNQUI4m-pbdT3cHO5t9O7Ts4y4tZLEu9m9VmCh5g4K0vkqL0ezBs4H4OmiKq1pQUoE8Pxubh4X-NTe_rTlk76iaI524KXbuvxLiGnRqnqPIyjibvsMfGWFPBTb9WgoNynaMijjQAorNmHJl0nGpmwQIkCclvOk6iP0cMVlSqm6VBoluBnQ7DJMBmCHOZffyW-r2j6X_VepeJQCjNpTPuEgHMBLIZCYOfn0McO9g="),
    ("Hesap #3 (Eski LisansArena)", "1AZWarzMBuxf5pi0qnDE4m_X3vtvYy-Y_a-RRROPx3YfavIpQeDlhKerJ_RRcl1le7CJYwXNPWwJWWMxgE08cSwSxqvcDts_PhqsJeXjQvWo17xdzc5k11mY4_O99DA8VjufYYTMDd5Dhc4v6t3mR_dU1vHM_eEQGvWms4JkX6BcpwZz8Bp5MtXGUEGX8FpD3inFg12hkQt-HOOtoeXKqT096lTPN4Bo9qAfQmkVcTSqL4nMQY8W45sZP_VmoUcnNhhkNvaqD2PQaMleRKFNGx4Zlisbhp36TQQGJCKI28FuNLZ7WT85lijOypQ9XHtsCn0xx771kuqrcjnX7jkK3kC2Gdukl11g=")
]

async def logout_account(name, session):
    print(f"[START] Connecting to {name}...")
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"[WARN] {name} is not authorized (already logged out)")
        await client.disconnect()
        return
        
    print(f"[LOGOUT] Logging out of {name}...")
    await client.log_out()
    print(f"[OK] Logged out of {name} successfully")
    await client.disconnect()

async def main():
    for name, session in old_sessions:
        try:
            await logout_account(name, session)
        except Exception as e:
            print(f"[ERR] Error on {name}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
