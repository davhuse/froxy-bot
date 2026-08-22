import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerEmpty, Channel, Chat
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

# Targeted live transaction phrases used by Turkish coupon & code traders
LIVE_TRADE_QUERIES = [
    "yemeksepeti satılık", "yemeksepeti alınır", "yemeksepeti kupon", "yemeksepeti hesap satılık",
    "yemeksepeti 500", "yemeksepeti 400", "yemeksepeti indirim", "yemek kuponu satılık",
    "migros çeki satılık", "migros çeki alınır", "migros kod satılık", "migros hediye çeki",
    "turna kodu satılık", "turna çeki satılık", "turna bilet kodu", "turna uçak",
    "tıkla gelsin kod", "tiklagelsin kupon", "tiklagelsin satılık", "getir yemek kupon",
    "tod tv kod satılık", "tod tv kupon", "tod süperlig kod", "s sport kod satılık",
    "pepsi kod satılık", "pepsi kapak satılık", "cips kodu satılık", "kazandrio kod satılık",
    "daha daha puan satılık", "dahadaha kod", "freebayt internet satılık",
    "kupon satılık dm", "kod satılık dm", "çek satılık dm", "kupon alınır dm", "kod alınır dm",
    "kupon satıyorum", "kod satıyorum", "çek satıyorum", "kupon alıyorum", "kod alıyorum"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "iddaa", "bahis", "casino", "slot", "rulet", "bet",
    "gayrimenkul", "emlak", "oto alım", "araba alım", "mining", "papara"
]

async def hunt_live_coupon_groups():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    print("[*] Telegram Canlı Mesaj Araması Başlatılıyor...")
    
    discovered_chats = {}
    now = datetime.now(timezone.utc)
    
    for idx, q in enumerate(LIVE_TRADE_QUERIES, 1):
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=None,
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=30
            ))
            
            chat_map = {c.id: c for c in res.chats}
            new_in_query = 0
            
            for msg in res.messages:
                peer = msg.peer_id
                cid = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None)
                if not cid:
                    continue
                chat = chat_map.get(cid)
                if not chat:
                    continue
                username = getattr(chat, 'username', None)
                if not username:
                    continue
                username_l = username.lower()
                
                is_mega = getattr(chat, 'megagroup', False)
                is_broad = getattr(chat, 'broadcast', False)
                
                # Must be supergroup, not broadcast channel
                if is_broad or not is_mega:
                    continue
                    
                if username_l not in discovered_chats:
                    discovered_chats[username_l] = {
                        "entity": chat,
                        "query_match": q,
                        "sample_msg": msg.message[:120].replace("\n", " ") if msg.message else "",
                        "msg_date": msg.date
                    }
                    new_in_query += 1
                    
            print(f"[{idx:02d}/{len(LIVE_TRADE_QUERIES):02d}] '{q:28s}' -> +{new_in_query} yeni grup (Toplam: {len(discovered_chats)})")
            await asyncio.sleep(1.2)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            pass

    print(f"\n[*] Toplam canlı mesajlardan çıkarılan süpergruplar: {len(discovered_chats)}")
    print("[*] Grupların detayları, üye sayıları ve mesaj akışları kontrol ediliyor...\n")
    
    approved_live_groups = []
    
    for u, data in discovered_chats.items():
        try:
            ent = data["entity"]
            full = await client(GetFullChannelRequest(ent))
            full_chat = full.full_chat
            
            title = getattr(ent, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(ent, limit=20)
            if not messages:
                continue
                
            latest = messages[0]
            if not latest or not latest.date:
                continue
                
            msg_d = latest.date
            if msg_d.tzinfo is None:
                msg_d = msg_d.replace(tzinfo=timezone.utc)
            age_h = (now - msg_d).total_seconds() / 3600.0
            
            # Must be active within last 72 hours
            if age_h > 72.0:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Strict exclusions
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.20:
                continue
                
            # Must have real coupon/code/food/trade signals
            if not any(k in combined_msgs for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna", "tod", "pepsi", "cips", "indirim", "fiyat", "tl", "₺", "satılık", "satıyorum", "alınır", "alıyorum"]):
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "yemeksepeti", "migros", "turna"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            if age_h < 1:
                last_active_str = f"{int(age_h * 60)} dakika önce"
            elif age_h < 24:
                last_active_str = f"{int(age_h)} saat önce"
            else:
                last_active_str = f"{int(age_h / 24)} gün önce"
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "last_active": last_active_str,
                "age_hours": round(age_h, 1),
                "matched_query": data["query_match"],
                "live_search_hit": data["sample_msg"],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved_live_groups.append(rec)
            print(f"🎯 CANLI KUPON GRUBU BULUNDU: @{u:22s} | {title[:28]} | {members:5d} üye | Son Mesaj: {last_active_str}")
            
        except Exception as e:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    approved_live_groups.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    with open("canli_mesaj_bulunan_saf_kupon_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(approved_live_groups, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TOPLAM {len(approved_live_groups)} ADET AKTİF CANLI KUPON & KOD GRUBU BULUNDU!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(hunt_live_coupon_groups())
