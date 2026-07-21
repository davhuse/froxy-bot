import asyncio
import json
import time
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    with open('bot_config.json', encoding='utf-8') as f:
        cfg = json.load(f)
    customer = TelegramClient('c4hex_session', API_ID, API_HASH)
    await customer.start()
    results = []
    for label, username in [('KeyVadiOnline', '@KeyVadiOnline'), ('LisansArenaOnline', '@LisansArenaOnline')]:
        me = await customer.get_entity(username)
        marker = f'Canva Pro test {label} {int(time.time())}'
        before = (await customer.get_messages(me.id, limit=1))[0].id if await customer.get_messages(me.id, limit=1) else 0
        await customer.send_message(me.id, marker)
        await asyncio.sleep(7)
        reply = None
        async for msg in customer.iter_messages(me.id, limit=8):
            if msg.id > before and not msg.out:
                reply = msg
                break
        text = (reply.raw_text or '') if reply else ''
        has_shopier = 'shopier.com' in text.lower()
        results.append((label, bool(reply), has_shopier, text[:180].replace('\n', ' ')))
    await customer.disconnect()
    for label, replied, has_shopier, text in results:
        print(f'{label}: replied={replied} shopier_link={has_shopier} text={text}')

if __name__ == '__main__':
    asyncio.run(main())
