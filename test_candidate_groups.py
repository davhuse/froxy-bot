import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

CANDIDATES = {
    "sohbet": [
        "turkcesohbetler", "chat_turkiye", "turksohbetgrubu", "sohbetmuhabbettr",
        "turkiyediyalog", "turkcechat", "sohbetodalari", "sohbetzamani",
        "gencliksohbet", "turkcediscussion"
    ],
    "borsa": [
        "kriptosohbet", "kriptoturk", "borsasohbet", "kriptoparatr",
        "kriptoturkiye", "borsatartisma", "coinsohbettr", "kriptotakip"
    ],
    "haber": [
        "teknolojisohbet", "yazilimtoplulugu", "teknolojihaber",
        "turkiyeyazilim", "yazilimcilar", "bilisimsohbet"
    ]
}

async def check():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    results = {}
    for cat, glist in CANDIDATES.items():
        results[cat] = []
        for g in glist:
            try:
                entity = await client.get_entity(g)
                title = getattr(entity, 'title', g)
                print(f"[{cat}] ✅ {g} -> {title}")
                results[cat].append(g)
            except Exception:
                pass
            await asyncio.sleep(0.3)
            
    await client.disconnect()
    print("\nSONUCLAR:")
    for cat, glist in results.items():
        print(f"{cat} ({len(glist)}): {glist}")

if __name__ == "__main__":
    asyncio.run(check())
