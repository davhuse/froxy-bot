import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateUsernameRequest

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

accounts = [
    {
        "phone": "+6285191728354",
        "session": "1BVtsOG0Bu1GAAiu17AGLK79bqLss-2keFt0Kugqnq1HUT1QHrjA1Jp6WI-TUhG4bQqSb51U3IqJSs3deRrC1DSDAJAXsT_Lo9VI8WcqqRreP5eBYp4yKWV8sEipJ7DLkMZiKy-o0fpnBNvpVKCEHz12H0wkF72dmkngFjGTV84tKw5yUJfT3xumBc-k-lf7NFQhNWnSQagkZNwb4UGHk_umO6ZcvZrBiu-1NdubZ4nUlI0LFmQ5wA3WQsISS1WVZoFBkmcEIjXtRVb7ygjB_7Zmx3Mr6v_TabgycCthAYMox61RTzZSTU686_bXbPpq_Dgrp50hgfj-Wp-S6UWK1A2MHJxPlyH4=",
        "candidates": ["KeyVadiDestek2", "KeyVadi_Destek", "KeyVadiSupport", "KeyVadiStore", "KVDestek", "KeyVadiResmi"]
    },
    {
        "phone": "+13412648927",
        "session": "1AZWarzsBuyAiCinDXh9__cCrDW0v3_s7zFaKzpygVSlkMgV3QEKHAtoRcb9zWetfi-F3Wsbb6lF8yCMsPPEdKDGI9q-Ojf5HmK-GZVlrDpl65za7Ryou5Vx7L9jyX8jiwBpJ8LDkH4qg2l5pT-IQQqtPfFyaPwGfp-kIgzpHCvI0YzQy27Gk0xDsz8syrSulTiZ8dFsJW8sxI4pHUOerilaOFmv6ChOee7ZBBdXN_bm75f0Tg__UwxXOz0NSTWqYyqTiodBeHvFVVGq5eQAwZCUDTcQsTktRhzxrBQ3pP6twIpeTSQKtuuJ_YvJ5WVQ_No3b27TOFajGHuNu_9MZBSh2qxN13ls=",
        "candidates": ["LisansArenaDestek"]  # already set, just verify
    }
]

async def set_username(phone, session, candidates):
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"[{phone}] YETKISIZ!")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"[{phone}] Mevcut username: @{me.username} | ID: {me.id}")

    for username in candidates:
        try:
            await client(UpdateUsernameRequest(username=username))
            print(f"[{phone}] [OK] Username ayarlandi: @{username}")
            break
        except Exception as e:
            print(f"[{phone}] @{username} bos degil veya hata: {e}")

    await client.disconnect()

async def main():
    for acc in accounts:
        await set_username(acc["phone"], acc["session"], acc["candidates"])
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
