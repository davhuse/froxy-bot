import asyncio
import json
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import CheckChatInviteRequest
from telethon.tl.types import ChatInvite, ChatInviteAlready

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

sample_targets = [
    "kuponsatisgrup", "kuponhesapsatis", "kuponkodindirimilanlar",
    "kodceksatismerkezi", "kuponkodalimsatimm", "ceksatkupon",
    "kuponindirimpazari", "kuponkodalimsatim", "KodKuponMerkezi",
    "indirimcek", "kuponceking", "yucekuponsatis", "satcek", "ceksat",
    "ticaretcanavari", "kuponvekodsatisgrubu", "kuponindirimkodalisveris",
    "alisverisforumuguncel"
]

invite_hashes = set()

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    print("=== Extracting Private Invite Links (t.me/+...) from Target Groups ===")
    for g in sample_targets:
        try:
            ent = await client.get_entity(g)
            msgs = await client.get_messages(ent, limit=120)
            for m in msgs:
                txt = m.raw_text or ""
                if not txt:
                    continue
                # Match t.me/+... and t.me/joinchat/...
                for h in re.findall(r't\.me/\+([a-zA-Z0-9_-]+)', txt):
                    invite_hashes.add(h)
                for h in re.findall(r't\.me/joinchat/([a-zA-Z0-9_-]+)', txt):
                    invite_hashes.add(h)
        except Exception:
            pass

    print(f"Total unique invite hashes extracted: {len(invite_hashes)}")

    verified_invites = []
    for h in list(invite_hashes):
        try:
            res = await client(CheckChatInviteRequest(hash=h))
            if isinstance(res, ChatInvite):
                title = res.title
                members = res.participants_count
                is_megagroup = res.megagroup
                
                # Check title for kupon / kod / çek / indirim / yemeksepeti
                t_low = title.lower()
                if any(k in t_low for k in ["kupon", "kod", "çek", "cek", "indirim", "fırsat", "yemek", "market", "pazar", "ticaret"]):
                    if not any(bad in t_low for bad in ["bahis", "kumar", "casino", "iddaa", "escort", "kripto"]):
                        verified_invites.append({
                            "link": f"https://t.me/+{h}",
                            "title": title,
                            "members": members,
                            "is_megagroup": is_megagroup
                        })
                        print(f"  🎟️ ÖZEL TİCARET GRUBU: {title} | {members} üye | https://t.me/+{h}")
            elif isinstance(res, ChatInviteAlready):
                chat = res.chat
                print(f"  Already in: {chat.title}")
        except Exception as e:
            pass
        await asyncio.sleep(1)

    await client.disconnect()

    with open("extracted_private_coupon_groups.json", "w", encoding="utf-8") as f:
        json.dump(verified_invites, f, indent=2, ensure_ascii=False)

    print(f"\nToplam doğrulanan özel kupon grubu: {len(verified_invites)}")

if __name__ == "__main__":
    asyncio.run(main())
