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

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

# Target new candidates discovered from prefix/suffix exploration
TARGETS = [
    "KodDeposuCom", "KodDeposu", "KodVadisi", "koddiyari", "Kodmerkezichat",
    "indirimmerkezininyeri", "indirimmerkezim", "firsatmerkezigrup", "kod_adi_alfa",
    "kuponcular_tr", "kupondeposu_tr", "cekkulubu_tr", "kodalsattr", "kuponalsattr",
    "kodmarketicom", "kuponmarketicom", "cekmarketicom", "kupondukkani", "koddukkani"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet"
]

async def check_targets():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    approved = []
    for u in TARGETS:
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
            
            if is_broad or not is_mega or members < 40:
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
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.20:
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "pepsi", "cips", "yemeksepeti"]):
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
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"🎯 ONAYLANDI: @{u:22s} | {title[:28]} | {members} üye")
        except Exception as e:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    with open("freshly_discovered_niche_groups.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print(f"Toplam onaylanan: {len(approved)}")

if __name__ == '__main__':
    asyncio.run(check_targets())
