import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

def get_blacklist():
    bl = set()
    files = [
        "gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "blacklist.txt",
        "master_known_blacklist.json"
    ]
    for fn in files:
        if os.path.exists(fn):
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for m in re.finditer(r"([a-z0-9_]{4,32})", line.lower()):
                        bl.add(m.group(1).lower())
    return bl

EXPAND_SEEDS = ["kinseimedyaticaret", "dijitalticaretgrubu", "aTicaret", "mailalimsatimticaret"]

async def expand():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    bl = get_blacklist()
    candidates = set()
    
    for seed in EXPAND_SEEDS:
        try:
            entity = await client.get_entity(seed)
            msgs = await client.get_messages(entity, limit=350)
            for m in msgs:
                if m and m.text:
                    for found in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                        u = found.group(1).lower()
                        if u not in bl and u not in EXPAND_SEEDS and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                            candidates.add(u)
        except Exception:
            pass
            
    print(f"[*] Aday sayısı: {len(candidates)}")
    
    approved = []
    now = datetime.now(timezone.utc)
    
    for u in sorted(list(candidates)):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            full_chat = full.full_chat
            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_mega = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            is_broad = getattr(entity, 'broadcast', False)
            
            if is_broad or not is_mega or members < 60:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in ["brawl", "pes", "roblox", "pubg", "koleksiyon", "iddaa", "bahis", "casino"]):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(entity, limit=30)
            if not messages:
                continue
                
            latest = messages[0]
            if not latest or not latest.date:
                continue
                
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_h = (now - msg_d).total_seconds() / 3600.0
            if age_h > 48.0:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            if len(messages) >= 12 and unique_senders < 6:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "hesap"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "unique_senders": unique_senders,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"💎 ONAYLANDI: @{u:22s} | {title[:28]} | {members} üye")
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    with open("expanded_pure_trade_groups.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    asyncio.run(expand())
