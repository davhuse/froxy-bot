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

with open("master_known_blacklist.json", "r", encoding="utf-8") as f:
    BLACKLIST = set(json.load(f))

SEARCH_QUERIES = [
    # Kupon Çeşitleri
    "kupon alım", "kupon satım", "kupon ticaret", "kupon pazar", "kupon borsa",
    "kupon market", "kupon depo", "kupon dünyası", "kupon ilan", "kupon merkezi",
    "kupon evi", "kupon kulübü", "kuponcu", "kuponalsat", "kupon borsa",
    
    # Çek & Hediye Çeki
    "çek alım", "çek satım", "çek ticaret", "çek pazar", "çek borsa",
    "çek market", "çek bozdurma", "hediye çeki", "market çeki", "alışveriş çeki",
    "çek deposu", "çek dünyası", "ceksat", "çek ilan",
    
    # Kod & İndirim & Promosyon
    "kod alım", "kod satım", "kod ticaret", "kod pazar", "kod borsa",
    "kod market", "kod depo", "kod dünyası", "indirim kodu", "promosyon kod",
    "kampanya kod", "kapak kodu", "cips kodu", "kod merkezi", "kod ilan",
    
    # Yemek & Market & Bilet
    "yemeksepeti kupon", "yemeksepeti kod", "yemeksepeti hesap", "yemek kuponu",
    "tıkla gelsin kod", "getir kupon", "migros çek", "migros money", "turna çek",
    "enuygun çek", "biletinial kod", "tod tv kod", "internet data", "gb kodu",
    
    # Hesap Satış & Pazar
    "hesap alım", "hesap satım", "hesap ticaret", "hesap pazar", "hesap borsa",
    "hesap market", "dijital hesap", "premium hesap", "hesap ilan",
    
    # AI & Tasarım & Lisans
    "chatgpt hesap", "chatgpt plus", "canva pro", "canva lisans", "adobe cc",
    "adobe lisans", "gemini advanced", "claude pro", "semrush hesap",
    "envato elements", "freepik premium", "capcut pro", "nordvpn hesap",
    "vpn hesap", "netflix 4k", "spotify premium", "youtube premium", "disney plus",
    
    # Yazılım & Lisans & Key
    "windows lisans", "windows key", "windows 11 key", "office 365 lisans",
    "office key", "kaspersky key", "antivirüs key", "yazılım ticaret",
    "script satış", "bot satış", "dijital tedarik", "dijital ürün",
    
    # Mail & Platform & SMM
    "gmail alım", "gmail satım", "gmail ticaret", "gmail pazar", "eski tarihli hesap",
    "facebook hesap", "instagram hesap", "telegram hesap", "sanal numara",
    "sms onay", "smm panel", "smm ticaret", "takipçi ticaret", "sosyal medya ticaret"
]

EXCLUDE_TERMS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları",
    "gayrimenkul", "emlak", "ev alım", "oto alım"
]

async def run_harvester():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    print(f"[*] Bilinen ve kara listedeki grup sayısı: {len(BLACKLIST)}")
    discovered = {}
    
    print(f"\n--- 1. {len(SEARCH_QUERIES)} Arama Sorgusu ile Telegram Global Taraması ---")
    for idx, q in enumerate(SEARCH_QUERIES, 1):
        try:
            res = await client(SearchRequest(q=q, limit=50))
            new_c = 0
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in BLACKLIST or getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered:
                    discovered[u_l] = chat
                    new_c += 1
            print(f"[{idx:02d}/{len(SEARCH_QUERIES):02d}] '{q:24s}' -> +{new_c} yeni (Toplam tekil: {len(discovered)})")
            await asyncio.sleep(1.2)
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n--- 2. {len(discovered)} Aday Grubun Derin İç Denetimi ---")
    approved = []
    
    for idx, (u_l, chat) in enumerate(discovered.items(), 1):
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
                
            combined_info = f"{title}\n{about}".lower()
            if any(et in combined_info for et in EXCLUDE_TERMS):
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
            
            if any(et in combined_msgs for et in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.20:
                continue
                
            hits = [k for k in [
                "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim",
                "kapak", "cips", "pepsi", "turna", "enuygun", "bilet", "tod", "gb", "internet",
                "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "satıyorum",
                "alınır", "alıyorum", "hesap", "lisans", "key", "chatgpt", "canva", "netflix",
                "spotify", "adobe", "vpn", "gmail", "smm", "panel", "takipçi", "sms onay", "numara"
            ] if k in combined_msgs + combined_info]
            
            if not hits:
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "hesap", "lisans"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            cats = []
            if any(k in combined_msgs + combined_info for k in ["kupon", "çek", "cek", "kod", "yemeksepeti", "migros", "turna", "tıkla gelsin", "enuygun", "bilet", "tod"]):
                cats.append("Kupon & Kod & Çek")
            if any(k in combined_msgs + combined_info for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail", "mail"]):
                cats.append("Dijital Hesap Satış")
            if any(k in combined_msgs + combined_info for k in ["lisans", "key", "windows", "office", "yazılım", "script", "bot"]):
                cats.append("Lisans & Key & Yazılım")
            if any(k in combined_msgs + combined_info for k in ["smm", "panel", "takipçi", "sosyal medya", "numara", "sms onay"]):
                cats.append("SMM & Sanal Numara & Sosyal Medya")
            if not cats:
                cats.append("Dijital Ticaret")
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "categories": cats,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"🎯 ONAYLANDI: @{u:22s} | {title[:28]} | {members} üye | {', '.join(cats)}")
        except Exception:
            pass
        await asyncio.sleep(0.4)

    await client.disconnect()
    
    approved.sort(key=lambda x: x["members"], reverse=True)
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_approved": len(approved),
        "groups": approved
    }
    
    with open("ultimate_approved_groups.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ TAMAMLANDI: Toplam {len(approved)} Yepyeni Onaylı Satış Grubu Bulundu!")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(run_harvester())
