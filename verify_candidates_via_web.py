import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import time

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

with open("extracted_raw_candidates.json", "r", encoding="utf-8") as f:
    raw_candidates = json.load(f)

print(f"[*] Toplam Değerlendirilecek Ham Aday Sayısı: {len(raw_candidates)}")

BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto sinyal"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım"
]

GAME_ACCOUNT_TERMS = [
    "brawl stars", "brawlstars", "clash royale", "clash of clans", "pes mobile",
    "efootball", "free fire", "wolfteam", "growtopia", "standoff", "supercell",
    "mobile legends", "mlbb"
]

ADMIN_DEAL_TERMS = [
    "sıcak fırsatlar", "sicak firsatlar", "fırsat avcısı", "firsat avcisi",
    "amazon fırsat", "affiliate", "sadece admin paylaşır", "yalnızca admin",
    "mesaj yazmak yasaktır", "sohbete kapalı", "paylaşım kanalı", "duyuru kanalı",
    "indirim haberleri", "günün fırsatları"
]

POSITIVE_TERMS = [
    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
    "lisans", "key", "windows", "office", "antivirüs", "vpn", "smm", "panel",
    "takipçi", "sosyal medya", "dijital", "ticaret", "alım", "satım", "satış", "satis",
    "fiyat", "tl", "₺", "stok", "dm", "özelden", "teslim", "güvenli", "aracı", "ilan", "devir",
    "pazar", "market", "al sat", "tedarik", "shopier", "hizmet"
]

def inspect_url(u):
    url = f"https://t.me/{u}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            title_m = re.search(r'<div class="tgme_page_title"[^>]*><span[^>]*>(.*?)</span>', html, re.DOTALL)
            if not title_m:
                title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            title = title_m.group(1).strip() if title_m else ""
            
            extra_m = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.DOTALL)
            extra = extra_m.group(1).strip() if extra_m else ""
            
            desc_m = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', html, re.DOTALL)
            if not desc_m:
                desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            desc = desc_m.group(1).strip() if desc_m else ""
            
            title = re.sub(r'<[^>]+>', '', title).strip()
            desc = re.sub(r'<[^>]+>', ' ', desc).strip()
            
            is_group = "members" in extra.lower() or "üye" in extra.lower()
            is_channel = "subscribers" in extra.lower() or "abone" in extra.lower()
            
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye)', extra, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            online_m = re.search(r'([0-9\s]+)\s*online', extra, re.IGNORECASE)
            online = 0
            if online_m:
                online = int(re.sub(r'\s+', '', online_m.group(1)))
                
            return {
                "username": u,
                "title": title,
                "extra": extra,
                "desc": desc,
                "is_group": is_group,
                "is_channel": is_channel,
                "members": members,
                "online": online
            }
    except Exception:
        return None

verified_groups = []

for u, occurrences in raw_candidates.items():
    info = inspect_url(u)
    if not info:
        continue
    
    # 1. Must be a Group, not a single user, not a channel
    if not info["is_group"] or info["is_channel"]:
        continue
        
    # 2. Member filter: At least 60 members
    if info["members"] < 60:
        continue
        
    title = info["title"]
    desc = info["desc"]
    combined_meta = f"{title}\n{desc}".lower()
    
    # 3. Negative filters on title & description
    if any(bt in combined_meta for bt in BETTING_TERMS):
        continue
    if any(st in combined_meta for st in SPAM_ILLEGAL_TERMS):
        continue
    if any(gt in combined_meta for gt in GAME_ACCOUNT_TERMS):
        continue
    if any(ad in combined_meta for ad in ADMIN_DEAL_TERMS):
        continue

    # 4. Message content analysis from occurrences in seed groups
    all_context = " \n ".join(occ["text"].lower() for occ in occurrences)
    
    # Filter betting in context
    if any(bt in all_context for bt in BETTING_TERMS):
        continue
    if any(st in all_context for st in SPAM_ILLEGAL_TERMS):
        continue

    # 5. Positive relevance check
    pos_matches = []
    full_blob = f"{combined_meta}\n{all_context}"
    for pt in POSITIVE_TERMS:
        cnt = full_blob.count(pt)
        if cnt > 0:
            pos_matches.append((pt, cnt))
            
    relevance_score = sum(cnt for _, cnt in pos_matches)
    if relevance_score < 2:
        continue
        
    # 6. Sample messages
    samples = []
    for occ in occurrences:
        txt = occ["text"].strip()
        if len(txt) > 10 and txt not in samples:
            clean_txt = " ".join(txt.split())
            if len(clean_txt) > 120:
                clean_txt = clean_txt[:120] + "..."
            samples.append(clean_txt)
            if len(samples) >= 3:
                break

    # 7. Category determination
    category = "Dijital Ticaret & Pazar"
    if any(k in full_blob for k in ["kupon", "çek", "cek", "yemeksepeti", "trendyol", "getir", "migros"]):
        category = "Kupon & Çek & Kod Pazarı"
    elif any(k in full_blob for k in ["lisans", "windows", "office", "antivirüs", "key", "kaspersky"]):
        category = "Lisans & Key & Yazılım"
    elif any(k in full_blob for k in ["chatgpt", "canva", "netflix", "spotify", "hesap", "gmail"]):
        category = "Premium Hesap & Dijital Ürün"
    elif any(k in full_blob for k in ["smm", "takipçi", "sosyal medya"]):
        category = "SMM & Sosyal Medya Hizmetleri"

    group_res = {
        "username": u,
        "title": title,
        "category": category,
        "members": info["members"],
        "online": info["online"],
        "found_in_seed_groups": list(set(occ["found_in"] for occ in occurrences)),
        "occurrence_count": len(occurrences),
        "relevance_score": relevance_score,
        "matched_keywords": [p[0] for p in pos_matches[:8]],
        "about_description": desc[:150] if desc else "N/A",
        "sample_trading_messages": samples,
        "t_me_link": f"https://t.me/{u}"
    }
    
    verified_groups.append(group_res)
    print(f"[ONAYLANDI ✅ #{len(verified_groups)}] @{u} | Başlık: {title[:28]} | Üye: {info['members']} (Online: {info['online']}) | Kat: {category}")
    time.sleep(0.2)

verified_groups.sort(key=lambda x: (-x["online"], -x["members"], -x["relevance_score"]))

print(f"\n=======================================================")
print(f"🎉 TOPLAM DOĞRULANAN YENİ HEDEF GRUP SAYISI: {len(verified_groups)}")
print(f"=======================================================\n")

with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
    json.dump(verified_groups, f, ensure_ascii=False, indent=2)

with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
    for g in verified_groups:
        f.write(f"{g['username']}\n")

print("[*] Sonuçlar 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt' dosyalarına kaydedildi.")
