import sys
import os
import json
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Set standard output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Load config
CONFIG_FILE = "bot_config.json"
with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
    config = json.load(f)

# API credentials
API_ID = 26543169
API_HASH = "8d1b11f0a20a48b5ab21356f9f25712f"

# Use Hesap 3 to test the bots
session_str = config.get("ad_string_session3", "")
if not session_str:
    print("Error: ad_string_session3 not found in config")
    sys.exit(1)

async def test_bot(client, bot_username):
    print(f"\nSending /start to {bot_username}...")
    # Send start command
    bot_entity = await client.get_input_entity(bot_username)
    await client.send_message(bot_entity, "/start")
    
    # Wait for the response (up to 5 seconds)
    print("Waiting for response...")
    await asyncio.sleep(4)
    
    # Fetch latest messages from the bot chat
    messages = await client.get_messages(bot_entity, limit=2)
    print(f"=== Response from {bot_username} ===")
    for msg in reversed(messages):
        print(f"[{msg.date}] Message: {msg.text}")
        if msg.reply_markup:
            print("Buttons:")
            for row in msg.reply_markup.rows:
                row_buttons = []
                for btn in row.buttons:
                    # Check button type
                    btn_text = getattr(btn, 'text', 'Button')
                    row_buttons.append(btn_text)
                print("  | " + " | ".join(row_buttons) + " |")

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Failed to authorize client.")
        await client.disconnect()
        return
        
    await test_bot(client, "@KeyVadiSatisBot")
    await test_bot(client, "@LisansArenaBot")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
