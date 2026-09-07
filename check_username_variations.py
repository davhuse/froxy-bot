import asyncio
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

usernames = [
    "kuponsatisgrubu", "kuponborsasi", "kuponplatformu", "kodplatformu",
    "cekplatformu", "indirimplatformu", "kupondunyasi", "koddunyasi",
    "cekdunyasi", "kuponvadisi", "kodvadisi", "cekvadisi", "firsatvadisi",
    "firsatplatformu", "firsatmerkezi", "kuponalsatyeri", "kodvekuponsatis",
    "kupon_ve_kod_satis", "dijitalkodsatisi", "dijitalkodlar", "kodalimsatimi",
    "kuponalimsatimi", "cekalimsatimi", "yemeksepetikupongrubu", "yemeksepeti_grup",
    "yemeksepeti_kuponlari", "yemeksepetikodlar", "turnakodlari", "uberindirimleri",
    "kuponsatisi", "kuponsatisi1", "kuponsatis1"
]

candidates = []

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for u in usernames:
        if u.lower() in blacklist or u.lower() in existing_groups:
            continue
        try:
            ent = await client.get_entity(u)
            if isinstance(ent, Channel) and ent.megagroup:
                banned = ent.default_banned_rights
                can_send = not (banned and banned.send_messages)
                if can_send:
                    full = await client(GetFullChannelRequest(ent))
                    members = getattr(full.full_chat, 'participants_count', 0)
                    if members >= 80:
                        msgs = await client.get_messages(ent, limit=3)
                        sample = msgs[0].raw_text.replace('\n', ' ')[:75] if msgs and msgs[0].raw_text else ""
                        candidates.append({
                            "username": u,
                            "title": ent.title,
                            "members": members,
                            "sample": sample
                        })
                        print(f"🔥 BULUNDU: @{u:<22} | Üye: {members:<5} | {ent.title}")
                        print(f"   💬 {sample[:65]}...")
        except Exception:
            pass
        await asyncio.sleep(0.3)

    await client.disconnect()
    print(f"\nToplam bulunan: {len(candidates)}")

if __name__ == "__main__":
    asyncio.run(main())
