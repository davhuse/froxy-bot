import asyncio
from telethon import TelegramClient

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
ADMIN_ID = 7499698483

bots = {
    "LisansArenaBot": "8971644915:AAESpHgQS5WtAGpCdSI8ACulN9Be9hZ-Dsw",
    "JarvisCraftsBot": "8940174381:AAE5M4yFbIZ8F5W8dsINCD3tQipHCYgOlzg",
    "KeyVadiSupportBot": "8617308476:AAFTTBoU4KYdSf5m71AUnYsOkT9fhgGQMkA",
    "FroxySupportBot": "8845484139:AAFRYXLbPqd1GmdsOa8n0xgNNHVHhBzIWlA",
}

async def test_all_bots():
    for name, token in bots.items():
        client = TelegramClient(f"test_bot_{name}", API_ID, API_HASH)
        try:
            await client.start(bot_token=token)
            me = await client.get_me()
            try:
                msg = await client.send_message(ADMIN_ID, f"Test: {name} can reach admin {ADMIN_ID}")
                print(f"[{name}] (@{me.username}) -> BASARILI (Msg ID: {msg.id})")
            except Exception as e:
                print(f"[{name}] (@{me.username}) -> HATA: {type(e).__name__}: {e}")
        except Exception as start_err:
            print(f"[{name}] -> Start hatasi: {start_err}")
        finally:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_all_bots())
