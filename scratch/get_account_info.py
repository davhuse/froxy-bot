import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = "7ba4072dcf0a05a7ccf80e570866b6d8"

sessions = {
    "Eski KeyVadiSatis (Hesap 2)": "1AZWarzgBu3nimycUJcGiTa-gMRXl1a_RG4dWoVJZpu3qchcjgH4zR5x2FnS8OFbRCXlZ1dTLjeCBP0rCepRDoLRLCbzoJBgMqAdMUb9EABFMzL8o2TNZxrnIFNQUI4m-pbdT3cHO5t9O7Ts4y4tZLEu9m9VmCh5g4K0vkqL0ezBs4H4OmiKq1pQUoE8Pxubh4X-NTe_rTlk76iaI524KXbuvxLiGnRqnqPIyjibvsMfGWFPBTb9WgoNynaMijjQAorNmHJl0nGpmwQIkCclvOk6iP0cMVlSqm6VBoluBnQ7DJMBmCHOZffyW-r2j6X_VepeJQCjNpTPuEgHMBLIZCYOfn0McO9g=",
    "Eski LisansArena (Hesap 3)": "1AZWarzMBuxf5pi0qnDE4m_X3vtvYy-Y_a-RRROPx3YfavIpQeDlhKerJ_RRcl1le7CJYwXNPWwJWWMxgE08cSwSxqvcDts_PhqsJeXjQvWo17xdzc5k11mY4_O99DA8VjufYYTMDd5Dhc4v6t3mR_dU1vHM_eEQGvWms4JkX6BcpwZz8Bp5MtXGUEGX8FpD3inFg12hkQt-HOOtoeXKqT096lTPN4Bo9qAfQmkVcTSqL4nMQY8W45sZP_VmoUcnNhhkNvaqD2PQaMleRKFNGx4Zlisbhp36TQQGJCKI28FuNLZ7WT85lijOypQ9XHtsCn0xx771kuqrcjnX7jkK3kC2Gdukl11g=",
    "Yeni KeyVadiSatis (Hesap 2 - Yeni)": "1BVtsOG0Bu1GAAiu17AGLK79bqLss-2keFt0Kugqnq1HUT1QHrjA1Jp6WI-TUhG4bQqSb51U3IqJSs3deRrC1DSDAJAXsT_Lo9VI8WcqqRreP5eBYp4yKWV8sEipJ7DLkMZiKy-o0fpnBNvpVKCEHz12H0wkF72dmkngFjGTV84tKw5yUJfT3xumBc-k-lf7NFQhNWnSQagkZNwb4UGHk_umO6ZcvZrBiu-1NdubZ4nUlI0LFmQ5wA3WQsISS1WVZoFBkmcEIjXtRVb7ygjB_7Zmx3Mr6v_TabgycCthAYMox61RTzZSTU686_bXbPpq_Dgrp50hgfj-Wp-S6UWK1A2MHJxPlyH4=",
    "Yeni LisansArenaSatis (Hesap 3 - Yeni)": "1AZWarzsBuyAiCinDXh9__cCrDW0v3_s7zFaKzpygVSlkMgV3QEKHAtoRcb9zWetfi-F3Wsbb6lF8yCMsPPEdKDGI9q-Ojf5HmK-GZVlrDpl65za7Ryou5Vx7L9jyX8jiwBpJ8LDkH4qg2l5pT-IQQqtPfFyaPwGfp-kIgzpHCvI0YzQy27Gk0xDsz8syrSulTiZ8dFsJW8sxI4pHUOerilaOFmv6ChOee7ZBBdXN_bm75f0Tg__UwxXOz0NSTWqYyqTiodBeHvFVVGq5eQAwZCUDTcQsTktRhzxrBQ3pP6twIpeTSQKtuuJ_YvJ5WVQ_No3b27TOFajGHuNu_9MZBSh2qxN13ls="
}

async def check():
    for name, s_str in sessions.items():
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"{name} | Phone: +{me.phone} | Username: @{me.username}")
        else:
            print(f"{name} | YETKISIZ")
        await client.disconnect()

asyncio.run(check())
