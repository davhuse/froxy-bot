import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

with open("yeni_birebir_hedef_gruplar.json", "r", encoding="utf-8") as f:
    raw_groups = json.load(f)

# Non-target filter patterns (cars, academic, foreign languages, physical textiles, real estate)
NON_TARGET_TERMS = [
    "araba", "araç", "arac", "oto alım", "doktora", "yüksek lisans", "tez",
    "tekstil", "kumaş", "toptan tekstil", "uzbek", "philippines", "мультипликация",
    "giyim", "eşya", "esya", "mobilya", "ev", "daire", "arsa"
]

pure_1to1_targets = []

for g in raw_groups:
    uname = g["username"].lower()
    title = g["title"].lower()
    desc = g.get("about_description", "").lower()
    combined = f"{uname} {title} {desc}"
    
    # 1. Skip non-target physical / academic / foreign
    if any(nt in combined for nt in NON_TARGET_TERMS):
        continue
        
    # 2. Skip foreign usernames
    if uname in ["animatecc", "cekerbabat1", "stilistlargruppasi", "diyarbakirikincielarac", "sahibindenarabalar", "izmiresya", "toptantekstilurunleri", "yukseklisansdoktora"]:
        continue
        
    # 3. Must be Turkish digital trade, coupon, code, account, license, smm, or trade market
    cat = g["category"]
    
    # Refine Category
    if any(k in combined for k in ["gmail", "hesap", "account", "tiktok", "instagram", "chatgpt", "canva", "spotify", "zoom"]):
        cat = "Premium Hesap & Dijital Ürün Satışı"
    elif any(k in combined for k in ["kupon", "çek", "cek", "kod", "bedava internet", "fırsat", "indirim"]):
        cat = "Kupon & Çek & Kod Pazarı"
    elif any(k in combined for k in ["windows", "lisans", "key", "office", "yazılım"]):
        cat = "Lisans, Key & Yazılım Ticareti"
    elif any(k in combined for k in ["smm", "panel", "takipçi", "social"]):
        cat = "SMM & Sosyal Medya Hizmetleri"
    else:
        cat = "Dijital Pazar & Alım-Satım Ticareti"
        
    g["category"] = cat
    pure_1to1_targets.append(g)

# Sort by online count and member count
pure_1to1_targets.sort(key=lambda x: (-x["online"], -x["members"]))

print(f"[*] Rafine Edilmiş 1'e 1 Saf Hedef Grup Sayısı: {len(pure_1to1_targets)}")

# Save final JSON
with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
    json.dump(pure_1to1_targets, f, ensure_ascii=False, indent=2)

# Save final TXT
with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
    for item in pure_1to1_targets:
        f.write(f"{item['username']}\n")

print("\n--- ONAYLANAN SAF HEDEF GRUPLAR ---")
for idx, item in enumerate(pure_1to1_targets, 1):
    print(f"{idx}. @{item['username']:<25} | Üye: {item['members']:<6} | Online: {item['online']:<4} | {item['category']}")
