import asyncio
import json
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    with open('bot_config.json', encoding='utf-8') as f:
        cfg = json.load(f)
    for label, key in [('KeyVadiOnline', 'ad_string_session2'), ('LisansArenaOnline', 'ad_string_session3')]:
        client = TelegramClient(StringSession(cfg[key]), API_ID, API_HASH)
        await client.connect()
        try:
            me = await client.get_me()
            try:
                entity = await client.get_entity('mukyemek')
                await client(JoinChannelRequest(entity))
                print(f'{label}: joined @mukyemek')
            except FloodWaitError as exc:
                print(f'{label}: flood_wait={exc.seconds}')
            except Exception as exc:
                name = type(exc).__name__
                if 'AlreadyParticipant' in name or 'already' in str(exc).lower():
                    print(f'{label}: already_member')
                elif 'InviteRequestSent' in name or 'invite' in str(exc).lower():
                    print(f'{label}: join_request_sent')
                else:
                    print(f'{label}: {name}')
        finally:
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
