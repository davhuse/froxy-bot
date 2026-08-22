#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hedef Liste Varyasyon Grubu Keşif ve Doğrulama Motoru
Mevcut hedef listesindeki kupon, kod, çek, ticaret, sanal pazar, dijital hesap,
referans/reklam ve alım-satım gruplarının adlarının ve başlıklarının farklı
varyasyonlarını aratır, Telegram web üzerinden doğrular ve yeni grupları raporlar.
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

print(f"[*] Mevcut Veritabanındaki Bilinen Grup/Kanal Sayısı: {len(known_usernames)}")

# 2. Hedef Grupların İsim & Başlık Varyasyon Arama Kelimeleri
SEARCH_QUERIES = [
    # Kupon & Kod & Çek Varyasyonları
    'site:t.me "kupon" "kod" "satış" telegram',
    'site:t.me "kupon çek" "alım satım" telegram',
    'site:t.me "indirim kuponu" "çek satış" telegram',
    'site:t.me "kupon alım satım" telegram',
    'site:t.me "kod ve kupon" telegram',
    'site:t.me "çek sat" "kupon" telegram',
    'site:t.me "yemek kuponu" telegram',
    'site:t.me "yemeksepeti" "kupon" "satış" telegram',
    'site:t.me "trendyol yemek" "kupon" telegram',
    'site:t.me "migros" "indirim kodu" telegram',
    'site:t.me "kupon pazarı" telegram',
    'site:t.me "indirim kodları" "alım satım" telegram',
    'site:t.me "hesap kod satış" telegram',
    'site:t.me "kupon market" telegram',
    'site:t.me "çek pazar" telegram',

    # Ticaret & Pazar & Alım Satım Varyasyonları
    'site:t.me "alım satım merkezi" telegram',
    'site:t.me "ticaret grubu" telegram',
    'site:t.me "ticaret forum" telegram',
    'site:t.me "sanal alım satım" telegram',
    'site:t.me "serbest ticaret" telegram',
    'site:t.me "alım satım ticaret" telegram',
    'site:t.me "ticaret pazarı" telegram',
    'site:t.me "ticaret sohbet" "alım satım" telegram',
    'site:t.me "alım satım grubu" telegram',
    'site:t.me "turkey ticaret" telegram',
    'site:t.me "türkiye alım satım" telegram',
    'site:t.me "ticaret alanı" telegram',
    'site:t.me "güvenilir alım satım" telegram',

    # Dijital Lisans, Hesap & Abonelik Varyasyonları
    'site:t.me "dijital lisans" "satış" telegram',
    'site:t.me "dijital abonelik" "hesap" telegram',
    'site:t.me "chatgpt" "hesap satışı" telegram',
    'site:t.me "canva pro" "satış" telegram',
    'site:t.me "adobe" "lisans" telegram',
    'site:t.me "windows key" "office lisans" telegram',
    'site:t.me "sosyal medya alım satım" telegram',
    'site:t.me "takipçi satış" "hesap alım" telegram',
    'site:t.me "smm ticaret" telegram',
    'site:t.me "smm pazar" telegram',
    'site:t.me "instagram hesap alım satım" telegram',
    'site:t.me "tiktok hesap alım satım" telegram',

    # Referans, Reklam & Yardımlaşma Varyasyonları
    'site:t.me "referans reklam" telegram',
    'site:t.me "referans kasma" telegram',
    'site:t.me "reklam ve link paylaşımı" telegram',
    'site:t.me "referans yardımlaşma" telegram',
    'site:t.me "ücretsiz reklam" "referans" telegram',
    'site:t.me "reklam ve referans" telegram',
    'site:t.me "reklam kasma" telegram',
    'site:t.me "referans grubu" telegram',
    'site:t.me "link paylaşım grubu" telegram',

    # İlan & 2. El Varyasyonları
    'site:t.me "dolap ilan" telegram',
    'site:t.me "letgo ilan" telegram',
    'site:t.me "ilan ve satış grubu" telegram',
    'site:t.me "ikinci el alım satım" telegram',
    'site:t.me "sanal pazar" telegram'
]

