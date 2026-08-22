import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

def get_all_known():
    known = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json"
    ]
    for fn in files:
        if not os.path.exists(fn):
            continue
        if fn.endswith(".json"):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        for item in d:
                            if isinstance(item, str):
                                known.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    known.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        known.add(item["username"].lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                known.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip().lstrip("@").lower()
                        m = re.search(r"([a-z0-9_]{4,32})", line)
                        if m:
                            known.add(m.group(1).lower())
            except Exception:
                pass
    return known

EXACT_SEARCH_QUERIES = [
    # Kupon Kod Çek Alım Satım
    "kupon kod alım satım", "kupon kod alim satim", "kupon kod ilan",
    "kupon kod al sat", "kupon kod pazar", "kupon kod borsa",
    "kod kupon alım satım", "çek kod alım satım", "cek kod satis",
    "kupon çek satış", "kod çek satış", "kupon al sat ticaret",
    "dijital kupon alım satım", "dijital kod alım satım", "dijital hesap alım satım",
    "yemeksepeti kupon alım satım", "migros çek alım satım", "turna çek alım satım",
    "indirim kuponu alım satım", "promosyon kod alım satım", "hediye çeki alım satım",
    "internet kod alım satım", "kod pazarı", "kupon pazarı", "çek pazarı",
    "kupon marketi", "kod marketi", "çek marketi", "kupon borsası", "kod borsası"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları",
    "gayrimenkul", "emlak", "ev alım", "oto alım"
]

async def main():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known = get_all_known()
    print(f"[*] Bilinen grup sayısı: {len(known)}")
    
    discovered = {}
    
    print("\n--- 1. Telegram Global Kupon/Kod Alım-Satım Araması ---")
    for q in EXACT_SEARCH_QUERIES:
        try:
            res = await client(SearchRequest(q=q, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in known or getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered:
                    discovered[u_l] = {"username": u, "chat": chat, "query": q}
            await asyncio.sleep(1.2)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    # Inspect seed groups for sibling links
    seed_groups = ["kodalimsatim", "kuponalsatgurup", "kuponkodmerkez", "KodKuponMerkezi", "ceksatp8", "Minakuponkodsatis", "herkesibeklerimm"]
    for seed in seed_groups:
        try:
            entity = await client.get_entity(seed)
            full = await client(GetFullChannelRequest(entity))
            about = getattr(full.full_chat, 'about', '') or ''
            for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", about):
                u = m.group(1).lower()
                if u not in known and u not in seed_groups:
                    if u not in discovered:
                        try:
                            ent = await client.get_entity(u)
                            discovered[u] = {"username": u, "chat": ent, "query": "seed_about"}
                        except Exception:
                            pass
            messages = await client.get_messages(entity, limit=60)
            for msg in messages:
                if msg and msg.text:
                    for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", msg.text):
                        u = m.group(1).lower()
                        if u not in known and u not in seed_groups and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                            if u not in discovered:
                                try:
                                    ent = await client.get_entity(u)
                                    discovered[u] = {"username": u, "chat": ent, "query": "seed_msg"}
                                except Exception:
                                    pass
        except Exception:
            pass

    print(f"\n[*] Toplam incelenecek aday grup sayısı: {len(discovered)}")
    
    approved = []
    for idx, (u_l, item) in enumerate(discovered.items(), 1):
        chat = item["chat"]
        u = item["username"]
        try:
            full = await client(GetFullChannelRequest(chat))
            full_chat = full.full_chat
            title = getattr(chat, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
            
            if getattr(chat, 'broadcast', False) or not is_megagroup or members < 60:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(chat, limit=25)
            if not messages:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 10 and len(set(senders)) <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.25:
                continue
                
            # Must have positive signals
            hits = [k for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim", "kapak", "cips", "turna", "bilet", "tod", "gb", "internet", "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "alınır", "hesap", "lisans"] if k in combined_msgs + combined]
            if not hits:
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 120:
                        clean = clean[:117] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            record = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(record)
            print(f"🎯 ONAYLANDI: @{u:22s} | {title[:28]} | {members} üye")
        except Exception:
            pass
        await asyncio.sleep(0.5)

    await client.disconnect()
    
    approved.sort(key=lambda x: x["members"], reverse=True)
    with open("birebir_yeni_kupon_kod_alimsatim_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Tamamlandı: {len(approved)} yeni grup bulundu.")

if __name__ == '__main__':
    asyncio.run(main())
