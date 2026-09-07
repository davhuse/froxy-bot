import asyncio
import json
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import SearchRequest
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

# Shopping & Deal searches
queries = [
    "sıcak fırsat", "sicak firsatlar", "fırsat köşesi", "fırsat ürünleri",
    "alışveriş fırsatları", "indirim kodu paylaşım", "fırsat kulübü",
    "trendyol indirim", "hepsiburada indirim", "amazon fırsatları",
    "indirim avcıları", "fırsat avcıları", "kupon avcıları",
    "çek satışı", "indirim çeki satış", "yemek kuponu"
]

discovered = {}

async def main():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    for q in queries:
        try:
            res = await client(SearchRequest(q=q, limit=30))
            for chat in res.chats:
                is_mg = isinstance(chat, Channel) and chat.megagroup
                is_ch = isinstance(chat, Channel) and chat.broadcast
                
                target_chat = None
                if is_mg:
                    target_chat = chat
                elif is_ch:
                    # Check if channel has a linked discussion group
                    try:
                        full = await client(GetFullChannelRequest(chat))
                        if full.full_chat.linked_chat_id:
                            linked = await client.get_entity(full.full_chat.linked_chat_id)
                            if isinstance(linked, Channel) and linked.megagroup:
                                target_chat = linked
                    except Exception:
                        pass

                if not target_chat:
                    continue

                uname = getattr(target_chat, 'username', None)
                if not uname:
                    continue
                u_low = uname.lower()
                t_low = (target_chat.title or "").lower()

                # Exclude betting/iddaa/games/cars/etc.
                if any(bad in u_low or bad in t_low for bad in [
                    "bahis", "iddaa", "kumar", "casino", "nba", "tips",
                    "pubg", "brawl", "pes", "etsy", "araba", "kripto",
                    "escort", "nargile", "tiktok", "instagram"
                ]):
                    continue

                if u_low in blacklist or u_low in existing_groups or u_low in discovered:
                    continue

                # Check write permissions
                banned = target_chat.default_banned_rights
                if banned and banned.send_messages:
                    continue

                members = getattr(target_chat, 'participants_count', 0) or 0
                if members < 100:
                    continue

                discovered[u_low] = {
                    "username": uname,
                    "title": target_chat.title,
                    "members": members,
                    "matched_query": q
                }
                print(f"  🔥 Bulundu: @{uname:<22} | {members:<5} üye | {target_chat.title}")
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"Hata {q}: {e}")
            await asyncio.sleep(2)

    await client.disconnect()

    sorted_list = sorted(discovered.values(), key=lambda x: x["members"], reverse=True)
    with open("pure_shopping_coupon_groups.json", "w", encoding="utf-8") as f:
        json.dump(sorted_list, f, indent=2, ensure_ascii=False)

    print(f"\nToplam {len(sorted_list)} adet gerçek alışveriş/kupon/fırsat grubu bulundu.")

if __name__ == "__main__":
    asyncio.run(main())
