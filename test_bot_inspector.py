import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
bot_token = '8961373302:AAGNs9fcPFU_XcWDUlhbNhQ2hRNzyRu6_MI'

async def test_bot_read():
    client = TelegramClient('test_bot_reader', api_id, api_hash)
    await client.start(bot_token=bot_token)
    print("Bot connected successfully!")
    
    test_usernames = ["kuponindirimsatis", "tahaaslan11", "indirimkodusatis"]
    for u in test_usernames:
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            print(f"Username: @{u}")
            print(f"  Title: {getattr(entity, 'title', '')}")
            print(f"  Is Group/Megagroup: {getattr(entity, 'megagroup', False)}")
            print(f"  Is Broadcast Channel: {getattr(entity, 'broadcast', False)}")
            print(f"  Participants: {getattr(full.full_chat, 'participants_count', 'N/A')}")
            print(f"  About: {getattr(full.full_chat, 'about', '')[:100]}")
            
            # Can bot get messages from public group?
            try:
                msgs = await client.get_messages(entity, limit=3)
                print(f"  Recent msgs count: {len(msgs)}")
                for m in msgs:
                    if m.text:
                        print(f"    - [{m.date}] {m.text[:60].replace(chr(10), ' ')}")
            except Exception as me:
                print(f"  Could not get msgs: {me}")
        except Exception as e:
            print(f"Error on @{u}: {e}")
            
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_bot_read())
