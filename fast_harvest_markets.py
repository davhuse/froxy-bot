import asyncio
import json
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

FORBIDDEN = [
    "pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto",
    "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile",
    "tiktok", "instagram", "takipçi", "takipci", "dizi", "film",
    "porn", "sex", "karı", "sahte", "para"
]

AD_WORDS = ["satılır", "satilir", "alınır", "alinir", "fiyat", "stok", "dm", "tl", "kupon", "hesap", "kod", "çek", "cek"]

top_hubs = [
    "kupongrupta", "kuponsatisgrup", "kuponhesapsatis", "kuponkodalimsatimm",
    "kuponceking", "kodceksatismerkezi", "alisverisforumuguncel", "ceksatkupon",
    "kodkuponmarketi", "kuponkodindirimilanlar", "kuponsatislari0", "indirimkodusatis"
]

candidate_usernames = set()
verified_markets = []

async def test_and_verify_candidate(client, uname):
    u_clean = uname.lower().lstrip('@')
    if u_clean in blacklist or u_clean in existing_groups:
        return None

    try:
        entity = await client.get_entity(uname)
        if not (isinstance(entity, Channel) and entity.megagroup):
            return None
        
        t_low = (entity.title or "").lower()
        if any(bad in u_clean or bad in t_low for bad in FORBIDDEN):
            return None

        banned = entity.default_banned_rights
        if banned and banned.send_messages:
            return None

        full = await client(GetFullChannelRequest(entity))
        members = full.full_chat.participants_count or 0
        if members < 80:
            return None

        msgs = await client.get_messages(entity, limit=15)
        if not msgs or len(msgs) < 3:
            return None

        ad_msg_count = 0
        senders = set()
        sample = ""

        for m in msgs:
            text = (m.raw_text or "").lower()
            if not text:
                continue
            if m.sender_id:
                senders.add(m.sender_id)

            if any(w in text for w in AD_WORDS):
                ad_msg_count += 1
                if not sample and len(m.raw_text) > 15:
                    sample = m.raw_text.replace('\n', ' ')[:90]

        if ad_msg_count >= 2 and len(senders) >= 2:
            return {
                "username": entity.username or u_clean,
                "title": entity.title,
                "members": members,
                "sample_ad": sample
            }
    except Exception:
        pass
    return None

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    print("=== Scanning Hub Groups for Cross-Promoted Trading Groups ===")
    for hub in top_hubs:
        try:
            ent = await client.get_entity(hub)
            msgs = await client.get_messages(ent, limit=50)
            for m in msgs:
                if m.fwd_from and m.fwd_from.from_id:
                    try:
                        f_ent = await client.get_entity(m.fwd_from.from_id)
                        if isinstance(f_ent, Channel) and getattr(f_ent, 'username', None):
                            candidate_usernames.add(f_ent.username)
                    except Exception:
                        pass
                if m.text:
                    for u in re.findall(r'@([a-zA-Z0-9_]{5,32})', m.text):
                        if "bot" not in u.lower():
                            candidate_usernames.add(u)
                    for l in re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', m.text):
                        if "bot" not in l.lower() and not l.startswith('+') and l != "joinchat":
                            candidate_usernames.add(l)
            print(f"  Scanned hub @{hub} -> Total unique harvested so far: {len(candidate_usernames)}")
        except Exception as e:
            print(f"  Error on hub @{hub}: {e}")
        await asyncio.sleep(0.5)

    print(f"\nChecking {len(candidate_usernames)} candidates...")
    for u in list(candidate_usernames):
        res = await test_and_verify_candidate(client, u)
        if res:
            verified_markets.append(res)
            print(f"  🛒 ONAYLANDI: @{res['username']:<22} | Üye: {res['members']:<5} | {res['title']}")
            print(f"     Örnek: {res['sample_ad'][:75]}...")
        await asyncio.sleep(0.5)

    await client.disconnect()

    sorted_res = sorted(verified_markets, key=lambda x: x["members"], reverse=True)
    with open("fast_harvested_markets.json", "w", encoding="utf-8") as f:
        json.dump(sorted_res, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted! Found {len(sorted_res)} classifieds groups.")

if __name__ == "__main__":
    asyncio.run(main())
