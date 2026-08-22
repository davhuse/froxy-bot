import asyncio
import json
import os
import re
import sys
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

TARGET_KEYWORDS_V2 = [
    "dijital pazar", "dijital market", "dijital ürün", "dijital satis",
    "kupon ticaret", "kupon borsa", "kupon depo", "kupon dükkanı",
    "kod al sat", "kod ticaret", "kod deposu", "kod borsa",
    "çek market", "çek ticaret", "indirim marketi", "indirim deposu",
    "yemek kupon", "yemeksepeti indirim", "migros kod", "trendyol kod",
    "lisans pazar", "lisans depo", "key pazar", "key ticaret",
    "hesap ticaret", "hesap market", "hesap borsa", "hesap deposu",
    "mail pazar", "mail ticaret", "gmail pazar", "gmail depo",
    "sosyal medya ticaret", "sosyal medya alım satım", "sosyal medya bayi",
    "smm ticaret", "smm pazar", "takipçi pazar", "takipçi ticaret",
    "bot pazar", "yazılım pazar", "script pazar", "freelance ticaret"
]

GAME_EXCLUDE_EXACT = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "gayrimenkul",
    "emlak", "ev alım", "araba alım", "oto alım"
]

def load_known_dump():
    known = set()
    if os.path.exists("known_groups_dump.json"):
        with open("known_groups_dump.json", "r", encoding="utf-8") as f:
            known = set(json.load(f))
    # Also load already approved groups from v1
    if os.path.exists("yeni_onayli_gruplar_raporu.json"):
        with open("yeni_onayli_gruplar_raporu.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for g in data.get("approved_groups", []):
                known.add(g["username"].lower())
    return known

async def run_search_v2():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known = load_known_dump()
    discovered = {}
    
    print(f"[*] 2. Aşama Hedefli Kelime Taraması Başlatılıyor ({len(TARGET_KEYWORDS_V2)} Kelime)...")
    for kw in TARGET_KEYWORDS_V2:
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in known:
                    continue
                if getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered:
                    discovered[u_l] = {"username": u, "chat": chat, "kw": kw}
            await asyncio.sleep(1.6)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"[*] 2. Aşama İncelenecek Aday Sayısı: {len(discovered)}")
    
    new_approved = []
    for u_l, item in discovered.items():
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
            if not is_megagroup or getattr(chat, 'broadcast', False) or members < 80:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(gt in combined for gt in GAME_EXCLUDE_EXACT):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(chat, limit=25)
            if not messages:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 12 and len(set(senders)) <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            game_msg_count = sum(1 for t in msg_texts if any(gt in t.lower() for gt in GAME_EXCLUDE_EXACT))
            if len(msg_texts) > 0 and (game_msg_count / len(msg_texts)) > 0.25:
                continue
                
            categories = []
            if any(t in combined_msgs + combined for t in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "migros", "getir", "indirim"]):
                categories.append("Kupon / Kod / Çek")
            if any(t in combined_msgs + combined for t in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail", "mail"]):
                categories.append("Dijital Hesap Satış")
            if any(t in combined_msgs + combined for t in ["lisans", "key", "windows", "office", "yazılım", "script", "bot"]):
                categories.append("Lisans & Key & Yazılım")
            if any(t in combined_msgs + combined for t in ["smm", "panel", "takipçi", "sosyal medya"]):
                categories.append("SMM & Sosyal Medya")
            if not categories:
                categories.append("Dijital Ticaret / Pazar")
                
            samples = [t.replace("\n", " ").strip()[:110] for t in msg_texts if any(k in t.lower() for k in ["satılık", "fiyat", "tl", "stok", "dm", "alım", "satım"])][:3]
            
            new_approved.append({
                "username": u,
                "title": title,
                "members": members,
                "categories": categories,
                "slowmode_seconds": slowmode,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            })
            print(f"🎯 ONAYLANDI: @{u} | {title} ({members} üye)")
        except Exception:
            pass
        await asyncio.sleep(1.0)
        
    await client.disconnect()
    
    with open("yeni_onayli_gruplar_v2.json", "w", encoding="utf-8") as f:
        json.dump(new_approved, f, ensure_ascii=False, indent=2)
    print(f"2. Aşama Ek Onaylanan Grup: {len(new_approved)}")

if __name__ == '__main__':
    asyncio.run(run_search_v2())
