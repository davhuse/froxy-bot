import asyncio
import sys
from telethon import TelegramClient, functions
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

TEST_SOHBET_GROUPS = [
    "turkcesohbet",
    "sohbetturkiye",
    "turkcesohbetler",
    "sohbetgrubumuz",
    "muhabbetkahvesi",
    "chat_turkiye",
    "turkiyesohbetalani",
    "turksohbetgrubu"
]

async def check():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    print("Checking sohbet groups with @Userrrrrrrrrra...")
    
    valid_groups = []
    for g in TEST_SOHBET_GROUPS:
        try:
            entity = await client.get_entity(g)
            print(f"✅ Bulundu: {g} -> Başlık: {getattr(entity, 'title', 'Grup')}")
            valid_groups.append(g)
        except Exception as e:
            print(f"❌ {g} bulunamadı: {e}")
            
    await client.disconnect()
    print("\nDoğrulanmış sohbet grupları:", valid_groups)

if __name__ == "__main__":
    asyncio.run(check())
