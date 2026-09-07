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

with open("gruplar.txt", "r", encoding="utf-8") as f:
    existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}

channels = [
    "enesozen", "firsatdedektifi", "onual_firsat", "firsatavcilari",
    "firsatci", "indirim_habercisi", "kampanyabul", "sicakfirsatlar_tr",
    "kuponcu", "indirimcik", "firsatvadisi", "trendyol_firsat",
    "hepsiburada_firsatlari", "yemeksepeti_firsatlari", "migros_kampanyalari"
]

more_groups = []

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for ch in channels:
        try:
            entity = await client.get_entity(ch)
            full = await client(GetFullChannelRequest(entity))
            
            # Check linked chat
            linked_id = full.full_chat.linked_chat_id
            if linked_id:
                lg = await client.get_entity(linked_id)
                if isinstance(lg, Channel) and lg.megagroup and lg.username:
                    u = lg.username.lower()
                    if u not in existing_groups:
                        banned = lg.default_banned_rights
                        if not (banned and banned.send_messages):
                            more_groups.append({
                                "username": lg.username,
                                "title": lg.title,
                                "members": getattr(lg, 'participants_count', 0)
                            })
                            print(f"  ✨ Found linked: @{lg.username} | {lg.title}")

            # Also check bio/about text for t.me/ links
            about = full.full_chat.about or ""
            usernames = re.findall(r'@([a-zA-Z0-9_]{5,32})', about)
            for u in usernames:
                if u.lower() not in existing_groups and "bot" not in u.lower():
                    try:
                        ent = await client.get_entity(u)
                        if isinstance(ent, Channel) and ent.megagroup:
                            banned = ent.default_banned_rights
                            if not (banned and banned.send_messages):
                                more_groups.append({
                                    "username": ent.username,
                                    "title": ent.title,
                                    "members": getattr(ent, 'participants_count', 0)
                                })
                                print(f"  ✨ Found from bio: @{ent.username} | {ent.title}")
                    except Exception:
                        pass
        except Exception:
            pass
        await asyncio.sleep(1)

    await client.disconnect()

    print(f"Total additional deal groups found: {len(more_groups)}")
    with open("more_deal_groups.json", "w", encoding="utf-8") as f:
        json.dump(more_groups, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
