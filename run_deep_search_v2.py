import asyncio
import os
import re
import json
import sys
import aiohttp
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChatBannedRights

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'
bot_token = '8961373302:AAGNs9fcPFU_XcWDUlhbNhQ2hRNzyRu6_MI'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

GAME_EXCLUDE_TERMS = [
    "brawl stars", "brawlstars", "pes", "efootball", "e-football", "roblox",
    "clash royale", "clash of clans", "pubg mobile", "free fire", "valorant",
    "metin2", "zula", "lol hesap", "league of legends", "mobile legends", "mlbb",
    "fc 24", "fc 25", "fc 26", "fifa", "wolfteam", "growtopia", "standoff",
    "brawl", "supercell", "pubg", "fortnite"
]

CHAT_EXCLUDE_TERMS = [
    "sohbet grubu", "muhabbet", "tanışma", "arkadaşlık", "itiraf", "gırgır",
    "geyik", "liseli", "üniversite", "chat grubu", "sohbet & muhabbet", "grup kuralları: sadece sohbet"
]

ADMIN_DEAL_EXCLUDE_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "indirim haberleri", "günün fırsatları", "gunun firsatlari", "amazon fırsat",
    "affiliate", "sadece admin paylaşır", "yalnızca admin", "mesaj yazmak yasaktır",
    "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı", "fırsat kanalı", "indirim kanalı"
]

POSITIVE_TARGET_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim kodu", "yemeksepeti", "trendyol",
    "getir", "migros", "hesap", "hesap satış", "hesap alım", "hesap alim",
    "lisans", "key", "windows", "office", "antivirüs", "dijital", "dijital ürün",
    "smm", "panel", "takipçi", "sosyal medya", "chatgpt", "canva", "adobe",
    "netflix", "spotify", "vpn", "freelance", "webmaster", "r10", "ticaret",
    "alım satım", "alim satim", "pazaryeri", "ilan", "e-ticaret", "tedarik"
]

def load_known():
    if os.path.exists("known_groups_dump.json"):
        with open("known_groups_dump.json", "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def clean_username(raw):
    raw = str(raw or "").strip()
    m = re.search(r"(?:t\.me/|telegram\.me/)?(?:joinchat/|\+)?([A-Za-z0-9_]{4,32})", raw)
    if m:
        u = m.group(1).lower()
        if u not in {"joinchat", "share", "addstickers", "proxy", "iv", "s", "c", "bot", "channel", "login", "signup"}:
            return u
    return None

async def fetch_url(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=6)) as r:
            if r.status == 200:
                return await r.text()
    except Exception:
        pass
    return ""

