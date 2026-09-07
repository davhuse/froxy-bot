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

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

turkish_queries = [
    "kupon alım", "kupon satım", "kod alım", "kod satım", "çek alım",
    "çek satım", "kupon takas", "kod takas", "çek takas", "indirim takas",
    "hesap al sat", "lisans al sat", "dijital al sat", "yemeksepeti kuponu",
    "migros hediye", "getir indirim", "ticaret ilanları", "serbest ilan",
    "pazar alım satım", "türkiye dijital", "dijital lisans türkiye"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun hesabı", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara",
    "ethio", "india", "russia", "iran", "arabic", "crypto"
]

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
TURKISH_MARKERS = ["satılık", "satılır", "alınır", "fiyat", "stok", "dm", "tl", "kupon", "hesap", "kod", "çek", "indirim", "fırsat"]

curated_turkish = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in turkish_queries:
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

                if u_low in blacklist or u_low in existing_groups or u_low in curated_turkish:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(chat, 'participants_count', 0) or 0
                if members < 60:
                    continue

                # Inspect recent messages: MUST BE TURKISH
                try:
                    msgs = await client.get_messages(chat, limit=12)
                    if not msgs or len(msgs) < 2:
                        continue

                    turkish_hits = 0
                    sample_txt = ""
                    for m in msgs:
                        txt = (m.raw_text or "").lower()
                        if not txt:
                            continue
                        if any(c in txt for c in TURKISH_CHARS) or any(w in txt for w in TURKISH_MARKERS):
                            turkish_hits += 1
                            if not sample_txt and len(m.raw_text) > 10:
                                sample_txt = m.raw_text.replace('\n', ' ')[:80]

                    # At least 3 messages must match Turkish language & commerce markers
                    if turkish_hits >= 2:
                        curated_turkish[u_low] = {
                            "username": uname,
                            "title": chat.title,
                            "members": members,
                            "sample": sample_txt
                        }
                        print(f"  🇹🇷 TÜRKÇE TİCARET GRUBU: @{uname:<22} | {members:<5} üye | {chat.title}")
                except Exception:
                    pass
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Hata {q}: {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_res = sorted(curated_turkish.values(), key=lambda x: x["members"], reverse=True)
    with open("pure_turkish_curated_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_res, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_res)} adet Türkçe saf ticaret/kupon grubu bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
