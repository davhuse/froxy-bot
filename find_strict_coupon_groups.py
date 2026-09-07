import asyncio
import json
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

# Highly specific coupon/çek/indirim queries
coupon_queries = [
    "çek sat",
    "çek alım satım",
    "kupon alım satım",
    "kupon satış",
    "indirim kupon",
    "indirim kodu",
    "yemeksepeti kupon",
    "getir kupon",
    "migros çek",
    "kupon kod",
    "çek takas",
    "sıcak fırsat",
    "fırsat kupon",
    "indirim çek",
    "kupon merkezi",
    "kupon pazarı",
    "çek kupon",
    "indirim kulübü",
    "kampanya kupon",
    "indirim fırsat"
]

discovered = {}

# Required positive keywords in title or username
REQUIRED_TERMS = ["kupon", "çek", "cek", "indirim", "kod", "fırsat", "firsat", "kampanya", "yemeksepeti", "getir", "migros"]

# Negative keywords
FORBIDDEN_TERMS = [
    "pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto",
    "kripto", "crypto", "forex", "escort", "kumar", "bahis", "gay",
    "nargile", "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sikiş", "sex", "karı", "kız", "rus", "çocuk"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Telegram auth failed")
        return

    print("Searching for STRICT coupon, voucher & discount groups only...")

    for q in coupon_queries:
        try:
            res = await client(SearchRequest(q=q, limit=50))
            for chat in res.chats:
                if not (isinstance(chat, Channel) and chat.megagroup):
                    continue
                
                uname = chat.username
                if not uname:
                    continue
                uname_lower = uname.lower()
                title_lower = (chat.title or "").lower()

                if uname_lower in blacklist or uname_lower in existing_groups:
                    continue
                if uname_lower in discovered:
                    continue

                # Must contain at least one required coupon term
                if not any(term in uname_lower or term in title_lower for term in REQUIRED_TERMS):
                    continue

                # Must not contain any forbidden terms
                if any(term in uname_lower or term in title_lower for term in FORBIDDEN_TERMS):
                    continue

                # Check write permissions
                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 100:  # Active coupon groups can be niche (100+ members)
                    continue

                discovered[uname_lower] = {
                    "username": uname,
                    "title": chat.title,
                    "members": members,
                    "matched_query": q
                }
                print(f"  🎯 Found: @{uname:<22} | {members:<5} üye | {chat.title}")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error for '{q}': {e}")
            await asyncio.sleep(3)

    # 2. Also inspect recent messages in our existing groups to find mentioned coupon groups (@...)
    print("\nScanning existing joined coupon groups for mentioned sibling groups...")
    for grp in list(existing_groups)[:20]:
        try:
            entity = await client.get_entity(grp)
            async for msg in client.iter_messages(entity, limit=30):
                if not msg.text:
                    continue
                # Extract @mentions
                mentions = re.findall(r'@([a-zA-Z0-9_]{4,32})', msg.text)
                for m in mentions:
                    m_lower = m.lower()
                    if m_lower in blacklist or m_lower in existing_groups or m_lower in discovered:
                        continue
                    if any(term in m_lower for term in REQUIRED_TERMS) and not any(term in m_lower for term in FORBIDDEN_TERMS):
                        try:
                            ch = await client.get_entity(m)
                            if isinstance(ch, Channel) and ch.megagroup:
                                banned = ch.default_banned_rights
                                if banned and banned.send_messages:
                                    continue
                                members = getattr(ch, 'participants_count', 0) or 0
                                if members >= 100:
                                    discovered[m_lower] = {
                                        "username": ch.username,
                                        "title": ch.title,
                                        "members": members,
                                        "matched_query": f"Mentioned in @{grp}"
                                    }
                                    print(f"  🌟 Sibling Found: @{ch.username:<22} | {members:<5} üye | {ch.title}")
                        except Exception:
                            pass
            await asyncio.sleep(1)
        except Exception:
            pass

    await client.disconnect()

    sorted_results = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("strict_coupon_candidates.json", "w", encoding="utf-8") as f:
        json.dump(sorted_results, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted! Found {len(sorted_results)} strictly relevant coupon/çek groups.")

if __name__ == "__main__":
    asyncio.run(main())
