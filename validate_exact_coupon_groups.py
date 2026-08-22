import json
import os
import re
import urllib.request
import html
import sys
import concurrent.futures

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

with open("fresh_candidates_to_audit.json", "r", encoding="utf-8") as f:
    fresh_candidates = json.load(f)

print(f"[*] Toplam Taranacak Taze Aday Sayısı: {len(fresh_candidates)}")

# Strict Negative Filters
BETTING_TERMS = [
    "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet",
    "blackjack", "iddaa", "tipster", "kupon tahmin", "maç tahmin", "oran şikesi",
    "bet", "deneme bonusu", "bonus veren", "pragmatic", "güvenilir bahis",
    "canlı bahis", "roll", "aviator", "zeplin", "canlibahis", "kripto", "forex", "binomo"
]

SPAM_ILLEGAL_TERMS = [
    "cc mail", "carding", "warez", "crack", "nulled", "escort", "porno", "lezbiyen",
    "gay", "ifsa", "ifşa", "tr ifsa", "yetiskin", "18+", "+18", "vip grup", "link tl",
    "illegal", "paneli patlat", "datacı", "muris", "gsm tc", "cc alım", "banka hesap",
    "hesap kiralama", "kiralık hesap", "papara kiralama"
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
    "indirim haberleri", "günün fırsatları", "indirimde al", "indirim paylaşımları",
    "haber kanalı", "koleksiyon kaydetme"
]

# EXACT TARGET SIGNALS (Pure Coupon / Code / Voucher / Food / Account Trade)
COUPON_TRADE_TERMS = [
    "kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "getir", "tıkla gelsin",
    "tiklagelsin", "migros", "money", "turna", "enuygun", "bilet", "pepsi", "kazandrio",
    "cips", "frebayt", "freebayt", "gb", "internet", "hediye çeki", "market çeki",
    "indirim", "kampanya", "satılık", "alınır", "alım", "satım", "takas", "pazar", "ticaret",
    "hesap", "chatgpt", "canva", "netflix", "spotify", "lisans", "key", "windows", "office"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def audit_group(u):
    url = f"https://t.me/{u}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            content_clean = html.unescape(content)
            
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content_clean)
            extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', content_clean, re.DOTALL)
            og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content_clean)
            
            title = og_title.group(1).strip() if og_title else ""
            extra_str = extra.group(1).strip() if extra else ""
            desc = og_desc.group(1).strip() if og_desc else ""
            
            is_group = "members" in extra_str.lower() or "üye" in extra_str.lower() or "online" in extra_str.lower()
            is_channel = "subscribers" in extra_str.lower() or "abone" in extra_str.lower()
            
            # RULE 1: Must be a GROUP, NOT a broadcast channel, NOT a personal user
            if not is_group or is_channel:
                return None
                
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye)', extra_str, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            online_m = re.search(r'([0-9\s]+)\s*online', extra_str, re.IGNORECASE)
            online = 0
            if online_m:
                online = int(re.sub(r'\s+', '', online_m.group(1)))
                
            # RULE 2: NOT DEAD -> At least 60 members and active online presence
            if members < 60 or online < 2:
                return None
                
            combined = f"{u} {title} {desc}".lower()
            
            # RULE 3: Negative filters (Bahis, İllegal, Oyun, Tek Admin İndirim)
            if any(bt in combined for bt in BETTING_TERMS):
                return None
            if any(st in combined for st in SPAM_ILLEGAL_TERMS):
                return None
            if any(gt in combined for gt in GAME_ACCOUNT_TERMS):
                return None
            if any(ad in combined for ad in ADMIN_DEAL_TERMS):
                return None

            # Skip physical cars, clothing, academic
            if any(nt in combined for nt in ["araba", "araç", "arac", "oto alım", "doktora", "yüksek lisans", "tekstil", "kumaş", "eşya", "mobilya"]):
                return None

            # RULE 4: Strict Target Positive Keyword Match
            pos_matches = []
            for pt in COUPON_TRADE_TERMS:
                cnt = combined.count(pt)
                if cnt > 0:
                    pos_matches.append((pt, cnt))
                    
            relevance_score = sum(cnt for _, cnt in pos_matches)
            if relevance_score < 2:
                return None
                
            # Must contain at least one CORE coupon/code/food/trade term in title or username
            has_core_in_name = any(k in f"{u} {title}".lower() for k in [
                "kupon", "çek", "cek", "kod", "indirim", "yemek", "fırsat", "firsat",
                "ticaret", "al-sat", "alsat", "alım", "satım", "satis", "satış", "pazar",
                "market", "hesap", "lisans", "key", "internet", "gb", "smm", "referans"
            ])
            if not has_core_in_name:
                return None

            # Sub-category classification
            category = "Kupon, Çek & Kod Alım-Satım Pazarı"
            if any(k in combined for k in ["yemeksepeti", "tıkla gelsin", "getir", "migros", "yemek"]):
                category = "Yemeksepeti, Market & Yemek Kuponları"
            elif any(k in combined for k in ["turna", "enuygun", "bilet"]):
                category = "Bilet, Seyahat & İndirim Kodları"
            elif any(k in combined for k in ["pepsi", "kazandrio", "cips", "gb", "internet", "bedava internet"]):
                category = "İnternet GB & Kapak/Cips Kodları"
            elif any(k in combined for k in ["chatgpt", "canva", "netflix", "spotify", "hesap", "account"]):
                category = "Premium Hesap & Dijital Satış"
            elif any(k in combined for k in ["windows", "lisans", "office", "key"]):
                category = "Lisans & Key & Yazılım"
            elif any(k in combined for k in ["smm", "panel", "takipçi"]):
                category = "SMM & Sosyal Medya Hizmetleri"
            elif any(k in combined for k in ["ticaret", "alım", "satım", "pazar", "al sat"]):
                category = "Genel Alım-Satım & İlan Ticareti"

            return {
                "username": u,
                "title": title,
                "category": category,
                "members": members,
                "online": online,
                "relevance_score": relevance_score,
                "matched_keywords": [p[0] for p in pos_matches[:8]],
                "about_description": desc[:200] if desc else "N/A",
                "t_me_link": f"https://t.me/{u}"
            }
    except Exception:
        return None

