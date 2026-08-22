import asyncio
import json
import os
import re
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

TARGET_TRADERS = [
    "ventaru",
    "craigkks",
    "John Snow",
    "ferhatb47",
    "Ferhat B47",
    "cano31m",
    "Cano31m"
]

SEED_GROUPS = [
    "kuponkodalimsatimm", "kuponyaticaret", "wishx_2", "kodkuponmarketi",
    "ceksatkupon2", "Kuponcekm", "kuponceking", "satcek", "ceksat",
    "kuponsat", "alimsatimmerkezii", "ticaretyapn", "letgoilanlari"
]

async def investigate_traders():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Connected as {me.first_name} ({me.id})\n")

    trader_info = {} # name/id -> details
    trader_ids = set()

    # Step 1: Scan seed groups to find exact user IDs and ad texts of these traders
    print("[*] Scanning seed groups to locate trader profiles and message templates...")
    for sg in SEED_GROUPS:
        try:
            entity = await client.get_entity(sg)
            msgs = await client.get_messages(entity, limit=300)
            for m in msgs:
                if not m:
                    continue
                txt = m.text or ""
                # Check sender
                sender = await m.get_sender()
                s_name = ""
                s_uname = ""
                s_id = m.sender_id
                if sender:
                    first = getattr(sender, 'first_name', '') or ''
                    last = getattr(sender, 'last_name', '') or ''
                    s_name = f"{first} {last}".strip()
                    s_uname = getattr(sender, 'username', '') or ''

                combined = f"{s_name} {s_uname} {txt}".lower()
                
                for t in TARGET_TRADERS:
                    if t.lower() in combined:
                        if s_id not in trader_info:
                            trader_info[s_id] = {
                                "name": s_name,
                                "username": s_uname,
                                "id": s_id,
                                "matched_target": t,
                                "sample_text": txt[:140].replace("\n", " "),
                                "groups_found": set()
                            }
                            trader_ids.add(s_id)
                        trader_info[s_id]["groups_found"].add(sg)
                        print(f"  [FOUND TRADER] {t} -> ID: {s_id} | Name: '{s_name}' | @{s_uname} in @{sg}")
                        print(f"    Ad: {txt[:90]}...")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Seed @{sg} err: {e}")

    print(f"\nTotal identified target trader profiles: {len(trader_info)}")
    for tid, tdata in trader_info.items():
        print(f" - {tdata['name']} (@{tdata['username']}) | Target: {tdata['matched_target']} | Groups: {tdata['groups_found']}")

    # Step 2: Run Global Search on Telegram for each trader keyword
    print("\n[*] Running SearchGlobalRequest for trader usernames/names...")
    trader_discovered_groups = {}

    queries = ["craigkks", "ventaru", "ferhatb47", "cano31m", "John Snow", "B47"]
    for q in queries:
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=40
            ))
            chat_map = {c.id: c for c in res.chats}
            print(f"Query '{q}': found {len(res.messages)} messages, {len(res.chats)} chats")
            for m in res.messages:
                peer = m.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                if not cid:
                    continue
                chat = chat_map.get(cid)
                if not chat:
                    continue
                uname = getattr(chat, 'username', None)
                if not uname:
                    continue
                u_l = uname.lower()
                is_mega = getattr(chat, 'megagroup', False)
                is_broad = getattr(chat, 'broadcast', False)
                title = getattr(chat, 'title', '')
                
                if u_l not in trader_discovered_groups:
                    trader_discovered_groups[u_l] = {
                        "username": u_l,
                        "title": title,
                        "is_mega": is_mega,
                        "is_broad": is_broad,
                        "messages": []
                    }
                trader_discovered_groups[u_l]["messages"].append({
                    "date": m.date,
                    "sender_id": m.sender_id,
                    "text": m.message[:120] if m.message else ""
                })
                print(f"    -> Chat @{u_l} (Mega:{is_mega}) | Date: {m.date} | Msg: {m.message[:60] if m.message else ''}")
        except Exception as e:
            print(f"Query '{q}' Error: {e}")
        await asyncio.sleep(1.0)

    print(f"\nTotal groups discovered via trader searches: {len(trader_discovered_groups)}")
    with open("trader_discovered_groups.json", "w", encoding="utf-8") as f:
        json.dump(trader_discovered_groups, f, ensure_ascii=False, indent=2, default=str)
    print("Saved to trader_discovered_groups.json")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(investigate_traders())
