#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hedef Liste Varyasyon Prober & Discovery Engine
Hedef listemizdeki grupların kullanıcı adları ve başlıklarından yola çıkarak
yüzlerce doğrudan isim varyasyonu (sayı, ek, tr, sohbet, pazar, vs.) üretir ve
Telegram web üzerinden anlık doğrular.
"""

import sys
import os
import re
import json
import time
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

print(f"[*] Mevcut Bilinen Grup/Kanal Sayısı: {len(known_usernames)}")

# 2. Hedef Listemizdeki Kök İsimler (Base Slugs)
BASE_SLUGS = [
    # Kupon / Kod / Çek / İndirim
    "alimsatimmerkezi", "alimsatimmerkezi", "alimsatimpazari", "alimsatimtr",
    "alisverisforumu", "alisverisforumuguncel", "alisverispazari", "alisverisdunyasi",
    "ceksatkupon", "ceksat", "ceksatis", "cekkod", "cekkodsatis",
    "indirimkodu", "indirimkodusatis", "indirimkuponu", "indirimkodlari", "indirimpazari", "indirimlisi",
    "kuponceksatisi", "kuponceksatis", "kuponcekkod", "kuponcekkodsatis",
    "kuponhesapsatis", "kuponhesap", "hesapkuponsatis", "hesapkupon",
    "kuponsatimalim", "kuponalimsatim", "kuponalimsatimi", "kuponalimsatimtr",
    "kuponsatisgrup", "kuponsatisgrubu", "kuponsatislari", "kuponsatisi",
    "kodsatisi", "kodsatis", "kodvekupon", "kuponvekod", "kuponkod", "kuponkodsatis",
    "yucekuponsatis", "yucekupon", "mukyemek", "yemekkuponu", "yemekkuponsatis",
    "yemeksepetikupon", "trendyolyemekkupon", "migroskupon", "yemekkuponlari",

    # Ticaret / Pazar / Alım Satım
    "ticar4t", "ticaretgrubu", "ticaretgruptr", "turkiyeticaret", "ticaretforumu", "ticaretforumofficial",
    "ticaretguvenilir", "guvenilirticaret", "guveniliralimsatim", "guvenlipazar",
    "sanalalimsatim", "sanalalimsatimticaret", "sanalticaret", "sanalpazar",
    "neonticaret", "zeroticaret", "ketenpereticaret", "darktradehouse", "darkhouse",
    "serbestticaret", "serbestticaretgrubu", "serbestpazar", "alimsatimchat", "ticaretchat",
    "chavoticaret", "chavoalimsatim", "ticaretalemi", "ticaretmerkezi", "ticaretborsasi",
    "ticaretplatformu", "turkiyepazari", "pazaryeri", "pazaralimsatim",

    # Dijital Lisans / Hesap / SMM / Takipçi
    "subhub_chat_turkey", "subhubtr", "dijitallisans", "dijitalabonelik", "lisanspazari", "abonelikpazari",
    "sosyalmedyaalimsatim", "sosyalmedyaalimsatimticaret", "sosyalmedyaticaret", "sosyalmedyapazari",
    "smmticaret", "smmpazari", "smmmarket", "smmalimsatim",
    "takipcisatiyor", "takipcisatis", "takipcialimsatim", "takipcipazari",
    "ttingalimsatim", "hesapsatisi", "hesappazari", "hesapalimsatim", "dijitalpazar",

    # Referans / Reklam / Yardımlaşma
    "referansreklam", "referansreklam1", "referansreklam2", "referanskasma", "referansgrubu",
    "referansreklamyardimlasma", "referansyardimlasma", "reklamyardimlasma",
    "reklamonliene", "reklamonline", "referansonline", "reklamreferans", "reklamvereferans", "reklamvereferanss",
    "referanslinkpaylasimi", "referanslinkpaylasimigrup", "linkpaylasimi", "linkpaylasimigrubu",
    "lioncyreklam", "lioncyreklamchat", "reklamchat", "reklampazari", "ucretsizreklam", "ucretsizreferans",

    # İlan / 2. El
    "dolapilanlari", "dolapilan", "dolapsatis", "dolappazari",
    "letgoilanlari", "letgoilan", "letgosatis", "letgopazari", "ikincielalimsatim"
]

# 3. Akıllı Varyasyon Türetme Kuralları
PREFIXES = ["", "tr_", "turk_", "turkey_", "official_", "guncel_", "yeni_", "vip_"]
SUFFIXES = [
    "", "_tr", "tr", "_official", "official", "_grup", "grup", "_grubu", "grubu",
    "_chat", "chat", "_sohbet", "sohbet", "_pazar", "pazar", "_pazari", "pazari",
    "_merkezi", "merkezi", "_alemi", "alemi", "_dunyasi", "dunyasi",
    "1", "2", "3", "0", "01", "10", "11", "2026", "online", "_online"
]

def generate_all_variations():
    candidates = set()
    for base in BASE_SLUGS:
        clean_base = base.replace("_", "").lower()
        candidates.add(clean_base)
        candidates.add(base.lower())
        
        # Sayı ekleme varyasyonları
        for n in ["1", "2", "3", "4", "0", "01", "10", "11", "00", "01", "2026"]:
            candidates.add(f"{clean_base}{n}")
            candidates.add(f"{base}_{n}")
            
        # TR ve Grup ekleme varyasyonları
        for suf in ["tr", "_tr", "grup", "_grup", "grubu", "_grubu", "chat", "_chat", "sohbet", "_sohbet", "pazar", "_pazar", "pazari", "_pazari", "online", "_online", "merkezi", "_merkezi"]:
            candidates.add(f"{clean_base}{suf.replace('_','')}")
            candidates.add(f"{clean_base}_{suf.replace('_','')}")
            candidates.add(f"{clean_base}{suf}")

        # Özel bileşikler
        if "kupon" in clean_base:
            candidates.add(f"{clean_base}kod")
            candidates.add(f"{clean_base}_kod")
            candidates.add(f"{clean_base}cek")
            candidates.add(f"{clean_base}_cek")
            candidates.add(f"{clean_base}alimsatim")
            candidates.add(f"{clean_base}_alimsatim")
        if "ticaret" in clean_base:
            candidates.add(f"{clean_base}alimsatim")
            candidates.add(f"{clean_base}_alimsatim")
            candidates.add(f"{clean_base}sohbet")
            candidates.add(f"{clean_base}_sohbet")
        if "referans" in clean_base:
            candidates.add(f"{clean_base}kasma")
            candidates.add(f"{clean_base}_kasma")
            candidates.add(f"{clean_base}reklam")
            candidates.add(f"{clean_base}_reklam")
            candidates.add(f"{clean_base}link")
            candidates.add(f"{clean_base}_link")

    # Geçerli Telegram kullanıcı adı uzunlukları (5 - 32 karakter, sadece [a-zA-Z0-9_])
    valid_candidates = set()
    for c in candidates:
        c_clean = re.sub(r'[^a-zA-Z0-9_]', '', c).lower()
        if 5 <= len(c_clean) <= 32 and not c_clean.startswith('_') and not c_clean.endswith('_'):
            if c_clean not in known_usernames:
                valid_candidates.add(c_clean)
                
    return valid_candidates

def inspect_username(u):
    """t.me web sayfasından kullanıcı adının bir Telegram Grubu olup olmadığını kontrol eder."""
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

            full_text = f"{title} {desc}".lower()
            
            # Bahis, +18, çocuk oyunları filtresi
            bad_keywords = [
                "bahis", "casino", "slot", "sweet bonanza", "gates of olympus", "rulet", "blackjack",
                "iddaa", "tipster", "kupon tahmin", "maç tahmin", "deneme bonusu", "pragmatic", "aviator",
                "cc mail", "carding", "warez", "crack", "escort", "porno", "ifsa", "ifşa", "yetiskin", "18+", "+18",
                "brawl stars", "clash royale", "pes mobile", "efootball", "free fire", "wolfteam"
            ]
            for bad in bad_keywords:
                if bad in full_text:
                    return None
            
            # Sadece aktif gruplar (en az 40 üye)
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
    variations = generate_all_variations()
    print(f"[*] Üretilen Benzersiz Varyasyon Adayı Sayısı: {len(variations)}")
    print(f"[*] Telegram Web Prober başlatılıyor (16 İş Parçacığı / Thread)...")

    verified_groups = []
    checked = 0
    total = len(variations)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(inspect_username, u): u for u in variations}
        for future in as_completed(futures):
            checked += 1
            if checked % 100 == 0 or checked == total:
                print(f"  -> İlerleme: {checked}/{total} kontrol edildi... (Şu ana kadar {len(verified_groups)} grup bulundu)")
            res = future.result()
            if res:
                verified_groups.append(res)
                print(f"  [+] BULUNDU: @{res['username']:28s} | {res['members']:>6d} üye | {res['category']:30s} | {res['title'][:35]}")

    # Sıralama
    verified_groups.sort(key=lambda x: (x.get('score', 0), x.get('members', 0)), reverse=True)

    output_file = "yeni_varyasyon_kesfedilen_gruplar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(verified_groups, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"BAŞARIYLA BULUNAN YENİ VARYASYON HEDEF GRUBU SAYISI: {len(verified_groups)}")
    print(f"Sonuçlar '{output_file}' dosyasına kaydedildi.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
