import asyncio
import json
import os
import re
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

def get_known():
    known = set()
    files = ["known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt"]
    for fn in files:
        if os.path.exists(fn):
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.search(r"([a-z0-9_]{4,32})", line.strip().lower())
                    if m:
                        known.add(m.group(1).lower())
    return known

EXACT_SEEDS = [
    "kuponyaticaret", "cek_kupon_kod_ilan", "kodalimsatim", "kuponalsatgurup",
    "Minakuponkodsatis", "herkesibeklerimm", "bedavainternetkodalimsatim",
    "kuponkodmerkez", "KodKuponMerkezi", "ceksatp8", "YemekSepetiKuponu"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları"
]

async def harvest():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known = get_known()
    raw_candidates = set()
    
    print("[*] Seed grupların son 250 mesajındaki satıcıların referans/grup linkleri taranıyor...")
    for seed in EXACT_SEEDS:
        try:
            entity = await client.get_entity(seed)
            messages = await client.get_messages(entity, limit=250)
            for msg in messages:
                if msg and msg.text:
                    # Match t.me links
                    for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", msg.text):
                        u = m.group(1).lower()
                        if u not in known and u not in EXACT_SEEDS and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                            raw_candidates.add(u)
        except Exception as e:
            print(f"Hata ({seed}): {e}")
            
    print(f"[*] Toplam bulunan aday link sayısı: {len(raw_candidates)}")
    
    approved = []
    for idx, u in enumerate(sorted(list(raw_candidates)), 1):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            full_chat = full.full_chat
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            
            if getattr(entity, 'broadcast', False) or not is_megagroup or members < 50:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(entity, limit=25)
            if not messages:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 10 and len(set(senders)) <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.25:
                continue
                
            hits = [k for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim", "kapak", "cips", "turna", "bilet", "tod", "gb", "internet", "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "alınır", "hesap", "lisans"] if k in combined_msgs + combined]
            if not hits:
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "hesap"]):
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
        await asyncio.sleep(0.4)
        
    await client.disconnect()
    
    approved.sort(key=lambda x: x["members"], reverse=True)
    with open("harvested_trade_groups.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Toplam Onaylanan Kardeş Ticaret Grubu: {len(approved)}")

if __name__ == '__main__':
    asyncio.run(harvest())
