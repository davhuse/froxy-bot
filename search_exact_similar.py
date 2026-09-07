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

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

# KeyVadi-specific blocks
try:
    with open("account_group_blocks.json", "r", encoding="utf-8") as f:
        blocks = json.load(f)
        for g, d in blocks.items():
            if "KeyVadiOnline" in d:
                blacklist.add(g.lower())
except Exception:
    pass

queries = [
    "yemeksepeti", "yemeksepeti kupon", "yemeksepeti hesap",
    "migros çek", "migros indirim", "getir kupon",
    "hediye çeki", "indirim çeki", "alışveriş çeki",
    "fırsat kupon", "kupon al sat", "kupon takas",
    "çek alım", "çek satış", "kupon pazarı", "indirim kodu alım",
    "bedava internet", "gb kupon", "kod çek alım", "sıcak fırsat",
    "kupon paylaşım", "indirim dünyası", "fırsat dünyası"
]

# We MUST match coupon/discount/voucher/food themes ONLY
STRICT_KEYWORDS = [
    "kupon", "çek", "cek", "indirim", "fırsat", "firsat",
    "yemeksepeti", "migros", "getir", "trendyol", "kod",
    "hediye", "promosyon", "kampanya", "alışveriş", "alisveris"
]

FORBIDDEN_KEYWORDS = [
    "pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "cc", "panel"
]

discovered = {}

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

                if u_low in blacklist or u_low in existing_groups or u_low in discovered:
                    continue

                if not any(k in u_low or k in t_low for k in STRICT_KEYWORDS):
                    continue

                if any(k in u_low or k in t_low for k in FORBIDDEN_KEYWORDS):
                    continue

                # Fetch full chat to check writing rights and slowmode
                try:
                    full = await client(GetFullChannelRequest(chat))
                    banned = chat.default_banned_rights
                    if banned and banned.send_messages:
                        continue
                    
                    members = full.full_chat.participants_count or 0
                    if members < 80:
                        continue

                    discovered[u_low] = {
                        "username": uname,
                        "title": chat.title,
                        "members": members,
                        "query": q
                    }
                    print(f"  🎯 Eşleşti: @{uname:<22} | Üye: {members:<5} | Başlık: {chat.title}")
                except Exception:
                    pass
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"Hata ({q}): {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_list = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("exact_similar_coupon_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_list, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_list)} adet hedef listemizle birebir uyumlu kupon grubu bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
