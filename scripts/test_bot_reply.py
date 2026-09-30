# -*- coding: utf-8 -*-
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 26569103
API_HASH = "80f68132924294ca237617b07903ee52"

session_file = "dijitalpazarim_session_string.txt"
if not os.path.exists(session_file):
    print("Session file not found!")
    sys.exit(1)

session_str = open(session_file, 'r', encoding='utf-8').read().strip()

async def test_bot():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("User not authorized!")
        return
    
    print("Sending /start to @DijitalPazarimBot...")
    msg = await client.send_message("DijitalPazarimBot", "/start")
    print(f"Sent message id: {msg.id}. Waiting 5 seconds for reply...")
    await asyncio.sleep(5)
    
    # Read latest messages in dialog with bot
    async for m in client.iter_messages("DijitalPazarimBot", limit=3):
        sender = "BOT" if m.out is False else "ME"
        print(f"[{sender}] {m.text[:100]}")
    
    await client.disconnect()

asyncio.run(test_bot())
