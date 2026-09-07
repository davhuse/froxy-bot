import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

queries = [
    "kupon platformu", "kod platformu", "çek platformu",
    "kupon & kod", "kod & kupon", "çek & kupon",
    "kupon dünyası", "kod dünyası", "çek dünyası",
    "kupon vadisi", "kod vadisi", "çek vadisi",
    "kupon borsası", "kod borsası", "çek borsası",
    "kupon merkezi", "kod merkezi", "çek merkezi",
    "kupon pazarı", "kod pazarı", "çek pazarı",
    "kupon marketi", "kod marketi", "çek marketi",
    "kupon satış platformu", "kod satış platformu",
    "indirim kuponu satış", "yemeksepeti kupon satış"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara"
]

HIGH_VALUE_ECOSYSTEM = [
    "yemeksepeti", "turna", "migros", "enuygun", "uber", "frebayt",
    "freebyte", "daha daha", "kazandrio", "kazandırio", "şerit",
    "tod tv", "s sport", "canva", "chatgpt", "espressolab", "fast track",
    "tıkla gelsin", "indirim", "kupon", "çek", "kod"
]

found_quality_groups = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in queries:
        try:
            res = await client(SearchRequest(q=q, limit=40))
            for chat in res.chats:
                if not (isinstance(chat, Channel) and chat.megagroup):
                    continue
                uname = chat.username
                if not uname:
                    continue
                u_low = uname.lower()
                t_low = (chat.title or "").lower()

                if u_low in blacklist or u_low in existing_groups or u_low in found_quality_groups:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                full = await client(GetFullChannelRequest(chat))
                members = getattr(full.full_chat, 'participants_count', 0)
                if members < 80:
                    continue

                # Check recent 5 messages
                msgs = await client.get_messages(chat, limit=5)
                if not msgs:
                    continue

                # Check last message date
                last_date = str(msgs[0].date)[:10]
                if not last_date.startswith("2026"):
                    continue

                # Count authentic commerce markers
                hits = 0
                sample = ""
                for m in msgs:
                    txt = (m.raw_text or "").lower()
                    if any(w in txt for w in HIGH_VALUE_ECOSYSTEM):
                        hits += 1
                        if not sample and len(m.raw_text) > 15:
                            sample = m.raw_text.replace('\n', ' ')[:85]

                if hits >= 2:
                    found_quality_groups[u_low] = {
                        "username": uname,
                        "title": chat.title,
                        "members": members,
                        "last_active": last_date,
                        "sample": sample
                    }
                    print(f"\n🔥 GERÇEK PAZAR BULUNDU: @{uname:<22} | {members:<5} üye | Son: {last_date} | {chat.title}")
                    print(f"   💬 {sample[:75]}...")
            await asyncio.sleep(1)
        except Exception:
            pass

    await client.disconnect()

    with open("new_authentic_coupon_markets.json", "w", encoding="utf-8") as f:
        json.dump(list(found_quality_groups.values()), f, indent=2, ensure_ascii=False)

    print(f"\nToplam bulunan: {len(found_quality_groups)}")

if __name__ == "__main__":
    asyncio.run(main())
