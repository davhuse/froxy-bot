import asyncio
import json
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel

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
    with open("gruplar.txt", "r", encoding="utf-8") as f:
        existing_groups = {line.strip().lower().replace("@", "") for line in f if line.strip()}
except Exception:
    pass

# Load existing candidates if any
discovered = {}
if os.path.exists("candidate_groups_found.json"):
    try:
        with open("candidate_groups_found.json", "r", encoding="utf-8") as f:
            for g in json.load(f):
                discovered[g["username"].lower()] = g
    except Exception:
        pass

more_keywords = [
    "alım satım", "al sat", "pazaryeri", "ilan pazar",
    "kod pazar", "çek satış", "pubg hesap", "valorant hesap",
    "steam hesap", "oyun pazarı", "hesap al sat", "dijital market",
    "dijital pazar", "internet al sat", "freelance pazar",
    "brawl stars alım", "sosyal medya pazar", "eticaret ilan"
]

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Telegram auth failed!")
        return

    print("Searching additional keywords...")

    for kw in more_keywords:
        try:
            result = await client(SearchRequest(q=kw, limit=30))
            for chat in result.chats:
                if isinstance(chat, Channel) and chat.megagroup:
                    username = chat.username
                    if not username:
                        continue
                    uname_clean = username.lower()
                    
                    if uname_clean in blacklist or uname_clean in existing_groups:
                        continue
                    if uname_clean in discovered:
                        continue

                    banned_rights = getattr(chat, 'default_banned_rights', None)
                    if banned_rights and getattr(banned_rights, 'send_messages', False):
                        continue

                    members = getattr(chat, 'participants_count', 0) or 0
                    title = chat.title or ""

                    # Filter out irrelevant groups like car sales, crypto pumps, arabic etc.
                    t_lower = title.lower()
                    if any(bad in t_lower for bad in ["araba", "otomobil", "kripto", "forex", "escort", "kumar", "bahis", "gay"]):
                        continue

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

    sorted_groups = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("candidate_groups_found.json", "w", encoding="utf-8") as f:
        json.dump(sorted_groups, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated total candidates: {len(sorted_groups)}")

if __name__ == "__main__":
    asyncio.run(main())
