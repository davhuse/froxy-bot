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

exact_patterns = [
    "kod evreni", "kupon evreni", "çek evreni", "indirim evreni",
    "kod diyarı", "kupon diyarı", "çek diyarı", "indirim diyarı",
    "kod dünyası", "kupon dünyası", "çek dünyası", "fırsat dünyası",
    "kod pazarı", "kupon pazarı", "çek pazarı", "indirim pazarı",
    "kod vadisi", "kupon vadisi", "çek vadisi", "fırsat vadisi",
    "dijital kod alım satım", "hediye çeki alım satım", "kod alım satım grubu",
    "kupon alım satım grubu", "çek alım satım grubu", "yemeksepeti kupon grubu",
    "kod borsası", "kupon borsası", "çek borsası", "fırsat borsası"
]

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para", "vape", "puff", "sigara"
]

HIGH_VALUE_MARKERS = [
    "yemeksepeti", "turna", "migros", "enuygun", "uber", "frebayt",
    "freebyte", "daha daha", "kazandrio", "kazandırio", "şerit",
    "tod tv", "s sport", "canva", "chatgpt", "espressolab", "fast track"
]

matched_groups = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in exact_patterns:
        try:
            res = await client(SearchRequest(q=q, limit=30))
            for chat in res.chats:
                if not (isinstance(chat, Channel) and chat.megagroup):
                    continue
                uname = chat.username
                if not uname:
                    continue
                u_low = uname.lower()
                t_low = (chat.title or "").lower()

                if u_low in blacklist or u_low in existing_groups or u_low in matched_groups:
                    continue

                if any(bad in u_low or bad in t_low for bad in FORBIDDEN):
                    continue

                banned = chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                full = await client(GetFullChannelRequest(chat))
                members = getattr(full.full_chat, 'participants_count', 0)
                if members < 100:
                    continue

                # Inspect recent 10 messages for REAL coupon/deal ecosystem keywords!
                try:
                    msgs = await client.get_messages(chat, limit=10)
                    if not msgs or len(msgs) < 3:
                        continue

                    # Check how many high-value markers match
                    match_count = 0
                    samples = []
                    for m in msgs:
                        txt = (m.raw_text or "").lower()
                        if any(marker in txt for marker in HIGH_VALUE_MARKERS):
                            match_count += 1
                            if len(samples) < 2 and len(m.raw_text) > 10:
                                samples.append(m.raw_text.replace('\n', ' ')[:75])

                    # IF it contains authentic coupon sellers like Yemeksepeti/Turna/Uber/Data!
                    if match_count >= 2:
                        matched_groups[u_low] = {
                            "username": uname,
                            "title": chat.title,
                            "members": members,
                            "matches": match_count,
                            "samples": samples
                        }
                        print(f"\n🌟 BULUNDU (BİREBİR KOD EVRENİ TİPİ): @{uname:<20} | {members:<5} üye | {chat.title}")
                        for s in samples:
                            print(f"   💬 {s}...")
                except Exception:
                    pass
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error {q}: {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    with open("exact_kodevrenii_twins.json", "w", encoding="utf-8") as f:
        json.dump(list(matched_groups.values()), f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(matched_groups)} adet Kod Evreni ikizi grup bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
