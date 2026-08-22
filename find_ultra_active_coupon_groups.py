import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

# Target strictly: Kupon, Çek, İndirim, Kod, Yemeksepeti, Migros, Turna, Enuygun, Bilet, Kapak/Promosyon Kodları
KEYWORDS = [
    # Kupon & Çek & Kod Alım Satım
    "kupon alım satım", "kupon al sat", "kupon satışı", "kupon pazarı", "kupon borsa",
    "çek alım satım", "çek al sat", "çek satışı", "çek pazarı", "çek borsa", "çek bozdurma",
    "kod alım satım", "kod al sat", "kod satışı", "kod pazarı", "kod borsa", "kod market",
    "kupon kod alım satım", "kupon çek alım satım", "kod çek alım satım",
    "indirim kuponu alım satım", "promosyon kodu alım satım", "hediye çeki alım satım",
    
    # Yemek & Market & Bilet Çekleri
    "yemeksepeti kupon", "yemeksepeti kod", "yemeksepeti indirim", "yemeksepeti ilk sipariş",
    "yemek kuponu", "yemek kodu", "tıkla gelsin kupon", "tıkla gelsin kod", "getir kupon",
    "migros çek", "migros kod", "migros money", "turna çek", "turna uçak", "enuygun çek",
    "biletinial indirim", "sinema kupon", "tod tv kupon", "tod tv kod",
    
    # Promosyon, İnternet GB & Kapak Kodları
    "kapak kodu", "cips kodu", "pepsi kodu", "kazandrio kod", "daha daha kod",
    "freebayt kod", "internet kod alım satım", "gb kod alım satım", "hediye kodu alım satım",
    
    # Kelime Birleşimleri
    "kuponlar", "kuponcu", "ceksat", "kuponsat", "kodsat", "kuponalsat", "kodalsat",
    "indirimvadisi", "kupondunyasi", "koddunyasi", "cekdunyasi"
]

EXCLUDE_WORDS = [
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp",
    "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları",
    "gayrimenkul", "emlak", "ev alım", "oto alım", "araba alım", "araç alım", "mining"
]

POSITIVE_KUPON_SIGNALS = [
    "yemeksepeti", "migros", "turna", "enuygun", "çek", "cek", "kupon", "kod",
    "indirim", "tıkla gelsin", "tiklagelsin", "getir", "hediye çeki", "hediye ceki",
    "kapak", "cips", "pepsi", "bilet", "tod", "gb", "internet", "daha daha",
    "kazandrio", "freebayt", "money", "satılık", "satıyorum", "alınır", "alıyorum"
]

