import asyncio
import json
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, ChatBannedRights

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

with open("session_key_output.txt", "r", encoding="utf-8") as f:
    session_str = f.read().strip()

# Load blacklists and existing groups
with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = {line.strip().lower() for line in f if line.strip()}

existing_groups = set()
try:
    import otomatik_katil
    existing_groups = {g.lower().replace("@", "") for g in getattr(otomatik_katil, "gruplar", [])}
except Exception:
    pass

keywords = [
    "kupon satış", "kod alım satım", "hesap satış", "dijital ürün",
    "lisans satış", "al sat pazar", "ticaret grubu", "epin satış",
    "oyun hesap satış", "trendyol kupon", "yemeksepeti kupon",
    "sosyal medya satış", "sanal ticaret", "premium hesap"
]

discovered = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Telegram auth failed!")
        return

    print("Connected to Telegram! Searching for active groups across keywords...")

    for kw in keywords:
        print(f"Searching: '{kw}'...")
        try:
            result = await client(SearchRequest(q=kw, limit=30))
            for chat in result.chats:
                if isinstance(chat, Channel) and chat.megagroup:
                    username = chat.username
                    if not username:
                        continue
                    uname_clean = username.lower()
                    
                    # Skip if already existing or blacklisted
                    if uname_clean in blacklist or uname_clean in existing_groups:
                        continue
                    if uname_clean in discovered:
                        continue

                    # Check permissions: can regular members send messages?
                    banned_rights = getattr(chat, 'default_banned_rights', None)
                    if banned_rights and getattr(banned_rights, 'send_messages', False):
                        # Members cannot send messages
                        continue

                    members = getattr(chat, 'participants_count', 0) or 0
                    title = chat.title or ""

                    # We want active groups with at least 250 members
                    if members >= 250:
                        discovered[uname_clean] = {
                            "username": username,
                            "title": title,
                            "members": members,
                            "keyword": kw
                        }
                        print(f"  ✨ Found: @{username} | {title} | {members} members")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error searching '{kw}': {e}")
            await asyncio.sleep(3)

    await client.disconnect()

    print(f"\nTotal new candidate groups discovered: {len(discovered)}")
    
    # Sort by member count descending
    sorted_groups = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("candidate_groups_found.json", "w", encoding="utf-8") as f:
        json.dump(sorted_groups, f, indent=2, ensure_ascii=False)
    
    print("Saved to candidate_groups_found.json")

if __name__ == "__main__":
    asyncio.run(main())