async def crawl_web_candidates():
    known_set = load_known()
    print(f"[*] Bilinen grup sayısı: {len(known_set)} (Bunlar elenecek)", flush=True)
    
    queries = [
        'site:t.me "kupon" "alım satım"',
        'site:t.me "kupon sat" telegram',
        'site:t.me "çek sat" kupon',
        'site:t.me "kod sat" indirim',
        'site:t.me "hesap sat" dijital',
        'site:t.me "hesap alım satım"',
        'site:t.me "lisans satış" key',
        'site:t.me "dijital ürün" satış',
        'site:t.me "smm panel" ticaret',
        'site:t.me "trendyol kupon" sat',
        'site:t.me "yemeksepeti kupon"',
        'site:t.me "canva" "chatgpt" hesap',
        'site:t.me "netflix" "spotify" hesap',
        'site:t.me "freelance" "ticaret"',
        'site:t.me "webmaster" "alım satım"',
        'site:t.me "sosyal medya" hesap sat',
        'site:t.me "dijital pazar" alım satım',
        'site:t.me "al sat" ticaret kupon',
        'site:t.me "kod pazarı" alım satım',
        'site:t.me "e-ticaret" alım satım',
        'site:t.me "hesap pazarı"',
        'site:t.me "kupon pazarı"',
        'site:t.me "lisans pazarı"',
        'site:t.me "dijital hesap satış"',
        'site:t.me "indirim çeki" satış'
    ]
    
    candidates = set()
    
    # 1. Generate algorithmic Turkish digital sales patterns
    base_stems = [
        "kupon", "kuponsatis", "kuponcu", "kuponlar", "kuponpazari", "kuponalsat", "kuponmarket",
        "ceksatis", "ceksat", "cekalim", "cekmagaza", "cekpazari",
        "kodsatis", "kodsat", "kodlar", "kodpazari", "kodalsat", "indirimkodu", "indirimkuponu",
        "hesapsatis", "hesappazari", "hesapalsat", "hesapmerkezi", "hesaplar", "dijitalhesap",
        "lisanssatis", "lisanspazari", "lisansmarket", "keysatis", "keypazari",
        "dijitalsatis", "dijitalpazar", "dijitalticaret", "dijitalmarket", "dijitalurun",
        "smmpaneltr", "smmticaret", "smmpazari", "sosyalmedyapazari", "sosyalmedyaticaret",
        "eticaretturkiye", "ticaretodasi", "ticaretalani", "alimsatimplatformu", "ticaretplatformu",
        "webmastertr", "freelancetr", "yazilimticaret", "dijitaltedarik"
    ]
    suffixes = ["", "1", "2", "tr", "_tr", "official", "grup", "grubu", "_official", "_grup"]
    for stem in base_stems:
        for s in suffixes:
            cand = f"{stem}{s}".lower()
            if cand not in known_set:
                candidates.add(cand)

    print(f"[*] Algoritmik aday sayısı: {len(candidates)}", flush=True)

    # 2. Async Web search
    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for q in queries:
            ddg_url = f"https://html.duckduckgo.com/html/?q={q}"
            bing_url = f"https://www.bing.com/search?q={q}"
            tasks.append(fetch_url(session, ddg_url))
            tasks.append(fetch_url(session, bing_url))
            
        print(f"[*] {len(tasks)} arama sorgusu çalıştırılıyor...", flush=True)
        results = await asyncio.gather(*tasks)
        for html in results:
            if not html:
                continue
            for m in re.finditer(r"t\.me/(?:joinchat/|\+)?([A-Za-z0-9_]{4,32})", html):
                u = clean_username(m.group(1))
                if u and u not in known_set:
                    candidates.add(u)
                    
    filtered_candidates = sorted(list(candidates - known_set))
    print(f"[*] Toplam taranacak yeni aday sayısı: {len(filtered_candidates)}", flush=True)
    return filtered_candidates

