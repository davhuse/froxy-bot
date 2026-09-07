import asyncio
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

# Target groups from gruplar.txt
sample_targets = [
    "kuponsatisgrup", "kuponhesapsatis", "kuponkodindirimilanlar",
    "kodceksatismerkezi", "kuponkodalimsatimm", "ceksatkupon",
    "kuponindirimpazari", "kuponkodalimsatim", "YemekSepetiKuponu",
    "KodKuponMerkezi", "indirimcek", "kuponceking", "yucekuponsatis"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for g in sample_targets:
        print(f"\n{'='*20} GRUP: @{g} {'='*20}")
        try:
            ent = await client.get_entity(g)
            print(f"Başlık: {ent.title} | Üye: {getattr(ent, 'participants_count', 'N/A')}")
            msgs = await client.get_messages(ent, limit=10)
            for m in msgs:
                if m.raw_text:
                    clean = m.raw_text.replace('\n', ' -- ')[:120]
                    sender = getattr(m.sender, 'first_name', 'Anonim') if m.sender else 'Anonim'
                    print(f"  [{sender}]: {clean}")
        except Exception as e:
            print(f"  Hata: {e}")
        await asyncio.sleep(0.5)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