def main():
    print(f"[*] 3.813 Taze Aday Arasında 1'e 1 Birebir Eşleşen Canlı Gruplar Denetleniyor...", flush=True)
    
    approved = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        future_to_uname = {executor.submit(audit_group, uname): uname for uname in fresh_candidates}
        checked = 0
        for future in concurrent.futures.as_completed(future_to_uname):
            checked += 1
            res = future.result()
            if res:
                approved.append(res)
                print(f"[ONAYLANDI ✅ #{len(approved):2d}] @{res['username']:<25} | Üye: {res['members']:<6} | Online: {res['online']:<4} | {res['category']}", flush=True)
            if checked % 500 == 0:
                print(f"  -> {checked}/{len(fresh_candidates)} aday denetlendi... (Onaylanan: {len(approved)})", flush=True)

    # Sort by online count, members, and relevance
    approved.sort(key=lambda x: (-x["online"], -x["members"], -x["relevance_score"]))
    
    print(f"\n=======================================================", flush=True)
    print(f"🎉 TOPLAM DOĞRULANMIŞ BİREBİR HEDEF GRUP SAYISI: {len(approved)}", flush=True)
    print(f"=======================================================\n", flush=True)

    with open("birebir_saf_kupon_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open("birebir_saf_kupon_kod_gruplari.txt", "w", encoding="utf-8") as f:
        for g in approved:
            f.write(f"{g['username']}\n")

    print("[*] Kaydedildi: 'birebir_saf_kupon_kod_gruplari.json' ve 'birebir_saf_kupon_kod_gruplari.txt'", flush=True)

if __name__ == "__main__":
    main()
