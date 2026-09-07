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

# Target groups where KeyVadi and Froxy recently posted
test_groups = [
    "kuponceking", "indirimcek", "KodKuponMerkezi",
    "yucekuponsatis", "kodevrenii", "kuponyaticaret"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for g in test_groups:
        print(f"\n{'='*20} @{g} {'='*20}")
        try:
            ent = await client.get_entity(g)
            # Fetch last 30 messages
            msgs = await client.get_messages(ent, limit=30)
            found_us = False
            for m in msgs:
                txt = m.raw_text or ""
                sender = getattr(m.sender, 'first_name', '')
                username = getattr(m.sender, 'username', '')
                # Check if it's KeyVadi, Froxy, or mentions our bots
                if any(k in txt.lower() for k in ["keyvadi", "froxy", "keyvadisatisbot", "froxydestekbot"]) or any(k in (username or "").lower() for k in ["keyvadi", "froxy"]):
                    found_us = True
                    print(f"  ✅ BİZİM MESAJ BULUNDU! ({sender} @{username} - Tarih: {m.date})")
                    print(f"     Metin: {txt[:80]}...")
            if not found_us:
                print(f"  ❌ Son 30 mesaj içinde bizim reklamımız YOK (silinmiş veya çok geride kalmış)!")
        except Exception as e:
            print(f"  Hata: {e}")
        await asyncio.sleep(0.5)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
