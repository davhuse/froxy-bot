import asyncio
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import InputPeerUser

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    with open('froxy_session_output.txt', 'r', encoding='utf-8') as f:
        s_str = f.read().strip()
    client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
    await client.connect()
    
    entity = await client.get_entity("gpt_nocard")
    print(f"Connected to @gpt_nocard")

    # Map sender objects from messages directly
    sender_objs = {}
    async for msg in client.iter_messages(entity, limit=2000):
        if msg.sender and hasattr(msg.sender, 'id'):
            if msg.sender.id not in sender_objs:
                sender_objs[msg.sender.id] = (msg.sender, msg.text or "")

    print(f"Cached {len(sender_objs)} sender objects with access hashes.")

    target_ids = [
        7159009666, 6147897825, 5766391009, 98593196, 5717492220,
        1937854254, 1254768942, 5463698804, 8550016068, 8302418712,
        5027052332, 7645340205, 6133389723, 8763711462, 1215799277,
        7644457363, 7177754708, 1920319975, 5516156034, 5798734190,
        8372488713, 8384878054
    ]

    detailed_results = []

    for uid in target_ids:
        if uid not in sender_objs:
            # try getting input entity
            try:
                user_obj = await client.get_entity(uid)
            except Exception as e:
                print(f"Could not get entity for {uid}: {e}")
                continue
        else:
            user_obj, sample_text = sender_objs[uid]

        name = f"{getattr(user_obj, 'first_name', '') or ''} {getattr(user_obj, 'last_name', '') or ''}".strip()
        username = getattr(user_obj, 'username', '') or ''

        bio = ""
        try:
            full = await client(GetFullUserRequest(user_obj))
            if hasattr(full, 'full_user') and hasattr(full.full_user, 'about'):
                bio = full.full_user.about or ""
            elif hasattr(full, 'about'):
                bio = full.about or ""
        except Exception as e:
            bio = f"[Error: {e}]"

        # Check for payshop links in bio, name, messages
        has_payshop = 'payshop' in bio.lower() or 'payshop' in username.lower() or 'payshop' in name.lower()

        links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9-]+\.(?:top|shop|xyz|com|cn|org|net|me|cc|io|site|vip|store|link)[^\s<>"]*', bio)
        telegram_bots = re.findall(r'@[a-zA-Z0-9_]+', bio)

        detailed_results.append({
            'id': uid,
            'name': name,
            'username': f"@{username}" if username else "Yok",
            'bio': bio,
            'links': links,
            'telegram_bots_in_bio': telegram_bots,
            'has_payshop': has_payshop
        })

        print(f"\n==========================================")
        print(f"Kullanıcı: {name} ({f'@{username}' if username else 'Yok'}) [ID: {uid}]")
        print(f"Biyo (About): {bio}")
        print(f"Linkler: {links}")
        print(f"Botlar / Mentionlar: {telegram_bots}")
        print(f"Payshop Eşleşmesi: {has_payshop}")

    with open('detailed_bio_check.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
