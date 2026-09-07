import asyncio
import re
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
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

sellers = [
    "Welattr", "Kayarct", "yemeksepeti0", "Migroskupon1", "boquet0",
    "Muhammed_ctn01", "beytullahkabakci", "UberTaksi500TLindirim",
    "utkualper", "uberuber2", "emre7caponee", "hesapliye", "sfpnto",
    "AuraDijital", "Karam_67o", "emirkaya63", "ecitah33", "Kaiserberkk",
    "yemekfirsati", "Beyza127", "berkk1"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    extracted_links = set()

    print("=== Scanning Bios of Top Sellers from @kodevrenii ===")
    for u in sellers:
        try:
            full = await client(GetFullUserRequest(u))
            about = full.full_user.about or ""
            print(f"@{u:<22} | Bio: {about}")
            for match in re.findall(r'@([a-zA-Z0-9_]{5,32})', about):
                extracted_links.add(match.lower())
            for match in re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', about):
                extracted_links.add(match.lower())
        except Exception as e:
            pass
        await asyncio.sleep(0.5)

    print(f"\nExtracted handles from bios: {extracted_links}")

    # Now verify if any of them are public supergroups where members can send messages!
    for target in list(extracted_links):
        if target in blacklist or target in existing_groups:
            continue
        try:
            ent = await client.get_entity(target)
            if isinstance(ent, Channel) and ent.megagroup:
                banned = ent.default_banned_rights
                can_send = not (banned and banned.send_messages)
                full = await client(GetFullChannelRequest(ent))
                members = getattr(full.full_chat, 'participants_count', 0)
                print(f"\n🎯 BULUNDU (SATICI BİYOSUNDAN GRUP): @{target} | Üye: {members} | Yazma: {can_send} | {ent.title}")
                msgs = await client.get_messages(ent, limit=3)
                for m in msgs:
                    if m.raw_text:
                        print(f"   - {m.raw_text.replace(chr(10), ' ')[:80]}")
        except Exception:
            pass
        await asyncio.sleep(0.5)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
