import asyncio
import json
import os
import re
import sys
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

with open("master_known_blacklist.json", "r", encoding="utf-8") as f:
    BLACKLIST = set(json.load(f))

# Add results of previous step to blacklist so we don't repeat them
BLACKLIST.update([
    "uluTrader", "kodebonusbinomo", "data_free_internett", "adobe_audition",
    "kodestek", "ghostinstadjdh", "proxy886prox", "HPalsat", "dataverse_city",
    "hesapapara", "datasphereIX", "instagram_tiktok_hesap", "trendyolkampanya5",
    "GoogleAIProPremiumgroup", "KOD_PROMOSYON", "FreepikPremiumA", "darktradehouse"
])

TARGET_PATTERNS = [
    "yemeksepeti", "yemek kupon", "yemek kod", "yemek indirim",
    "migros çek", "migros kod", "migros kupon", "turna uçak", "turna kod",
    "tiklagelsin", "tıkla gelsin", "enuygun", "biletinial", "sinema kupon",
    "tod tv", "exxen", "blutv", "kuponkod", "kodkupon", "cekkod", "kodcek",
    "kuponcu", "indirimcik", "firsatci", "dijitalkod", "hediyekodu",
    "bedavainternet", "frebayt", "dahadaha", "kazandrio"
]

EXCLUDE_TERMS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet"
]

async def find_gems():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    discovered = {}
    for kw in TARGET_PATTERNS:
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in BLACKLIST or getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered:
                    discovered[u_l] = chat
            await asyncio.sleep(1.0)
        except Exception:
            pass

    print(f"[*] Aday sayısı: {len(discovered)}")
    
    approved = []
    for u_l, chat in discovered.items():
        u = getattr(chat, 'username', '')
        try:
            full = await client(GetFullChannelRequest(chat))
            full_chat = full.full_chat
            title = getattr(chat, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
            
            if getattr(chat, 'broadcast', False) or not is_megagroup or members < 50:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in EXCLUDE_TERMS):
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
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.20:
                continue
                
            hits = [k for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim", "kapak", "cips", "pepsi", "turna", "enuygun", "bilet", "tod", "gb", "internet", "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "satıyorum", "alınır", "alıyorum", "hesap", "lisans"] if k in combined_msgs + combined]
            if not hits:
                continue
                
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
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"🎯 ONAYLANDI: @{u:22s} | {title[:28]} | {members} üye")
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    approved.sort(key=lambda x: x["members"], reverse=True)
    with open("food_code_gems_approved.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Toplam Onaylanan Yeni Grup: {len(approved)}")

if __name__ == '__main__':
    asyncio.run(find_gems())
