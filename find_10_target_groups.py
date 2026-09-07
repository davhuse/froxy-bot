import asyncio
import json
import re
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

# Turkish Coupon & Digital Market Search Queries
queries = [
    "kupon kod", "kod kupon", "çek satış", "kupon satış", "indirim kodu",
    "yemeksepeti kupon", "getir kupon", "migros çek", "hediye çeki",
    "hesap satış", "lisans satış", "dijital pazar", "kupon alım satım",
    "kod alım satım", "fırsat köşesi", "sıcak fırsatlar", "kupon borsası",
    "kupon dünyası", "indirim marketi", "çek satışı", "hesap marketi",
    "dijital ürün satış", "kupon pazarı", "kampanya kupon", "çek kod ilan"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara"
]

AD_WORDS = ["satılır", "satilir", "alınır", "alinir", "fiyat", "stok", "dm", "tl", "kupon", "hesap", "kod", "çek", "cek", "hesabı", "hesabi", "indirim", "fırsat", "kampanya"]

found_groups = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Auth failed for session_7384!")
        return

    me = await client.get_me()
    print(f"Searching using helper account: {me.first_name} (@{me.username})")

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

                if u_low in blacklist or u_low in existing_groups or u_low in found_groups:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                # Check write permissions
                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 70:
                    continue

                # Check recent 10 messages for user activity
                try:
                    msgs = await client.get_messages(chat, limit=10)
                    if not msgs:
                        continue
                    
                    has_ads = False
                    for m in msgs:
                        txt = (m.raw_text or "").lower()
                        if any(w in txt for w in AD_WORDS):
                            has_ads = True
                            break

                    if has_ads:
                        found_groups[u_low] = {
                            "username": uname,
                            "title": chat.title,
                            "members": members,
                            "matched_query": q
                        }
                        print(f"  🎯 BULUNDU: @{uname:<22} | {members:<5} üye | {chat.title}")
                except Exception:
                    pass
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error for query '{q}': {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_groups = sorted(found_groups.values(), key=lambda x: x["members"], reverse=True)
    with open("new_10_target_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_groups, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_groups)} adet kaliteli hedef grup bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