async def main():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    now = datetime.now(timezone.utc)
    print(f"[*] Canlı Telegram Kupon/Kod Pazar Taraması Başlatıldı ({now.isoformat()})")
    
    discovered = {}
    
    # 1. Check account's current dialogs for existing joined groups and scrape mentions
    print("[*] 1. Hesabın mevcut grupları ve dialogları inceleniyor...")
    try:
        dialogs = await client.get_dialogs(limit=100)
        for d in dialogs:
            if d.is_group or d.is_channel:
                chat = d.entity
                u = getattr(chat, 'username', None)
                if u and not getattr(chat, 'broadcast', False):
                    discovered[u.lower()] = chat
                # Check recent messages in these groups for mentions of other groups
                try:
                    msgs = await client.get_messages(chat, limit=40)
                    for m in msgs:
                        if m and m.text:
                            for found_u in re.findall(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", m.text):
                                found_u_l = found_u.lower()
                                if found_u_l not in discovered and found_u_l not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                                    try:
                                        ent = await client.get_entity(found_u_l)
                                        if getattr(ent, 'megagroup', False) or getattr(ent, 'gigagroup', False):
                                            discovered[found_u_l] = ent
                                    except Exception:
                                        pass
                except Exception:
                    pass
    except Exception as e:
        print(f"Dialog hatası: {e}")
        
    print(f"    -> Dialog ve iç bağlantılardan bulunan grup: {len(discovered)}")

    # 2. Global Telegram Search
    print(f"[*] 2. {len(KEYWORDS)} Hedef Kupon/Çek/Kod Terimi ile Telegram Global Taraması...")
    for idx, kw in enumerate(KEYWORDS, 1):
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u or getattr(chat, 'broadcast', False):
                    continue
                u_l = u.lower()
                if u_l not in discovered:
                    discovered[u_l] = chat
            await asyncio.sleep(1.1)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    print(f"\n[*] Toplam incelenecek aday grup sayısı: {len(discovered)}")
    print("[*] 3. Canlılık, Güncellik ve Kupon/Kod İlan Denetimi Yapılıyor...\n")
    
    approved_active = []
    
    for u_l, chat in discovered.items():
        u = getattr(chat, 'username', '')
        if not u:
            continue
        try:
            full = await client(GetFullChannelRequest(chat))
            full_chat = full.full_chat
            title = getattr(chat, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False)
            
            # Supergroup & member count check
            if getattr(chat, 'broadcast', False) or not is_megagroup or members < 60:
                continue
                
            combined_meta = f"{title}\n{about}".lower()
            if any(ew in combined_meta for ew in EXCLUDE_WORDS):
                continue
                
            # Permission check: Members must be able to send messages
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            # Fetch recent 35 messages
            messages = await client.get_messages(chat, limit=35)
            if not messages:
                continue
                
            # --- CRITICAL LIVELINESS & ACTIVITY CHECK ---
            latest_msg = messages[0]
            if not latest_msg or not latest_msg.date:
                continue
                
            msg_date = latest_msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            
            # Calculate how many hours ago the last message was sent
            age_hours = (now - msg_date).total_seconds() / 3600.0
            
            # Must have message activity within the last 72 hours (Active group!)
            if age_hours > 72.0:
                continue
                
            # Check sender diversity (Not 1 admin broadcasting)
            senders = [m.sender_id for m in messages if m and m.sender_id]
            unique_senders = len(set(senders))
            if len(messages) >= 12 and unique_senders <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Reject trendyol collection spam
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan"]):
                continue
                
            # Reject game accounts (PES, Brawl Stars, Roblox etc)
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.20:
                continue
                
            # Check presence of positive coupon/code/food/voucher trading signals
            signal_hits = [k for k in POSITIVE_KUPON_SIGNALS if k in combined_msgs + combined_meta]
            if len(signal_hits) < 2:
                continue
                
            # Extract sample trading ads
            sample_ads = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "turna"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(sample_ads) < 3:
                        sample_ads.append(clean)
                        
            # Format time ago string
            if age_hours < 1:
                last_active_str = f"{int(age_hours * 60)} dakika önce"
            elif age_hours < 24:
                last_active_str = f"{int(age_hours)} saat önce"
            else:
                last_active_str = f"{int(age_hours / 24)} gün önce"
                
            group_data = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "last_active": last_active_str,
                "age_hours": round(age_hours, 1),
                "unique_senders_last_35": unique_senders,
                "signals": signal_hits,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": sample_ads,
                "link": f"https://t.me/{u}"
            }
            approved_active.append(group_data)
            print(f"🔥 AKTİF GRUP: @{u:22s} | {title[:28]} | {members} üye | Son Mesaj: {last_active_str}")
            
        except Exception:
            pass
        await asyncio.sleep(0.4)

    await client.disconnect()
    
    # Sort by member count and recent activity
    approved_active.sort(key=lambda x: (x["age_hours"], -x["members"]))
    
    output = {
        "scan_time": now.isoformat(),
        "total_active_groups": len(approved_active),
        "groups": approved_active
    }
    
    with open("aktif_saf_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ AKTİF KUPON & KOD GRUP TARAMASI TAMAMLANDI!")
    print(f"Bulunan Canlı & Aktif Ticaret Grubu: {len(approved_active)}")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(main())
