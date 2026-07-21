import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

key3 = "1AZWarzsBuyAiCinDXh9__cCrDW0v3_s7zFaKzpygVSlkMgV3QEKHAtoRcb9zWetfi-F3Wsbb6lF8yCMsPPEdKDGI9q-Ojf5HmK-GZVlrDpl65za7Ryou5Vx7L9jyX8jiwBpJ8LDkH4qg2l5pT-IQQqtPfFyaPwGfp-kIgzpHCvI0YzQy27Gk0xDsz8syrSulTiZ8dFsJW8sxI4pHUOerilaOFmv6ChOee7ZBBdXN_bm75f0Tg__UwxXOz0NSTWqYyqTiodBeHvFVVGq5eQAwZCUDTcQsTktRhzxrBQ3pP6twIpeTSQKtuuJ_YvJ5WVQ_No3b27TOFajGHuNu_9MZBSh2qxN13ls="

async def test_session():
    c = TelegramClient(StringSession(key3), api_id, api_hash)
    await c.connect()
    if await c.is_user_authorized():
        me = await c.get_me()
        print(f"Key 3 Authorized! User ID: {me.id} | First Name: {me.first_name} | Username: {getattr(me, 'username', 'N/A')}")
    else:
        print("Key 3 is NOT authorized!")
    await c.disconnect()

if __name__ == '__main__':
    asyncio.run(test_session())
