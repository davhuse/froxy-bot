import asyncio
import json
import os
import sys

# Windows terminal encoding fix
sys.stdout.reconfigure(encoding='utf-8')

from telethon import TelegramClient, events
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def test_bot_interaction(client, bot_username, name):
    print(f"\n[TEST] Testing interaction with {name} (@{bot_username})...")
    try:
        # Clear previous dialog history or just send message
        entity = await client.get_input_entity(bot_username)
        
        # Event handler to capture the reply
        reply_received = asyncio.Event()
        captured_reply = []

        @client.on(events.NewMessage(incoming=True, from_users=bot_username))
        async def handler(event):
            captured_reply.append(event.message.text)
            reply_received.set()

        # Send /start command
        await client.send_message(entity, "/start")
        print(f" -> Sent '/start' to @{bot_username}. Waiting for reply...")
        
        try:
            # Wait for 8 seconds for a reply
            await asyncio.wait_for(reply_received.wait(), timeout=8.0)
            print(f"✅ [PASS] {name} responded successfully!")
            print(f"--- Reply Preview ---\n{captured_reply[0][:150]}...\n---------------------")
            client.remove_event_handler(handler)
            return True
        except asyncio.TimeoutError:
            print(f"❌ [FAIL] {name} did NOT respond in time (timeout).")
            client.remove_event_handler(handler)
            return False
            
    except Exception as e:
        print(f"❌ [FAIL] Error testing {name}: {e}")
        return False

async def main():
    print("=== LIVE BOT INTEGRATION TESTING ===")
    print("-------------------------------------")
    
    if not os.path.exists("bot_config.json"):
        print("Error: bot_config.json not found!")
        return

    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    session_str = cfg.get("ad_string_session", "")
    if not session_str:
        print("Error: ad_string_session is missing in config!")
        return

    print("Connecting test client (Account #1)...")
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Error: Test client is not authorized!")
        return
        
    print("Test client connected successfully.")

    # Run tests sequentially
    await test_bot_interaction(client, "KeyVadiSatisBot", "KeyVadi Satış Botu")
    await test_bot_interaction(client, "FroxyDestekBOT", "Froxy AI Destek Botu")
    await test_bot_interaction(client, "LisansArenaBot", "LisansArena Botu")

    await client.disconnect()
    print("\n-------------------------------------")
    print("=== TESTING COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(main())
