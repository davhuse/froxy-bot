import asyncio
import os
import sys
from pyrogram import Client

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def test_pyrogram():
    session_name = "sessions/user_8181918048"
    try:
        app = Client("sessions/user_8181918048", api_id=api_id, api_hash=api_hash)
        await app.start()
        me = await app.get_me()
        print(f"Pyrogram session OK: {me.first_name} (ID: {me.id}, Username: @{me.username})")
        await app.stop()
    except Exception as e:
        print(f"Pyrogram error: {e}")

if __name__ == '__main__':
    asyncio.run(test_pyrogram())
