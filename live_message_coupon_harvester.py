import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

LIVE_TRADE_QUERIES = [
    # 1. Yemeksepeti & Yemek İndirimleri
    "yemeksepeti kupon", "yemeksepeti kod", "yemeksepeti hesap", "yemeksepeti indirim",
    "yemeksepeti satılık", "yemeksepeti alınır", "yemeksepeti 500", "yemeksepeti 400",
    "yemek kuponu satılık", "tıkla gelsin kod", "tiklagelsin kupon", "getir yemek kupon",
    
    # 2. Migros & Alışveriş Çekleri
    "migros çek", "migros hediye çeki", "migros kod", "migros money", "migros sanal market",
    "market çeki satılık", "alışveriş çeki satılık", "hediye çeki satılık", "çek satılık dm",
    
    # 3. Turna, Enuygun & Bilet Kodları
    "turna çek", "turna uçak", "turna bilet", "turna kod satılık", "enuygun çek",
    "enuygun bilet", "bilet kuponu satılık", "tod tv kod", "tod süperlig kod", "s sport kod",
    
    # 4. Promosyon Kapak & Cips & GB Kodları
    "pepsi kod", "kazandrio kod", "daha daha puan", "cips kodu", "freebayt internet",
    "frebayt puan", "gb kod satılık", "hediye kodu satılık",
    
    # 5. Genel Kupon & Kod Alım-Satım İlanları
    "kupon satılık dm", "kod satılık dm", "çek satılık dm", "kupon alınır dm", "kod alınır dm",
    "kupon satıyorum", "kod satıyorum", "çek satıyorum", "kupon alıyorum", "kod alıyorum"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    "iddaa", "bahis", "casino", "slot", "rulet", "bet", "bonus", "kumar",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "mining", "papara"
]

async def harvest_live_coupon_groups():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    now = datetime.now(timezone.utc)
    print(f"[*] {len(LIVE_TRADE_QUERIES)} Özel Terim ile Telegram Canlı Mesaj Araması Başlatılıyor...\n")
    
    discovered_groups = {}
    
    for idx, q in enumerate(LIVE_TRADE_QUERIES, 1):
        try:
            res = await client(SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=35
            ))
            
            chat_map = {c.id: c for c in res.chats}
            new_c = 0
            
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
                u_l = username.lower()
                
                is_mega = getattr(chat, 'megagroup', False)
                is_broad = getattr(chat, 'broadcast', False)
                
                if is_broad or not is_mega:
                    continue
                    
                if u_l not in discovered_groups:
                    discovered_groups[u_l] = {
                        "entity": chat,
                        "matched_query": q,
                        "sample_ad": msg.message[:130].replace("\n", " ") if msg.message else "",
                        "msg_date": msg.date
                    }
                    new_c += 1
                    
            print(f"[{idx:02d}/{len(LIVE_TRADE_QUERIES):02d}] '{q:26s}' -> +{new_c} yeni grup (Toplam: {len(discovered_groups)})")
            await asyncio.sleep(1.0)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n[*] Toplam canlı mesajlardan toplanan süpergruplar: {len(discovered_groups)}")
    print("[*] Grupların canlılık, üye yazma izni ve alım-satım denetimleri yapılıyor...\n")
    
    verified_groups = []
    
    for u, data in discovered_groups.items():
        try:
            ent = data["entity"]
            full = await client(GetFullChannelRequest(ent))
            full_chat = full.full_chat
            
            title = getattr(ent, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            
            if members < 40:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(ew in combined for ew in EXCLUDE_WORDS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(ent, limit=25)
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
            
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.20:
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
                "slowmode_seconds": slowmode,
                "last_active": last_active_str,
                "age_hours": round(age_h, 1),
                "matched_query": data["matched_query"],
                "live_search_hit": data["sample_ad"],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            verified_groups.append(rec)
            print(f"💎 CANLI KUPON PAZARI: @{u:22s} | {title[:28]} | {members:5d} üye | Son Mesaj: {last_active_str}")
            
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    verified_groups.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    with open("canli_mesaj_onayli_kupon_gruplari.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_verified": len(verified_groups),
            "groups": verified_groups
        }, f, ensure_ascii=False, indent=2)
        
    with open("canli_kupon_gruplari.txt", "w", encoding="utf-8") as f:
        for g in verified_groups:
            f.write(f"@{g['username']}\n")
            
    print(f"\n=======================================================")
    print(f"✅ TOPLAM {len(verified_groups)} ADET CANLI KUPON & KOD GRUBU BAŞARIYLA DOĞRULANDI!")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(harvest_live_coupon_groups())