# Doğrudan Hedef Varyasyon Kullanıcı Adı Adayları (Doğrudan t.me üstünden kontrol edilecek)
DIRECT_USERNAME_PATTERNS = [
    # Kupon / Çek / Kod
    "kuponkodsatis", "kuponkodsatis_tr", "kuponceksatis", "kupon_cek_satis", "kuponcekkod",
    "kuponsatisi", "kuponsatisgrubu", "kuponalimsatim", "kupon_alimsatim", "kuponpazari",
    "kuponvadisi", "kupondeposu", "kuponmarket", "kuponplatformu", "kuponborsasi",
    "ceksatis", "ceksatisgrubu", "cekpazari", "ceksat_tr", "cekalimsatim",
    "indirimkodsatis", "indirimkuponu_tr", "indirimvadisi", "indirimpazari", "indirim_market",
    "yemekkuponlari", "yemeksepetikuponu", "trendyolyemekkupon", "yemekkuponsatis",
    "hesapkodsatis", "dijitalhesappazari", "hesapkuponsatis", "kodvekuponsatis",

    # Ticaret & Alım Satım
    "alimsatimmerkezi", "alimsatimpazari", "alimsatimtr", "alimsatim_turkiye", "alimsatim_grubu",
    "turkiyeticaret", "ticaretgrubu_tr", "ticaretpazari", "ticaretalemi", "ticaretforumu",
    "ticaretplatformu", "serbestticaret", "serbestticaret_tr", "sanalticaret", "sanalpazar_tr",
    "guvenilirticaret", "guveniliralimsatim", "pazaryeri_tr", "pazaralimsatim",

    # Dijital & Sosyal Medya
    "dijitalpazar", "dijitallisans_tr", "dijitalabonelik_tr", "lisanspazari", "abonelikpazari",
    "sosyalmedyaticaret", "sosyalmedyapazari", "smmticaret", "smmpazari", "takipcimarket_tr",
    "hesapalimsatim_tr", "hesappazari_tr",

    # Referans & Reklam
    "referansreklam", "referanskasma", "referansgrubu", "referansyardimlasma", "referanspaylasim",
    "reklamreferans", "reklamkasma", "reklampazari", "reklamgrubutr", "linkpaylasim",
    "linkpaylasimi_tr", "ucretsizreklam_tr", "ucretsizreferans"
]

def search_duckduckgo(query):
    candidates = set()
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    candidates.add(u)
    except Exception:
        pass
    return candidates

def search_bing(query):
    candidates = set()
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            for m in re.finditer(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]{4,32})", html):
                u = m.group(1).lower()
                if u not in {"joinchat", "share", "addstickers", "proxy", "bot", "channel", "telegram", "s", "c", "iv", "html"}:
                    candidates.add(u)
    except Exception:
        pass
    return candidates

def inspect_telegram_group(u):
    """t.me web önizlemesini inceler ve grup niteliklerini çıkarır."""
    url = f"https://t.me/{u}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
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
            
            # Kanal / Grup ayrımı
            is_group = "members" in extra.lower() or "üye" in extra.lower()
            is_channel = "subscribers" in extra.lower() or "abone" in extra.lower()
            
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

            # Filtreler (Bahis, Spam, +18, çocuk oyunları)
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
            
            # Sadece gerçek gruplar (en az 50 üye)
            if is_group and members >= 50:
                # Pozitif ticaret / kupon / kod eşleşmesi puanı
                pos_keywords = [
                    "kupon", "çek", "cek", "kod", "indirim", "yemeksepeti", "trendyol", "getir", "migros",
                    "hesap", "chatgpt", "canva", "netflix", "spotify", "adobe", "gemini", "claude",
                    "lisans", "key", "windows", "office", "smm", "panel", "takipçi", "sosyal medya",
                    "dijital", "ticaret", "alım", "satım", "satış", "satis", "fiyat", "ilan", "pazar",
                    "referans", "reklam", "yardımlaşma", "link", "kasma", "dolap", "letgo"
                ]
                score = sum(1 for w in pos_keywords if w in full_text)
                
                # Grup kategorisi
                category = "Genel Ticaret & Alım-Satım"
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
    print(f"[*] Hedef varyasyon arama motoru başlatılıyor...")
    all_candidates = set(DIRECT_USERNAME_PATTERNS)

    print(f"[*] {len(SEARCH_QUERIES)} arama sorgusu çalıştırılıyor...")
    for idx, q in enumerate(SEARCH_QUERIES, 1):
        ddg_results = search_duckduckgo(q)
        bing_results = search_bing(q)
        combined = ddg_results.union(bing_results)
        all_candidates.update(combined)
        print(f"  [{idx:02d}/{len(SEARCH_QUERIES)}] Sorgu: {q[:45]}... -> +{len(combined)} aday (Toplam Aday: {len(all_candidates)})")
        time.sleep(0.4)

    # Zaten bilinenleri filtrele
    new_candidates = [u for u in all_candidates if u.lower() not in known_usernames]
    print(f"\n[*] Toplam Bulunan Benzersiz Yeni Aday Sayısı: {len(new_candidates)}")
    print(f"[*] Adaylar Telegram Web üzerinden doğrulanıyor (Paralel İşlem)...")

    verified_groups = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(inspect_telegram_group, u): u for u in new_candidates}
        for future in as_completed(futures):
            res = future.result()
            if res:
                verified_groups.append(res)
                print(f"  [+] BULUNDU: @{res['username']:28s} | {res['members']:>6d} üye | {res['category']:30s} | {res['title'][:35]}")

    # Puan ve üye sayısına göre sırala
    verified_groups.sort(key=lambda x: (x.get('score', 0), x.get('members', 0)), reverse=True)

    print(f"\n{'='*80}")
    print(f"TOPLAM KEŞFEDİLEN VE DOĞRULANAN YENİ HEDEF GRUP SAYISI: {len(verified_groups)}")
    print(f"{'='*80}")

    output_file = "yeni_kesfedilen_hedef_gruplar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Sonuçlar '{output_file}' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
