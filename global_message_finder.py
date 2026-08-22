import asyncio
import json
import os
import re
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

with open("master_known_blacklist.json", "r", encoding="utf-8") as f:
    BLACKLIST = set(json.load(f))

SEARCH_TERMS = [
    "yemeksepeti kupon", "yemeksepeti kod", "migros çek", "turna uçak", "tıkla gelsin kod",
    "enuygun çek", "biletinial indirim", "tod tv kod", "kapak kodu satılık",
    "chatgpt plus satılık", "canva pro", "adobe cc lisans", "windows 11 pro key",
    "office 365 lisans", "gmail hesabı alınır", "gmail alım satım", "sanal numara satılık",
    "sms onay satılık", "smm panel bayilik", "kupon kod alım satım", "çek alım satım",
    "kuponcu", "indirim kodu satılık", "daha daha hak", "kazandrio kod",
    "kupon satılık", "kod alım satım", "hesap alım satım", "lisans satılık", "key satılık",
    "netflix 4k satılık", "spotify premium satılık", "youtube premium satılık",
    "disney plus satılık", "nordvpn satılık", "exxen hesap satılık", "blutv hesap satılık",
    "takipçi satılık", "sosyal medya satış", "bot satılık", "script satılık",
    "freelance iş ilan", "e-ticaret tedarik", "dijital ürün satılık", "hediye çeki satılık"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
    "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları",
    "gayrimenkul", "emlak", "ev alım", "oto alım"
]

async def search_via_global_messages():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    print(f"[*] Bilinen grup sayısı: {len(BLACKLIST)}")
    discovered_chats = {}
    
    print(f"[*] {len(SEARCH_TERMS)} Terim ile Global Canlı Mesaj Taraması Başlatılıyor...")
    for term in SEARCH_TERMS:
        try:
            res = await client(SearchGlobalRequest(
                q=term,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=60
            ))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in BLACKLIST or getattr(chat, 'broadcast', False):
                    continue
                if u_l not in discovered_chats:
                    discovered_chats[u_l] = chat
            print(f"  '{term:26s}' -> Toplam bulunan benzersiz grup: {len(discovered_chats)}")
            await asyncio.sleep(1.4)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"Hata ({term}): {e}")

    print(f"\n[*] Toplam incelenecek yeni aday grup sayısı: {len(discovered_chats)}")
    
    approved = []
    for u_l, chat in discovered_chats.items():
        u = getattr(chat, 'username', '')
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
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.25:
                continue
                
            hits = [k for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim", "kapak", "cips", "turna", "bilet", "tod", "gb", "internet", "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "alınır", "hesap", "lisans", "key"] if k in combined_msgs + combined]
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
                        
            cats = []
            if any(k in combined_msgs + combined for k in ["kupon", "çek", "cek", "kod", "yemeksepeti", "migros", "turna", "tıkla gelsin", "enuygun", "bilet"]):
                cats.append("Kupon & Kod & Çek")
            if any(k in combined_msgs + combined for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail"]):
                cats.append("Dijital Hesap Satış")
            if any(k in combined_msgs + combined for k in ["lisans", "key", "windows", "office", "yazılım"]):
                cats.append("Lisans & Key & Yazılım")
            if any(k in combined_msgs + combined for k in ["smm", "panel", "takipçi", "sosyal medya", "numara", "sms onay"]):
                cats.append("SMM & Sosyal Medya")
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
    with open("global_message_search_results.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Bulunan Yepyeni Grup Sayısı: {len(approved)}")

if __name__ == '__main__':
    asyncio.run(search_via_global_messages())
