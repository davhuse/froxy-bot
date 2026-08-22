import asyncio
from telethon import TelegramClient

API_ID = 26588523
API_HASH = "fa7a57a0773d40e118ae0be9bcba846b"
SESSION_PATH = "sessions/LisansArenaOnline.session"

async def test_bots():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("User not authorized in session!")
        return

    me = await client.get_me()
    print(f"Logged in as user: @{me.username} ({me.id})")

    for bot_username in ["@KeyVadiSatisBot", "@LisansArenaBot"]:
        print(f"\n--- Testing {bot_username} ---")
        try:
            entity = await client.get_input_entity(bot_username)
            sent = await client.send_message(entity, "/start")
            print(f"Sent /start (msg id: {sent.id}). Waiting 5s for reply...")
            await asyncio.sleep(5)
            
            # Fetch recent messages
            messages = await client.get_messages(entity, limit=3)
            print(f"Recent messages from {bot_username}:")
            for m in messages:
                sender = "ME" if m.out else "BOT"
                print(f"  [{sender}] {m.text[:120] if m.text else '[media/buttons]'}")
        except Exception as e:
            print(f"Error testing {bot_username}: {e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_bots())
