import asyncio
import os
import sys
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

sessions = [
    'sessions/user_8181918048',
    'c4hex_session',
    'login_lisans_final',
    'login_keyvadi_final',
    'login_lisans_final2',
    'login_keyvadi_final2',
    'froxy_bot_session',
    'froxy_destek_bot_session',
]

async def main():
    for s in sessions:
        if not os.path.exists(f"{s}.session"):
            print(f"{s}: FILE NOT FOUND")
            continue
        try:
            client = TelegramClient(s, api_id, api_hash)
            await client.connect()
            auth = await client.is_user_authorized()
            if auth:
                me = await client.get_me()
                is_bot = getattr(me, 'bot', False)
                print(f"{s}: AUTH OK | Name: {me.first_name} | ID: {me.id} | is_bot: {is_bot}")
            else:
                print(f"{s}: NOT AUTHORIZED")
            await client.disconnect()
        except Exception as e:
            print(f"{s}: ERROR: {e}")

if __name__ == '__main__':
    asyncio.run(main())
