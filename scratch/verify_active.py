import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open('bot_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

s2 = cfg.get('ad_string_session2', '')
s3 = cfg.get('ad_string_session3', '')

async def verify_active_accounts():
    print('--- AKTİF BOT CONFIG HESAPLARI ---')

    c2 = TelegramClient(StringSession(s2), api_id, api_hash)
    await c2.connect()
    me2 = await c2.get_me()
    print(f'Hesap 2 (KeyVadi): ID={me2.id}, Username=@{me2.username}, FirstName="{me2.first_name}"')
    await c2.disconnect()

    c3 = TelegramClient(StringSession(s3), api_id, api_hash)
    await c3.connect()
    me3 = await c3.get_me()
    print(f'Hesap 3 (LisansArena): ID={me3.id}, Username=@{me3.username}, FirstName="{me3.first_name}"')
    await c3.disconnect()

if __name__ == '__main__':
    asyncio.run(verify_active_accounts())
