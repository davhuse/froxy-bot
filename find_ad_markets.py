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
    "kupon ilan", "kod ilan", "çek ilan", "kupon satış", "kod satış",
    "çek satış", "kupon pazar", "kod pazar", "çek pazar", "kupon al sat",
    "kod al sat", "çek al sat", "kupon alım satım", "kod alım satım",
    "çek alım satım", "indirim ilan", "fırsat ilan", "kupon borsa",
    "hesap kupon", "yemeksepeti ilan"
]

# Patterns that indicate regular users posting sales ads
AD_PATTERNS = [
    r'\bsatılır\b', r'\bsatilir\b', r'\balınır\b', r'\balinir\b',
    r'\bfiyat\b', r'\bstok\b', r'\bdm\b', r'\bdetay\b', r'\baktif\b',
    r'\btl\b', r'\bhesap\b', r'\bkupon\b', r'\bkod\b', r'\bçek\b', r'\bcek\b'
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para"
]

market_groups = {}

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

                if u_low in blacklist or u_low in existing_groups or u_low in market_groups:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                # Banned rights check
                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 50:
                    continue

                # INSPECT RECENT MESSAGES: Are users posting ads / listings?
                try:
                    msgs = await client.get_messages(chat, limit=15)
                    if not msgs or len(msgs) < 3:
                        continue

                    ad_msg_count = 0
                    different_senders = set()
                    sample_ad = ""

                    for m in msgs:
                        text = (m.raw_text or "").lower()
                        if not text:
                            continue
                        sender_id = m.sender_id
                        if sender_id:
                            different_senders.add(sender_id)

                        # Check if message looks like a sales/trade ad
                        matches = sum(1 for p in AD_PATTERNS if re.search(p, text))
                        if matches >= 2:
                            ad_msg_count += 1
                            if not sample_ad and len(m.raw_text) > 20:
                                sample_ad = m.raw_text.replace('\n', ' ')[:100]

                    # If multiple different users are posting classified sales messages:
                    if ad_msg_count >= 3 and len(different_senders) >= 2:
                        market_groups[u_low] = {
                            "username": uname,
                            "title": chat.title,
                            "members": members,
                            "ad_count_in_last_15": ad_msg_count,
                            "sample_ad": sample_ad
                        }
                        print(f"  🛒 İLAN GRUBU ONAYLANDI: @{uname:<22} | {members:<5} üye | Başlık: {chat.title}")
                        print(f"     Örnek İlan: {sample_ad[:70]}...")
                except Exception:
                    pass
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"Error {q}: {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_res = sorted(market_groups.values(), key=lambda x: x["members"], reverse=True)
    with open("pure_classified_ad_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_res, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_res)} adet üyelerin serbestçe ilan paylaştığı pazar grubu bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
