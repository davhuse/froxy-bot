import asyncio
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
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

sample_targets = [
    "kuponsatisgrup", "kuponhesapsatis", "kuponkodindirimilanlar",
    "kodceksatismerkezi", "kuponkodalimsatimm", "ceksatkupon",
    "kuponindirimpazari", "kuponkodalimsatim", "KodKuponMerkezi",
    "indirimcek", "kuponceking", "yucekuponsatis", "satcek", "ceksat",
    "ticaretcanavari", "kuponvekodsatisgrubu", "kuponindirimkodalisveris",
    "alisverisforumuguncel"
]

discovered_usernames = set()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    print("=== Scanning messages for group/channel links posted by sellers ===")
    for g in sample_targets:
        try:
            ent = await client.get_entity(g)
            msgs = await client.get_messages(ent, limit=80)
            for m in msgs:
                txt = m.raw_text or ""
                if not txt:
                    continue
                # Extract @usernames
                for u in re.findall(r'@([a-zA-Z0-9_]{5,32})', txt):
                    if not any(x in u.lower() for x in ["bot", "shopier", "destek"]):
                        discovered_usernames.add(u.lower())
                # Extract t.me/ links
                for l in re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', txt):
                    if not any(x in l.lower() for x in ["bot", "joinchat", "+"]):
                        discovered_usernames.add(l.lower())
        except Exception:
            pass

    print(f"Total extracted potential targets: {len(discovered_usernames)}")

    # Now verify which ones are supergroups where members can post!
    valid_new_markets = []
    for uname in list(discovered_usernames):
        if uname in existing_groups or uname in blacklist:
            continue
        try:
            ent = await client.get_entity(uname)
            if isinstance(ent, Channel) and ent.megagroup:
                banned = ent.default_banned_rights
                if not (banned and banned.send_messages):
                    full = await client(GetFullChannelRequest(ent))
                    members = getattr(full.full_chat, 'participants_count', 0)
                    if members >= 100:
                        # Check last 5 messages to see if it's the same coupon/turna/uber/yemeksepeti niche!
                        msgs = await client.get_messages(ent, limit=5)
                        sample = msgs[0].raw_text.replace('\n', ' ')[:80] if msgs and msgs[0].raw_text else ""
                        valid_new_markets.append({
                            "username": uname,
                            "title": ent.title,
                            "members": members,
                            "sample": sample
                        })
                        print(f"  💎 BULUNDU: @{uname:<22} | Üye: {members:<5} | {ent.title}")
                        print(f"     Örnek: {sample[:65]}...")
        except Exception:
            pass
        await asyncio.sleep(0.5)

    await client.disconnect()

    print(f"\nToplam bulunan yeni pazar grubu: {len(valid_new_markets)}")

if __name__ == "__main__":
    asyncio.run(main())
