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

# Precise voucher/coupon queries observed in actual target group messages
exact_coupon_queries = [
    "turna kod", "turna kupon", "turna bilet", "enuygun kod", "enuygun kupon",
    "yemeksepeti kupon alım", "yemeksepeti kod alım", "yemeksepeti hesap",
    "frebayt", "freebyte", "daha daha kod", "dahadaha", "kazandrio kod",
    "cips şeridi kod", "uber kod", "uber indirim", "migros yemek kupon",
    "tıkla gelsin kod", "tikla gelsin", "alt limitsiz kod", "altlimitsiz kod",
    "tod tv kod", "exxen kod", "fast track kod", "havaist kod"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara"
]

discovered_groups = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in exact_coupon_queries:
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

                if u_low in blacklist or u_low in existing_groups or u_low in discovered_groups:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                # Check write permissions
                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 50:
                    continue

                # Inspect recent messages to ensure users are active and trading
                try:
                    msgs = await client.get_messages(chat, limit=8)
                    if not msgs or len(msgs) < 2:
                        continue

                    # Must have recent messages
                    last_date = str(msgs[0].date)[:10]
                    sample = msgs[0].raw_text.replace('\n', ' ')[:90] if msgs[0].raw_text else ""

                    discovered_groups[u_low] = {
                        "username": uname,
                        "title": chat.title,
                        "members": members,
                        "last_active": last_date,
                        "sample": sample,
                        "matched_query": q
                    }
                    print(f"  🎟️ EŞLEŞTİ: @{uname:<22} | {members:<5} üye | Son: {last_date} | {chat.title}")
                    print(f"     Örnek: {sample[:70]}...")
                except Exception:
                    pass
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error {q}: {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_res = sorted(discovered_groups.values(), key=lambda x: x["members"], reverse=True)
    with open("exact_deal_voucher_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_res, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_res)} adet birebir kupon/çek/kod ekosistemine ait grup bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
