import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for b in ["KeyVadiSatisBot", "FroxyDestekBOT"]:
        print(f"\n{'='*20} Testing @{b} {'='*20}")
        try:
            bot_ent = await client.get_entity(b)
            await client.send_message(bot_ent, "/start")
            await asyncio.sleep(2)
            msgs = await client.get_messages(bot_ent, limit=3)
            for m in msgs:
                if m.out is False:
                    print(f"  Bot Yanıtı:\n{m.raw_text}")
                    if m.reply_markup:
                        print("  Butonlar:", [[getattr(b, 'text', '') for b in row.buttons] for row in getattr(m.reply_markup, 'rows', [])])
        except Exception as e:
            print(f"Hata: {e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
