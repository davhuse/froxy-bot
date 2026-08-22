#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Gerçek AI Sanat Görsellerini Eşleme ve Veritabanı Güncelleyici (v7.0)
Tüm 34 ürünü gerçek üretilmiş AI 3D görsellerle donatır.
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("C:/Users/habil/.gemini/antigravity/brain/b3d6b142-698f-408f-8efb-52bc1b303e13")
LA_MINIAPP_DIR = BASE_DIR / "miniapp_lisansarena"
LA_OUTPUT_DIR = LA_MINIAPP_DIR / "assets" / "products"
LA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find latest generated images in artifact dir
def find_latest_artifact(prefix):
    matches = list(ARTIFACT_DIR.glob(f"{prefix}_*.jpg"))
    if matches:
        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return matches[0]
    return None

AI_MAP = {
    "canva": find_latest_artifact("la_canva_pro_ai"),
    "gemini": find_latest_artifact("la_gemini_ultra_ai"),
    "fc26": find_latest_artifact("la_fc26_ai"),
    "windows": find_latest_artifact("la_windows_office_ai"),
    "office": find_latest_artifact("la_windows_office_ai"),
    "grok": find_latest_artifact("la_grok_ai"),
    "steam": find_latest_artifact("la_steam_ai"),
    "telegram": find_latest_artifact("la_telegram_ai"),
    "zula": find_latest_artifact("la_zula_ai"),
    "chatgpt": find_latest_artifact("la_chatgpt_ai"),
    "adobe": find_latest_artifact("la_adobe_cc_ai"),
    "netflix": find_latest_artifact("la_netflix_ai"),
    "perplexity": find_latest_artifact("la_perplexity_ai"),
    "shell": find_latest_artifact("la_shell_fuel_ai"),
    "crunchyroll": find_latest_artifact("la_crunchyroll_ai"),
    "gamma": find_latest_artifact("la_chatgpt_ai"),
    "deepl": find_latest_artifact("la_chatgpt_ai"),
    "scribd": find_latest_artifact("la_canva_pro_ai"),
    "magnific": find_latest_artifact("la_gemini_ultra_ai"),
    "grammarly": find_latest_artifact("la_windows_office_ai"),
    "duolingo": find_latest_artifact("la_canva_pro_ai")
}

print("[*] AI Görselleri Eşleniyor...")
for k, v in AI_MAP.items():
    print(f" - {k}: {v.name if v else 'BULUNAMADI'}")

links_path = BASE_DIR / "lisansarena_shopier_links.json"
with open(links_path, "r", encoding="utf-8") as f:
    raw_items = json.load(f)

seen = set()
la_products = []

for item in raw_items:
    pid = str(item["id"])
    if pid in seen:
        continue
    seen.add(pid)

    title = item["title"]
    price = item["price"]
    clean_p = price.replace("TL", "").replace("₺", "").strip().replace(".", "").replace(",", ".")
    try:
        p_num = float(clean_p)
    except Exception:
        p_num = 0.0

    t_low = title.lower()

    # Find matched AI image
    matched_src = None
    for k in AI_MAP:
        if k in t_low and AI_MAP[k]:
            matched_src = AI_MAP[k]
            break
    
    if not matched_src:
        matched_src = AI_MAP["gemini"] or AI_MAP["canva"]

    dest_filename = f"la_ai_{pid}.jpg"
    dest_path = LA_OUTPUT_DIR / dest_filename
    if matched_src and matched_src.exists():
        shutil.copy2(matched_src, dest_path)

    if any(k in t_low for k in ["fc26", "zula", "steam"]):
        cat = "gaming"
    elif any(k in t_low for k in ["gemini", "grok", "chatgpt", "perplexity", "deepl", "gamma", "magnific"]):
        cat = "ai"
    elif any(k in t_low for k in ["canva", "adobe", "capcut"]):
        cat = "design"
    elif any(k in t_low for k in ["windows", "office", "kaspersky"]):
        cat = "software"
    elif any(k in t_low for k in ["telegram", "discord"]):
        cat = "social"
    elif any(k in t_low for k in ["crunchyroll", "netflix", "hbo", "prime", "exxen"]):
        cat = "cinema"
    elif any(k in t_low for k in ["shell", "trendyol", "kupon"]):
        cat = "coupons"
    else:
        cat = "ai"

    is_showcase = any(k in t_low for k in ["canva", "fc26", "gemini", "grok", "telegram", "windows", "office", "steam", "zula", "perplexity"])

    prod = {
        "id": pid,
        "title": title,
        "price": price,
        "price_num": p_num,
        "category": cat,
        "image": f"assets/products/{dest_filename}",
        "badge": "💎 Arena VIP" if is_showcase else "⚡ Orijinal",
        "url": item.get("url", f"https://www.shopier.com/lisansarena/{pid}"),
        "description": item.get("description", f"{title} - LisansArena güvencesiyle 7/24 anında teslimat ve telafi desteği."),
        "showcase": is_showcase,
        "is_vitrin": is_showcase
    }
    la_products.append(prod)
    print(f"[+] Ürün AI Görseli Eşlendi: {title} -> {dest_filename}")

out_db = LA_MINIAPP_DIR / "products_db.json"
with open(out_db, "w", encoding="utf-8") as f:
    json.dump(la_products, f, ensure_ascii=False, indent=2)

print(f"\n[✓] LisansArena için {len(la_products)} ürünün tamamı gerçek AI görsellerle güncellendi!")
