import asyncio
import json
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, ChannelParticipantsAdmins

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

discovered = {}

COUPON_TERMS = ["kupon", "çek", "cek", "indirim", "kod", "fırsat", "firsat", "kampanya", "yemeksepeti", "migros", "getir", "trendyol", "firsatlar", "indirimler", "sicakfirsat"]

FORBIDDEN = ["pubg", "brawl", "pes", "oyun", "game", "etsy", "araba", "oto", "kripto", "forex", "escort", "kumar", "bahis", "gay", "nargile", "tiktok", "instagram", "takipci", "takipçi", "dizi", "film", "porn", "sex", "karı", "sahte", "para"]

async def check_candidate(client, uname_or_entity):
    try:
        entity = await client.get_entity(uname_or_entity)
        if not (isinstance(entity, Channel) and entity.megagroup):
            return None
        uname = entity.username
        if not uname:
            return None
        u_low = uname.lower()
        t_low = (entity.title or "").lower()

        if u_low in blacklist or u_low in existing_groups or u_low in discovered:
            return None

        # Must have coupon keywords in username or title
        if not any(term in u_low or term in t_low for term in COUPON_TERMS):
            return None

        # No forbidden terms
        if any(term in u_low or term in t_low for term in FORBIDDEN):
            return None

        # Check write permissions
        banned = entity.default_banned_rights
        if banned and banned.send_messages:
            return None

        members = getattr(entity, 'participants_count', 0) or 0
        if members < 100:
            return None

        return {
            "username": uname,
            "title": entity.title,
            "members": members
        }
    except Exception:
        return None

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Auth failed")
        return

    print("=== Scanning 1: Deep Message History of All Joined Coupon Groups ===")
    dialogs = await client.get_dialogs(limit=100)
    for d in dialogs:
        if not (d.is_group or d.is_channel):
            continue
        try:
            async for msg in client.iter_messages(d.entity, limit=100):
                if not msg.text:
                    continue
                # 1. Regex find all @usernames
                found_usernames = re.findall(r'@([a-zA-Z0-9_]{5,32})', msg.text)
                # 2. Regex find t.me/ links
                links = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', msg.text)
                candidates_to_check = set(found_usernames + links)

                for c in candidates_to_check:
                    c_low = c.lower()
                    if c_low in blacklist or c_low in existing_groups or c_low in discovered:
                        continue
                    if any(term in c_low for term in COUPON_TERMS) and not any(term in c_low for term in FORBIDDEN):
                        cand = await check_candidate(client, c)
                        if cand:
                            discovered[cand["username"].lower()] = cand
                            print(f"  🔥 Found in history: @{cand['username']:<22} | {cand['members']:<5} üye | {cand['title']}")
        except Exception:
            pass

    print(f"\n=== Scanning 2: Targeted Query Combinations ===")
    combos = [
        "yemeksepeti", "yemeksepeti kupon", "getir indirim", "migros indirim",
        "indirim kulübü", "kupon paylaşım", "fırsat köşesi", "sıcak fırsatlar",
        "kupon vadisi", "çek dünyası", "kupon diyarı", "indirim dünyası",
        "kupon kanalı", "indirim marketi", "çek borsası", "kupon borsası",
        "kod paylaşım", "indirim kuponları", "kampanya kuponları", "fırsat kuponları"
    ]
    for q in combos:
        try:
            res = await client(SearchRequest(q=q, limit=40))
            for chat in res.chats:
                cand = await check_candidate(client, chat)
                if cand:
                    discovered[cand["username"].lower()] = cand
                    print(f"  🎯 Found via search: @{cand['username']:<22} | {cand['members']:<5} üye | {cand['title']}")
            await asyncio.sleep(2)
        except Exception:
            pass

    await client.disconnect()

    sorted_list = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("pure_coupon_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_list, f, indent=2, ensure_ascii=False)

    print(f"\nTotal pure coupon/discount groups found: {len(sorted_list)}")

if __name__ == "__main__":
    asyncio.run(main())
