import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

SESSION_FILE = "froxy_session_output.txt"
with open(SESSION_FILE, "r", encoding="utf-8") as f:
    SESSION_STRING = f.read().strip()

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    # 1. Inspect Ventaru's full ad text
    res = await client(SearchGlobalRequest(
        q="ventaru",
        filter=InputMessagesFilterEmpty(),
        min_date=None, max_date=None, offset_rate=0,
        offset_peer=InputPeerEmpty(), offset_id=0, limit=10
    ))
    
    if res.messages:
        first_msg = res.messages[0]
        print("=== VENTARU FULL MESSAGE ===")
        print(first_msg.message)
        print("Sender ID:", first_msg.sender_id)
        print("Date:", first_msg.date)
        print("============================")

    # 2. Search other keywords and trader signatures
    queries = [
        "PREMİUM HİZMETLER", "YAPAY ZEKA & EĞİTİM",
        "John Snow", "craig", "snow", "Ferhat", "B47", "Cano", "cano31",
        "UBER", "YemekSepeti", "TIKLA GELSİN", "TOD Süperlig",
        "Turna", "Enuygun", "Migros çek", "Pepsi 2.5", "frebayt"
    ]

    all_trader_chats = {}

    for q in queries:
        try:
            r = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None, max_date=None, offset_rate=0,
                offset_peer=InputPeerEmpty(), offset_id=0, limit=50
            ))
            chat_map = {c.id: c for c in r.chats}
            print(f"Query '{q}': {len(r.messages)} msgs, {len(r.chats)} chats")
            for m in r.messages:
                peer = m.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                chat = chat_map.get(cid)
                if chat:
                    u = getattr(chat, 'username', None)
                    if u:
                        u_l = u.lower()
                        is_mega = getattr(chat, 'megagroup', False)
                        is_broad = getattr(chat, 'broadcast', False)
                        if is_mega and not is_broad:
                            if u_l not in all_trader_chats:
                                all_trader_chats[u_l] = {
                                    "username": u_l,
                                    "title": getattr(chat, 'title', ''),
                                    "matched_queries": set(),
                                    "sample_messages": []
                                }
                            all_trader_chats[u_l]["matched_queries"].add(q)
                            if m.message and len(all_trader_chats[u_l]["sample_messages"]) < 3:
                                all_trader_chats[u_l]["sample_messages"].append(m.message[:100].replace("\n", " "))
            await asyncio.sleep(1.0)
        except Exception as ex:
            print(f"Query '{q}' err: {ex}")

    print(f"\nTOTAL MATCHING TRADER CHATS DISCOVERED: {len(all_trader_chats)}")
    
    # Save results
    serializable = {}
    for k, v in all_trader_chats.items():
        serializable[k] = {
            "username": v["username"],
            "title": v["title"],
            "matched_queries": list(v["matched_queries"]),
            "sample_messages": v["sample_messages"]
        }
        
    with open("all_trader_active_groups.json", "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print("Saved to all_trader_active_groups.json")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
