#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Dizinleri ve Arama Motoru Harvester
grupbul.com, tg-cat.com, igruplari.com, telegramgruplari.org vb. dizinlerde
kupon, kod, çek, ticaret, alım satım, hesap, referans, reklam aramalarını yapar.
"""

import sys
import os
import re
import json
import time
import glob
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
}

# 1. Mevcut Bilinen Grupları Yükle
known_usernames = set()
for fpath in glob.glob("cached_groups_*.json") + [
    "groups_pure_account_trading.json",
    "pure_account_code_approved.json",
    "ultimate_approved_groups.json",
    "yeni_birebir_hedef_gruplar.json",
    "100_tam_dogrulanmis_kupon_kod_gruplari.json",
    "exhaustive_excluded_groups.json"
]:
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        u = item.get("username") if isinstance(item, dict) else str(item)
                        if u:
                            known_usernames.add(u.replace("@", "").lower().strip())
                elif isinstance(data, dict):
                    for k in data.keys():
                        known_usernames.add(str(k).replace("@", "").lower().strip())
        except Exception:
            pass

KEYWORDS = [
    "kupon", "çek", "kod", "indirim", "yemeksepeti", "trendyol", "hesap",
    "ticaret", "alım satım", "al sat", "dijital", "lisans", "referans",
    "reklam", "yardımlaşma", "smm", "takipçi", "dolap", "letgo", "pazar"
]

def search_grupbul(kw):
    found = set()
    try:
        url = f"https://www.grupbul.com/telegram-gruplari/?s={urllib.parse.quote(kw)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    found.add(u)
    except Exception:
        pass
    return found

def search_igruplari(kw):
    found = set()
    try:
        url = f"https://igruplari.com/?s={urllib.parse.quote(kw)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    found.add(u)
    except Exception:
        pass
    return found

def search_tgcat(kw):
    found = set()
    try:
        url = f"https://tg-cat.com/search?q={urllib.parse.quote(kw)}&lang=tr"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    found.add(u)
    except Exception:
        pass
    return found

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
                "brawl stars", "clash royale", "pes mobile", "efootball", "free fire", "wolfteam"
            ]
            for bad in bad_keywords:
                if bad in full_text:
                    return None
            
            if is_group and members >= 40:
                pos_keywords = [
                    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
                    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
                    "lisans", "key", "windows", "office", "smm", "panel", "takipçi", "sosyal medya",
                    "dijital", "ticaret", "alım", "satım", "satış", "satis", "fiyat", "ilan", "pazar",
                    "referans", "reklam", "yardımlaşma", "link", "kasma", "dolap", "letgo"
                ]
                score = sum(1 for w in pos_keywords if w in full_text)
                
                category = "Ticaret & Alım-Satım"
                if any(w in full_text for w in ["kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol"]):
                    category = "Kupon, Kod & Çek Pazarı"
                elif any(w in full_text for w in ["lisans", "dijital", "chatgpt", "canva", "netflix", "adobe", "hesap"]):
                    category = "Dijital Hesap & Lisans"
                elif any(w in full_text for w in ["referans", "reklam", "kasma", "yardımlaşma"]):
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
    print("[*] Dizin tarama motoru başlatılıyor...")
    raw_candidates = set()
    for kw in KEYWORDS:
        r1 = search_grupbul(kw)
        r2 = search_igruplari(kw)
        r3 = search_tgcat(kw)
        comb = r1.union(r2).union(r3)
        raw_candidates.update(comb)
        print(f"  -> '{kw}': +{len(comb)} aday bulundu (Toplam: {len(raw_candidates)})")
        time.sleep(0.3)

    new_candidates = [u for u in raw_candidates if u.lower() not in known_usernames]
    print(f"\n[*] Toplam Yeni Dizin Adayı: {len(new_candidates)}")
    print(f"[*] Telegram Web Prober başlatılıyor (12 Thread)...")

    verified_groups = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(inspect_username, u): u for u in new_candidates}
        for future in as_completed(futures):
            res = future.result()
            if res:
                verified_groups.append(res)
                print(f"  [+] BULUNDU: @{res['username']:28s} | {res['members']:>6d} üye | {res['category']:30s} | {res['title'][:35]}")

    output_file = "dizin_kesfedilen_gruplar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] {len(verified_groups)} grup başarıyla kaydedildi -> {output_file}")

if __name__ == "__main__":
    main()
