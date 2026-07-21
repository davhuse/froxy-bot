import asyncio
import time
from telethon import TelegramClient

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'


async def newest_incoming(client, entity, after_id):
    async for message in client.iter_messages(entity, limit=12):
        if message.id > after_id and not message.out:
            return message
    return None


async def main():
    customer = TelegramClient('c4hex_session', API_ID, API_HASH)
    await customer.start()
    results = []
    try:
        for label, username in [('KeyVadiOnline', '@KeyVadiOnline'), ('LisansArenaOnline', '@LisansArenaOnline')]:
            entity = await customer.get_entity(username)
            before = (await customer.get_messages(entity, limit=1))[0].id
            await customer.send_message(entity, f'merhaba nasılsın test {label} {time.time_ns()}')
            await asyncio.sleep(8)
            greeting_reply = await newest_incoming(customer, entity, before)

            before = (await customer.get_messages(entity, limit=1))[0].id
            await customer.send_message(entity, f'Canva Pro fiyat ve Shopier linki nedir test {label} {time.time_ns()}')
            await asyncio.sleep(8)
            sales_reply = await newest_incoming(customer, entity, before)
            sales_text = (sales_reply.raw_text or '') if sales_reply else ''
            results.append({
                'label': label,
                'greeting_replied': bool(greeting_reply),
                'sales_replied': bool(sales_reply),
                'shopier_link': 'shopier.com' in sales_text.lower(),
                'sales_text': sales_text[:180].replace('\n', ' '),
            })
    finally:
        await customer.disconnect()
    for item in results:
        print(item)


if __name__ == '__main__':
    asyncio.run(main())
