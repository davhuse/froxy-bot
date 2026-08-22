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

def get_all_previously_reported():
    known = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json"
    ]
    for fn in files:
        if not os.path.exists(fn):
            continue
        if fn.endswith(".json"):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        for item in d:
                            if isinstance(item, str):
                                known.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    known.add(u.lower().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        known.add(item["username"].lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                known.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip().lstrip("@").lower()
                        m = re.search(r"([a-z0-9_]{4,32})", line)
                        if m:
                            known.add(m.group(1).lower())
            except Exception:
                pass
    return known

async def find_sibling_and_similar_groups():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    known = get_all_previously_reported()
    print(f"[*] Daha önce raporlanan ve bilinen toplam grup sayısı: {len(known)}")
    
    candidates = set()
    
    # 1. Inspect @kodalimsatim and @kuponalsatgurup and check their messages for mentions/links to other sister trade groups
    seed_groups = ["kodalimsatim", "kuponalsatgurup", "kuponkodmerkez", "KodKuponMerkezi", "ceksatp8"]
    for seed in seed_groups:
        try:
            entity = await client.get_entity(seed)
            full = await client(GetFullChannelRequest(entity))
            about = getattr(full.full_chat, 'about', '') or ''
            print(f"Seed @{seed} Hakkında: {about}")
            for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", about):
                u = m.group(1).lower()
                if u not in known and u not in seed_groups:
                    candidates.add(u)
                    
            messages = await client.get_messages(entity, limit=100)
            for msg in messages:
                if msg and msg.text:
                    for m in re.finditer(r"(?:t\.me/|@)([A-Za-z0-9_]{4,32})", msg.text):
                        u = m.group(1).lower()
                        if u not in known and u not in seed_groups and u not in {"joinchat", "share", "proxy", "iv", "s", "c", "bot", "channel"}:
                            candidates.add(u)
        except Exception as e:
            print(f"Seed hatası ({seed}): {e}")

    print(f"[*] Seed grupların içindeki linklerden bulunan adaylar: {len(candidates)}")

    # 2. Targeted search queries mimicking the exact structure of @kodalimsatim / @kuponalsatgurup
    exact_style_keywords = [
        "kupon kod alım satım", "kupon kod alim satim", "kupon kod ilan",
        "kupon kod satış", "kupon kod satis", "kod kupon alım",
        "çek kod satış", "cek kod satis", "çek kupon alım satım",
        "kupon çek satış", "kupon cek satis", "kod çek alım satım",
        "kupon al sat grup", "kod al sat grup", "çek al sat grup",
        "dijital alım satım grup", "dijital kod satış", "dijital kupon satış",
        "yemek kupon alım satım", "hediye çeki alım satım", "market çeki satış",
        "indirim kuponu alım satım", "promosyon kodu alım satım", "kampanya kupon satış",
        "internet kod alım satım", "gb kod alım satım", "kapak kod alım satım",
        "kod pazarı alım satım", "kupon pazarı alım satım", "çek pazarı alım satım",
        "kupon borsa alım satım", "kod borsa alım satım", "çek borsa alım satım",
        "kupon market alım satım", "kod market alım satım", "çek market alım satım",
        "kupon dükkanı satış", "kod dükkanı satış", "dijital pazar alım satım"
    ]

    for kw in exact_style_keywords:
        try:
            res = await client(SearchRequest(q=kw, limit=50))
            for chat in res.chats:
                u = getattr(chat, 'username', None)
                if not u:
                    continue
                u_l = u.lower()
                if u_l in known or getattr(chat, 'broadcast', False):
                    continue
                candidates.add(u_l)
            await asyncio.sleep(1.5)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception:
            pass

    # 3. Username pattern variations of kod / kupon / cek / alsat / ilan
    prefixes = ["kupon", "kod", "cek", "indirim", "firsat", "dijital", "alsat", "ticaret"]
    middles = ["kod", "kupon", "cek", "ilan", "pazar", "market", "alsat", "alim", "satis", "merkez", "depo", "borsa"]
    suffixes = ["tr", "turkiye", "grubu", "grup", "ilanlar", "ilanlari", "resmi", "official", "1", "2", "3", "vip", "paylasim"]

    for p in prefixes:
        for m in middles:
            if p == m:
                continue
            cand1 = f"{p}{m}".lower()
            cand2 = f"{p}_{m}".lower()
            if cand1 not in known:
                candidates.add(cand1)
            if cand2 not in known:
                candidates.add(cand2)
            for s in suffixes:
                cand3 = f"{p}{m}{s}".lower()
                cand4 = f"{p}_{m}_{s}".lower()
                cand5 = f"{p}{m}_{s}".lower()
                if cand3 not in known:
                    candidates.add(cand3)
                if cand4 not in known:
                    candidates.add(cand4)
                if cand5 not in known:
                    candidates.add(cand5)

    candidate_list = sorted(list(candidates - known))
    print(f"\n[*] Toplam taranacak yeni kupon/kod adayı: {len(candidate_list)}")

    # 4. Inspect candidates
    approved_new = []
    
    EXCLUDE_TERMS = [
        "brawl", "pes", "efootball", "roblox", "pubg", "free fire", "valorant",
        "metin2", "zula", "lol", "fifa", "fc 24", "fc 25", "fc 26", "wolfteam",
        "koleksiyon", "paylaş kazan", "kaydetme", "takip et kazan",
        "iddaa", "bahis", "casino", "slot", "rulet", "canlı bahis", "rtp",
        "sıcak fırsatlar", "fırsat avcısı", "günün fırsatları", "amazon fırsat",
        "gayrimenkul", "emlak", "ev alım", "oto alım"
    ]

    for idx, u in enumerate(candidate_list, 1):
        try:
            entity = await client.get_entity(u)
            full = await client(GetFullChannelRequest(entity))
            full_chat = full.full_chat
            
            title = getattr(entity, 'title', '') or ''
            about = getattr(full_chat, 'about', '') or ''
            members = getattr(full_chat, 'participants_count', 0) or 0
            slowmode = getattr(full_chat, 'slowmode_seconds', 0) or 0
            is_megagroup = getattr(entity, 'megagroup', False) or getattr(entity, 'gigagroup', False)
            
            if getattr(entity, 'broadcast', False) or not is_megagroup or members < 60:
                continue
                
            combined = f"{title}\n{about}".lower()
            if any(et in combined for et in EXCLUDE_TERMS):
                continue
                
            banned = getattr(full_chat, 'default_banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
                
            messages = await client.get_messages(entity, limit=25)
            if not messages:
                continue
                
            senders = [m.sender_id for m in messages if m and m.sender_id]
            if len(messages) >= 10 and len(set(senders)) <= 2:
                continue
                
            msg_texts = [m.text for m in messages if m and m.text]
            combined_msgs = "\n".join(msg_texts).lower()
            
            if any(et in combined_msgs for et in ["koleksiyon kaydet", "koleksiyonuma tıkla", "paylaş kazan link"]):
                continue
                
            game_msg_cnt = sum(1 for t in msg_texts if any(gt in t.lower() for gt in ["brawl", "pes", "pubg", "roblox", "valorant", "free fire"]))
            if len(msg_texts) > 0 and (game_msg_cnt / len(msg_texts)) > 0.25:
                continue
                
            kupon_kod_hits = [k for k in ["kupon", "kod", "çek", "cek", "yemeksepeti", "migros", "getir", "indirim", "kapak", "turna", "bilet", "tod", "gb", "internet", "daha daha", "tıkla gelsin", "fırsat", "hesap", "lisans"] if k in combined_msgs + combined]
            if not kupon_kod_hits:
                continue
                
            samples = []
            for t in msg_texts:
                tl = t.lower()
                if any(kh in tl for kh in ["satılık", "satıyorum", "alınır", "alıyorum", "fiyat", "tl", "₺", "stok", "dm", "kupon", "kod", "çek", "cek"]):
                    clean = t.replace("\n", " ").strip()
                    if len(clean) > 120:
                        clean = clean[:117] + "..."
                    if clean and len(samples) < 3:
                        samples.append(clean)
                        
            rec = {
                "username": u,
                "title": title,
                "members": members,
                "slowmode_seconds": slowmode,
                "signals": kupon_kod_hits,
                "about": about.replace("\n", " ")[:200],
                "sample_ads": samples,
                "link": f"https://t.me/{u}"
            }
            approved_new.append(rec)
            print(f"🎯 ONAYLANDI: @{u:22s} | {title[:30]} | {members} üye | Sinyaller: {', '.join(kupon_kod_hits[:3])}")
        except Exception:
            pass
        await asyncio.sleep(0.8)

    await client.disconnect()
    
    approved_new.sort(key=lambda x: x["members"], reverse=True)
    
    with open("yeni_birebir_kupon_kod_satim_gruplari.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_found": len(approved_new),
            "groups": approved_new
        }, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"✅ BİREBİR KUPON KOD SATIM TARAMASI BİTTİ! Bulunan: {len(approved_new)}")
    print(f"=======================================================\n")

if __name__ == '__main__':
    asyncio.run(find_sibling_and_similar_groups())
