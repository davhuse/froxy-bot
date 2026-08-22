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
from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

with open("session_7384.txt", "r", encoding="utf-8") as f:
    session_string = f.read().strip()

with open("master_known_blacklist.json", "r", encoding="utf-8") as f:
    KNOWN_BLACKLIST = set(json.load(f))

# Major seed trading groups to scrape linked trade communities
SEED_TRADE_GROUPS = [
    "kuponindirimsatis", "satcek", "kuponsat", "ceksat", "ticaretcanavari",
    "alsatticarettz", "letgoilanlari", "kuponhesapsatis", "kuponsatisgrup",
    "kuponcekkodsatis", "tahaaslan11", "indirimkodusatis", "alimsatimmerkezii",
    "ticaretforumofficial", "yucekuponsatis", "kupongrupta", "kodceksatismerkezi",
    "ticaretyapn", "wishx_2", "zeroticaret", "ticaretgruptr", "mukyemek",
    "ticaretZ", "uygunkod", "Kuponcekm", "kuponkodindirimilanlar", "kuponkodhesapilan",
    "kodkuponmarketi", "satiskodtakasi", "kuponindirimpazari", "indirim363",
    "kuponkodceksatis", "kodindirimsatis", "ceksatistakasgrup", "kuponvekodsatisgrubu",
    "ceksatkupon2", "kuponkodalimsatim", "kodmalf", "indirimruzgari1",
    "kuponindirimkodalisveris", "alisverisforumuguncel", "kuponindirimcek"
]

SEARCH_QUERIES = [
    # Kupon & Kod & Çek Alım Satım
    "kupon alım satım", "kupon al sat", "kupon ticaret", "kupon pazarı", "kupon borsa",
    "kupon market", "kupon depo", "kupon dünyası", "kupon ilan", "kupon merkezi",
    "çek alım satım", "çek al sat", "çek ticaret", "çek pazarı", "çek borsa",
    "çek market", "çek bozdurma", "hediye çeki", "market çeki", "alışveriş çeki",
    "kod alım satım", "kod al sat", "kod ticaret", "kod pazarı", "kod borsa",
    "kod market", "kod depo", "kod dünyası", "promosyon kod", "indirim kodu satış",
    
    # Yemek & Market & Bilet Çekleri
    "yemeksepeti kupon", "yemeksepeti kod", "yemeksepeti hesap", "yemeksepeti ilk sipariş",
    "yemek kuponu alım satım", "tıkla gelsin kupon", "getir kupon", "migros çek alım satım",
    "migros money kod", "turna çek", "enuygun çek", "biletinial kod", "tod tv kupon",
    "internet data kod", "gb kod alım satım", "daha daha kod", "kazandrio kod",
    
    # Dijital Hesap Satış
    "hesap alım satım", "hesap ticaret", "hesap pazarı", "hesap borsa", "hesap market",
    "dijital hesap satış", "premium hesap satış", "chatgpt hesap", "chatgpt plus",
    "canva pro hesap", "canva lisans", "adobe cc hesap", "adobe lisans", "gemini advanced",
    "claude pro", "semrush hesap", "envato elements", "freepik premium", "capcut pro",
    "nordvpn hesap", "vpn hesap satış", "netflix 4k hesap", "spotify premium",
    "youtube premium", "disney plus hesap", "exxen hesap", "blutv hesap",
    
    # Lisans & Key & Yazılım
    "lisans satış", "lisans alım satım", "windows lisans", "windows key", "windows 11 key",
    "office 365 lisans", "office key", "kaspersky key", "antivirüs key", "yazılım ticaret",
    "script satış", "bot satış", "dijital tedarik", "dijital ürün alım satım",
    
    # Mail & Platform Hesapları & SMM
    "gmail alım satım", "gmail ticaret", "gmail pazar", "eski tarihli hesap",
    "facebook hesap satış", "instagram hesap satış", "telegram hesap satış",
    "twitter hesap satış", "sanal numara satış", "sms onay", "smm panel ticaret",
    "smm pazar", "takipçi satış", "sosyal medya ticaret", "freelance ticaret"
]

EXCLUDE_WORDS = [
    # Oyun hesapları
    "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
    "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam", "growtopia",
    "standoff", "supercell", "fortnite",
    # Trendyol koleksiyon kaydetme
    "koleksiyon", "paylaş kazan", "paylas kazan", "kaydetme", "takip et kazan", "koleksiyonum",
    # Bahis / Kumar
    "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp", "rexbet", "betroy",
    # Admin fırsat tek taraflı yayın
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi", "günün fırsatları",
    # Emlak / Araç
    "gayrimenkul", "emlak", "ev alım", "oto alım"
]