async def inspect_candidates(candidates):
    known_set = load_known()
    client = TelegramClient('deep_inspector_bot', api_id, api_hash)
    await client.start(bot_token=bot_token)
    
    approved = []
    rejected = []
    
    print("\n=======================================================", flush=True)
    print("      TELEGRAM CANLI İÇ VE KURAL DENETİMİ BAŞLADI      ", flush=True)
    print("=======================================================\n", flush=True)
    
    for idx, u in enumerate(candidates, 1):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full.full_chat, 'about', '') or ''
            members = getattr(full.full_chat, 'participants_count', 0) or 0
            is_megagroup = getattr(entity, 'megagroup', False)
            is_gigagroup = getattr(entity, 'gigagroup', False)
            is_broadcast = getattr(entity, 'broadcast', False)
            
            combined = f"{title}\n{about}".lower()
            
            # 1. Kanal / Broadcast Kontrolü
            if is_broadcast or (not is_megagroup and not is_gigagroup):
                rejected.append({"username": u, "title": title, "members": members, "reason": "Broadcast Kanal (Üyeler yazamaz)"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> KANAL (Elenmiştir)", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 2. Üye Sayısı Kontrolü
            if members < 80:
                rejected.append({"username": u, "title": title, "members": members, "reason": f"Yetersiz üye ({members})"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> YETERSİZ ÜYE ({members})", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 3. Oyun Hesapları (PES, Brawl Stars vb.) Kontrolü
            game_hits = [term for term in GAME_EXCLUDE_TERMS if term in combined]
            if game_hits:
                rejected.append({"username": u, "title": title, "members": members, "reason": f"Oyun hesabı grubu ({', '.join(game_hits)})"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> OYUN HESABI ({', '.join(game_hits)})", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 4. Sohbet / Muhabbet Kontrolü
            has_sales = any(term in combined for term in POSITIVE_TARGET_TERMS)
            chat_hits = [term for term in CHAT_EXCLUDE_TERMS if term in combined]
            if (chat_hits and not has_sales) or ("sohbet" in title.lower() and not has_sales):
                rejected.append({"username": u, "title": title, "members": members, "reason": "Sohbet / Muhabbet grubu"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> SOHBET GRUBU", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 5. Admin İndirim / Sıcak Fırsat / Affiliate Paylaşım Kanalı Kontrolü
            admin_hits = [term for term in ADMIN_DEAL_EXCLUDE_TERMS if term in combined]
            if admin_hits:
                rejected.append({"username": u, "title": title, "members": members, "reason": f"Admin fırsat/duyuru paylaşımı ({', '.join(admin_hits)})"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> ADMİN İNDİRİM KANALI ({', '.join(admin_hits)})", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 6. Pozitif Dijital Satış / Kupon / Hesap / Lisans / Ticaret Sinyali
            pos_hits = [term for term in POSITIVE_TARGET_TERMS if term in combined]
            if not pos_hits:
                rejected.append({"username": u, "title": title, "members": members, "reason": "Hedef satış sinyali yok"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> SATIŞ SİNYALİ YOK", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # 7. Mesaj Gönderme İzni Kontrolü
            banned_rights = getattr(full.full_chat, 'default_banned_rights', None)
            if banned_rights and getattr(banned_rights, 'send_messages', False):
                rejected.append({"username": u, "title": title, "members": members, "reason": "Grupta üyelerin mesaj yazması kapalı"})
                print(f"[{idx:03d}/{len(candidates):03d}] ❌ @{u:25s} -> MESAJ YAZMA KAPALI", flush=True)
                await asyncio.sleep(0.3)
                continue
                
            # Kategori Etiketleme
            cat_list = []
            if any(t in combined for t in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "migros", "getir", "indirim"]):
                cat_list.append("Kupon & Çek & İndirim")
            if any(t in combined for t in ["hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "vpn", "mail"]):
                cat_list.append("Dijital Hesap Satış")
            if any(t in combined for t in ["lisans", "key", "windows", "office", "yazılım"]):
                cat_list.append("Lisans & Key & Yazılım")
            if any(t in combined for t in ["smm", "panel", "takipçi", "sosyal medya"]):
                cat_list.append("SMM & Sosyal Medya")
            if any(t in combined for t in ["ticaret", "alım satım", "pazaryeri", "ilan", "freelance"]):
                cat_list.append("Dijital Ticaret / Pazar")
                
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "categories": cat_list,
                "positive_signals": pos_hits,
                "about": about.replace("\n", " ")[:200],
                "link": f"https://t.me/{u}"
            }
            approved.append(rec)
            print(f"[{idx:03d}/{len(candidates):03d}] 🎯 ONAYLANDI: @{u:20s} | {title[:30]} | {members} üye | {', '.join(cat_list)}", flush=True)
            
        except Exception as exc:
            err_msg = str(exc)
            if "Cannot find any entity" in err_msg or "UsernameNotOccupied" in err_msg:
                pass
            else:
                pass
                
        await asyncio.sleep(0.3)
        
    await client.disconnect()
    
    # Sort approved by members descending
    approved.sort(key=lambda x: x["members"], reverse=True)
    
    output_data = {
        "total_approved": len(approved),
        "total_rejected": len(rejected),
        "groups": approved
    }
    
    with open("yeni_onayli_gruplar_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print("\n=======================================================", flush=True)
    print(f"✅ TARAMA BİTTİ! Toplam {len(approved)} Adet Filtreye Uygun Yeni Satış Grubu Bulundu.", flush=True)
    print("=======================================================\n", flush=True)

async def main():
    candidates = await crawl_web_candidates()
    await inspect_candidates(candidates)

if __name__ == '__main__':
    asyncio.run(main())
