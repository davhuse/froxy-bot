#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arşiv & Varyasyon Tam Havuz Doğrulayıcısı
Tüm arşiv dosyalarındaki adayları toplar, hedef listemizdeki kategorilerle
(Kupon, Kod, Çek, Ticaret, Sanal Pazar, Dijital Hesap/Lisans, Referans/Reklam)
birebir eşleşen ve şu an canlı olan grupları Telegram Web üzerinden doğrular.
"""

import sys
import os
import re
import json
import glob
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# 1. Şu an aktif katıldığımız / hedefte olan gruplar
current_target_usernames = set()
for fpath in glob.glob("cached_groups_*.json"):
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                u = item.get("username")
                if u:
                    current_target_usernames.add(u.replace("@", "").lower().strip())
    except Exception:
        pass

print(f"[*] Aktif Katılınmış Hedef Grup Sayısı: {len(current_target_usernames)}")

# 2. Tüm arşiv ve havuz dosyalarından adayları topla
raw_pool = set()
archive_files = glob.glob("*.json")
for fpath in archive_files:
    if fpath.startswith("cached_groups_") or fpath in ["blacklist_meta.json", "group_failures.json"]:
        continue
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and 4 <= len(item) <= 32:
                        raw_pool.add(item.replace("@", "").lower().strip())
                    elif isinstance(item, dict):
                        u = item.get("username") or item.get("user") or item.get("link")
                        if u and isinstance(u, str):
                            # extract username from t.me link or string
                            clean = re.sub(r'https?://t\.me/', '', u).replace('@', '').strip().lower()
                            if 4 <= len(clean) <= 32 and '/' not in clean:
                                raw_pool.add(clean)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if 4 <= len(k) <= 32 and not k.startswith('-100') and not k.isdigit():
                        raw_pool.add(k.replace("@", "").lower().strip())
    except Exception:
        pass

# Şu anki hedefleri havuzdan çıkar
unjoined_candidates = [u for u in raw_pool if u not in current_target_usernames and not u.startswith('_')]
print(f"[*] Toplam Havuzdan Çıkarılan Yeni Aday Sayısı: {len(unjoined_candidates)}")

def inspect_username(u):
    url = f"https://t.me/{u}"
    req = urllib.request.Request(url, headers=HEADERS)
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
            members = 0
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye)', extra, re.IGNORECASE)
            if mem_m:
                try:
                    members = int(re.sub(r'\s+', '', mem_m.group(1)))
                except ValueError:
                    members = 0
                    
            online = 0
            online_m = re.search(r'([0-9\s]+)\s*online', extra, re.IGNORECASE)
            if online_m:
                try:
                    online = int(re.sub(r'\s+', '', online_m.group(1)))
                except ValueError:
                    online = 0

            full_text = f"{title} {desc}".lower()
            
            bad_keywords = [
                "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet", "blackjack",
                "iddaa", "tipster", "kupon tahmin", "maç tahmin", "deneme bonusu", "pragmatic", "aviator",
                "cc mail", "carding", "warez", "crack", "escort", "porno", "ifsa", "ifşa", "yetiskin", "18+", "+18",
                "brawl stars", "clash royale", "pes mobile", "efootball", "free fire", "wolfteam", "growtopia"
            ]
            for bad in bad_keywords:
                if bad in full_text:
                    return None
            
            # Sadece hedef kitlemizle tam uyuşan gruplar
            if is_group and members >= 50:
                pos_keywords = [
                    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
                    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
                    "lisans", "key", "windows", "office", "smm", "panel", "takipçi", "sosyal medya",
                    "dijital", "ticaret", "alım", "satım", "satış", "satis", "fiyat", "ilan", "pazar",
                    "referans", "reklam", "yardımlaşma", "link", "kasma", "dolap", "letgo"
                ]
                score = sum(1 for w in pos_keywords if w in full_text)
                
                # En az 1 hedef anahtar kelime eşleşmesi olmalı
                if score >= 1:
                    category = "Ticaret & Alım-Satım"
                    if any(w in full_text for w in ["kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "migros", "indirim"]):
                        category = "Kupon, Kod & Çek Pazarı"
                    elif any(w in full_text for w in ["lisans", "dijital", "chatgpt", "canva", "netflix", "adobe", "hesap"]):
                        category = "Dijital Hesap & Lisans"
                    elif any(w in full_text for w in ["referans", "reklam", "kasma", "yardımlaşma", "link"]):
                        category = "Referans, Reklam & Yardımlaşma"
                    elif any(w in full_text for w in ["sosyal medya", "smm", "takipçi"]):
                        category = "Sosyal Medya & SMM"
                    elif any(w in full_text for w in ["dolap", "letgo", "ilan"]):
                        category = "İlan & 2. El Pazarı"

                    return {
                        "username": u,
                        "title": title,
                        "members": members,
                        "online": online,
                        "category": category,
                        "score": score,
                        "desc": desc[:200]
                    }
    except Exception:
        pass
    return None

def main():
    print(f"[*] Havuz Telegram Web üzerinden doğrulanıyor (20 İş Parçacığı / Thread)...")
    verified_groups = []
    checked = 0
    total = len(unjoined_candidates)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(inspect_username, u): u for u in unjoined_candidates}
        for future in as_completed(futures):
            checked += 1
            if checked % 100 == 0 or checked == total:
                print(f"  -> İlerleme: {checked}/{total} kontrol edildi... (Şu ana kadar {len(verified_groups)} uygun grup bulundu)")
            res = future.result()
            if res:
                verified_groups.append(res)
                print(f"  [+] BULUNDU: @{res['username']:28s} | {res['members']:>6d} üye | {res['category']:30s} | {res['title'][:35]}")

    # Sıralama
    verified_groups.sort(key=lambda x: (x.get('score', 0), x.get('members', 0)), reverse=True)

    output_file = "tum_havuzdan_dogrulanan_yeni_hedef_gruplar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"BAŞARIYLA DOĞRULANAN YENİ HEDEF GRUBU SAYISI: {len(verified_groups)}")
    print(f"Sonuçlar '{output_file}' dosyasına kaydedildi.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