async def harvest_candidates(client):
    candidates = set()
    
    print(f"[*] 1. AŞAMA: {len(SEED_TRADE_GROUPS)} Ana Ticaret Grubunun İçi Taranıyor (Link & Referanslar)...")
    for seed in SEED_TRADE_GROUPS:
        try:
            entity = await client.get_entity(seed)
            full = await client(GetFullChannelRequest(entity))
            about = getattr(full.full_chat, 'about', '') or ''
            for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", about):
                u = m.group(1).lower()
                if u not in KNOWN_BLACKLIST and u not in SEED_TRADE_GROUPS:
                    candidates.add(u)
                    
            messages = await client.get_messages(entity, limit=150)
            for msg in messages:
                if msg and msg.text:
                    for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", msg.text):
                        u = m.group(1).lower()
                        if u not in KNOWN_BLACKLIST and u not in SEED_TRADE_GROUPS and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
                            candidates.add(u)
        except Exception:
            pass
            
    print(f"    -> Seed grupların içindeki linklerden bulunan tekil aday sayısı: {len(candidates)}")

    print(f"[*] 2. AŞAMA: {len(SEARCH_QUERIES)} Özel Arama Sorgusu ile Telegram Global Araması Yapılıyor...")
    for q in SEARCH_QUERIES:
        try:
            res = await client(SearchRequest(q=q, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in KNOWN_BLACKLIST or getattr(chat, 'broadcast', False):
                    continue
                candidates.add(u_l)
            await asyncio.sleep(1.3)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass
            
    print(f"    -> Toplam keşfedilen ham aday grup sayısı: {len(candidates)}")
    return sorted(list(candidates - KNOWN_BLACKLIST))

async def inspect_and_filter(client, candidates):
    print(f"\n[*] 3. AŞAMA: {len(candidates)} Aday Grubun İç Mesaj, Kural ve İzin Denetimi Başlatılıyor...\n")
    
    approved = []
    rejected = []
    
    for idx, u in enumerate(candidates, 1):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            full_chat = full.full_chat
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            
            # 1. Supergroup/Megagroup check
            if getattr(entity, 'broadcast', False) or not is_megagroup:
                rejected.append({"username": u, "reason": "Broadcast Kanal"})
                continue
                
            # 2. Member threshold (>= 60)
            if members < 60:
                rejected.append({"username": u, "reason": f"Yetersiz üye ({members})"})
                continue
                
            combined_info = f"{title}\n{about}".lower()
            
            # 3. Keyword exclusions
            if any(ew in combined_info for ew in EXCLUDE_WORDS):
                rejected.append({"username": u, "reason": "Yasaklı anahtar kelime"})
                continue
                
            # 4. Member posting permission
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                rejected.append({"username": u, "reason": "Yazma izni kapalı"})
                continue
                
            # 5. Fetch recent messages
            try:
                messages = await client.get_messages(entity, limit=30)
            except Exception:
                messages = []
                
            if not messages:
                rejected.append({"username": u, "reason": "Mesaj geçmişi boş"})
                continue
                
            # Senders distribution
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 12 and len(set(senders)) <= 2:
                rejected.append({"username": u, "reason": "Tek taraflı yayın"})
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            # Exclude trendyol collection / game spam in messages
            if any(ew in combined_msgs for ew in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan link"]):
                rejected.append({"username": u, "reason": "Koleksiyon spamı"})
                continue
                
            game_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_cnt / len(msg_texts)) > 0.20:
                rejected.append({"username": u, "reason": "Oyun hesap spamı"})
                continue
                
            # Positive signals
            pos_hits = [k for k in [
                "kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim",
                "kapak", "cips", "pepsi", "turna", "enuygun", "bilet", "tod", "gb", "internet",
                "daha daha", "tıkla gelsin", "fiyat", "tl", "₺", "satılık", "satıyorum",
                "alınır", "alıyorum", "hesap", "lisans", "key", "chatgpt", "canva", "netflix",
                "spotify", "adobe", "vpn", "gmail", "smm", "panel", "takipçi", "sms onay", "numara"
            ] if k in combined_msgs + combined_info]
            
            if not pos_hits:
                rejected.append({"username": u, "reason": "Ticaret/satış sinyali yok"})
                continue
                
            # Sample live ads
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(k in tl for k in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "hesap", "lisans"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 130:
                        clean = clean[:127] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            # Determine category tags
            categories = []
            if any(k in combined_msgs + combined_info for k in ["kupon", "çek", "cek", "kod", "yemeksepeti", "migros", "turna", "tıkla gelsin", "enuygun", "bilet", "tod"]):
                categories.append("Kupon & Kod & Çek")
            if any(k in combined_msgs + combined_info for k in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "gmail", "mail"]):
                categories.append("Dijital Hesap Satış")
            if any(k in combined_msgs + combined_info for k in ["lisans", "key", "windows", "office", "yazılım", "script", "bot"]):
                categories.append("Lisans & Key & Yazılım")
            if any(k in combined_msgs + combined_info for k in ["smm", "panel", "takipçi", "sosyal medya", "numara", "sms onay"]):
                categories.append("SMM & Sanal Numara & Sosyal Medya")
            if not categories:
                categories.append("Dijital Ticaret")
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "categories": categories,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"🎯 ONAYLANDI: @{u:24s} | {title[:28]} | {members} üye | {', '.join(categories)}")
            
        except Exception:
            pass
        await asyncio.sleep(0.5)

    approved.sort(key=lambda x: x["members"], reverse=True)
    return approved

async def main():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    candidates = await harvest_candidates(client)
    approved = await inspect_and_filter(client, candidates)
    
    await client.disconnect()
    
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_new_approved": len(approved),
        "groups": approved
    }
    
    with open("derin_kesif_onayli_yeni_gruplar.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ DERİN KEŞİF TAMAMLANDI: {len(approved)} Adet Yepyeni Satış Grubu Bulundu!")
    print("=======================================================\n")

if __name__ == '__main__':
    asyncio.run(main())
