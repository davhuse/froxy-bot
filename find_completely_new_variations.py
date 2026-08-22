#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tamamen Sıfır / Daha Önce Hiç Görülmemiş Hedef Grup Keşif Motoru
Projedeki TÜM geçmiş dosyalarda (arşivler, blacklist, loglar, dump'lar) var olan
tüm kullanıcı adlarını toplar ve şu anki hedef listemizin kelimelerinden
yeni ve henüz hiç bulunmamış grupları aratıp Telegram Web üzerinden doğrular.
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

# 1. Projedeki TÜM geçmiş kullanıcı adlarını topla
all_historical_usernames = set()
for fpath in glob.glob("*.json") + glob.glob("*.txt") + glob.glob("*.py"):
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            matches = re.findall(r'(?:t\.me/|@)([a-zA-Z0-9_]{4,32})', text)
            for m in matches:
                u = m.lower().strip()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    all_historical_usernames.add(u)
    except Exception:
        pass

print(f"[*] Tüm Proje Geçmişinde Daha Önce Görülmüş Kullanıcı Adı Sayısı: {len(all_historical_usernames)}")

# 2. Şu anki hedef listemizdeki 46 grup ve bunların varyasyon kombinasyonları
BASE_TERMS = [
    "kupon", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "migros", "getir",
    "ticaret", "alimsatim", "pazar", "sanalticaret", "sanalpazar", "serbestticaret",
    "dijital", "lisans", "abonelik", "hesap", "chatgpt", "canva", "adobe",
    "referans", "reklam", "kasma", "yardimlasma", "linkpaylasim", "smm", "takipci", "dolap", "letgo"
]

# Çok çeşitli varyasyon ekleri ve kombinasyonları
SUFFIXES_1 = ["", "tr", "turkiye", "official", "resmi", "grup", "grubu", "chat", "sohbet", "pazar", "pazari", "merkezi", "alemi", "dunyasi", "platformu", "borsasi", "kulubu", "alani"]
SUFFIXES_2 = ["", "1", "2", "3", "0", "01", "10", "11", "2026", "24", "online", "vip", "pro"]

def generate_fresh_variations():
    candidates = set()
    
    # 2'li kombinasyonlar: örn kuponsatis, ceksat, kodalimsatim, sanalpazar, lisansalimsatim, referanskasma...
    pairs = [
        ("kupon", "satis"), ("kupon", "alimsatim"), ("kupon", "pazari"), ("kupon", "kod"), ("kupon", "cek"),
        ("kupon", "paylasim"), ("kupon", "market"), ("kupon", "borsasi"), ("kupon", "vadisi"), ("kupon", "merkezi"),
        ("cek", "satis"), ("cek", "alimsatim"), ("cek", "pazari"), ("cek", "sat"), ("cek", "kod"),
        ("kod", "satis"), ("kod", "alimsatim"), ("kod", "pazari"), ("kod", "market"), ("kod", "paylasim"),
        ("indirim", "kuponu"), ("indirim", "kodu"), ("indirim", "pazari"), ("indirim", "alimsatim"), ("indirim", "firsat"),
        ("yemek", "kuponu"), ("yemeksepeti", "kupon"), ("trendyol", "kupon"), ("trendyol", "indirim"), ("migros", "kupon"),
        ("ticaret", "grubu"), ("ticaret", "pazari"), ("ticaret", "forumu"), ("ticaret", "merkezi"), ("ticaret", "alemi"),
        ("ticaret", "sohbet"), ("ticaret", "chat"), ("ticaret", "borsasi"), ("ticaret", "platformu"),
        ("alimsatim", "grubu"), ("alimsatim", "pazari"), ("alimsatim", "merkezi"), ("alimsatim", "chat"), ("alimsatim", "turkiye"),
        ("sanal", "ticaret"), ("sanal", "pazar"), ("sanal", "alimsatim"), ("serbest", "ticaret"), ("serbest", "pazar"),
        ("dijital", "lisans"), ("dijital", "hesap"), ("dijital", "pazar"), ("dijital", "abonelik"), ("dijital", "market"),
        ("lisans", "satis"), ("lisans", "pazari"), ("lisans", "alimsatim"), ("abonelik", "pazari"), ("hesap", "satis"),
        ("hesap", "alimsatim"), ("hesap", "pazari"), ("chatgpt", "hesap"), ("canva", "pro"), ("adobe", "lisans"),
        ("referans", "reklam"), ("referans", "kasma"), ("referans", "yardimlasma"), ("referans", "grubu"), ("referans", "paylasim"),
        ("reklam", "referans"), ("reklam", "kasma"), ("reklam", "yardimlasma"), ("reklam", "pazari"), ("reklam", "chat"),
        ("link", "paylasim"), ("link", "paylasimi"), ("ucretsiz", "reklam"), ("ucretsiz", "referans"),
        ("smm", "ticaret"), ("smm", "pazar"), ("smm", "alimsatim"), ("takipci", "satis"), ("takipci", "pazari"),
        ("dolap", "ilan"), ("dolap", "satis"), ("dolap", "pazari"), ("letgo", "ilan"), ("letgo", "satis")
    ]

    for p1, p2 in pairs:
        # Bitişik ve altçizgili
        combos = [f"{p1}{p2}", f"{p1}_{p2}", f"{p2}{p1}", f"{p2}_{p1}"]
        for c in combos:
            for s1 in SUFFIXES_1:
                for s2 in SUFFIXES_2:
                    var1 = f"{c}{s1}{s2}".strip("_")
                    var2 = f"{c}_{s1}_{s2}".strip("_").replace("__", "_")
                    var3 = f"{c}_{s1}".strip("_")
                    var4 = f"{c}{s2}".strip("_")
                    for v in [var1, var2, var3, var4]:
                        clean = re.sub(r'[^a-zA-Z0-9_]', '', v).lower()
                        if 5 <= len(clean) <= 32 and not clean.startswith('_') and not clean.endswith('_'):
                            # DAHA ÖNCE ASLA GÖRÜLMEMİŞ OLMALI
                            if clean not in all_historical_usernames:
                                candidates.add(clean)

    return candidates

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
            
            if is_group and members >= 30:
                pos_keywords = [
                    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
                    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
                    "lisans", "key", "windows", "office", "smm", "panel", "takipçi", "sosyal medya",
                    "dijital", "ticaret", "alım", "satım", "satış", "satis", "fiyat", "ilan", "pazar",
                    "referans", "reklam", "yardımlaşma", "link", "kasma", "dolap", "letgo"
                ]
                score = sum(1 for w in pos_keywords if w in full_text)
                
                category = "Ticaret & Alım-Satım"
                if any(w in full_text for w in ["kupon", "çek", "cek", "kod", "yemeksepeti", "trendyol", "migros"]):
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
    variations = generate_fresh_variations()
    print(f"[*] Tamamen Sıfır (Daha Önce Hiç Taranmamış) Üretilen Varyasyon Sayısı: {len(variations)}")
    print(f"[*] Telegram Web Prober başlatılıyor (20 İş Parçacığı / Thread)...")

    verified_groups = []
    checked = 0
    total = len(variations)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(inspect_username, u): u for u in variations}
        for future in as_completed(futures):
            checked += 1
            if checked % 250 == 0 or checked == total:
                print(f"  -> İlerleme: {checked}/{total} kontrol edildi... (Şu ana kadar {len(verified_groups)} SIFIR YENİ grup bulundu)")
            res = future.result()
            if res:
                verified_groups.append(res)
                print(f"  [+] BULUNDU (SIFIR YENİ): @{res['username']:28s} | {res['members']:>6d} üye | {res['category']:30s} | {res['title'][:35]}")

    verified_groups.sort(key=lambda x: (x.get('score', 0), x.get('members', 0)), reverse=True)

    output_file = "tamamen_sifir_yeni_hedef_gruplar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"TOPLAM BULUNAN TERTEMİZ / SIFIR YENİ HEDEF GRUP SAYISI: {len(verified_groups)}")
    print(f"Sonuçlar '{output_file}' dosyasına kaydedildi.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
