#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena ve KeyVadi — Saf AI Sanat Kapakları ve Veritabanı Eşleyici (v9.0)
Hiçbir yapay çizgi, bozuk kutu olmadan saf ve yüksek kaliteli AI görsellerini doğrudan ürünlere bağlar.
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("C:/Users/habil/.gemini/antigravity/brain/b3d6b142-698f-408f-8efb-52bc1b303e13")

# Find latest generated artifact
def find_latest_art(name):
    matches = list(ARTIFACT_DIR.glob(f"{name}_*.jpg"))
    if matches:
        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return matches[0]
    return None

ART_SOURCES = {
    "fc26": find_latest_art("la_fc26_ai"),
    "zula": find_latest_art("la_zula_ai"),
    "steam_key": find_latest_art("la_steam_ai"),
    "steam_game": find_latest_art("la_steam_game_ai"),
    "canva": find_latest_art("la_canva_pro_ai"),
    "shell": find_latest_art("la_shell_fuel_ai"),
    "gemini": find_latest_art("la_gemini_ultra_ai"),
    "gamma": find_latest_art("la_gamma_ai"),
    "grok": find_latest_art("la_grok_ai"),
    "windows": find_latest_art("la_windows_office_ai"),
    "office": find_latest_art("la_windows_office_ai"),
    "telegram": find_latest_art("la_telegram_ai"),
    "perplexity": find_latest_art("la_perplexity_ai"),
    "duolingo": find_latest_art("la_duolingo_ai"),
    "deepl": find_latest_art("la_deepl_ai"),
    "scribd": find_latest_art("la_scribd_ai"),
    "magnific": find_latest_art("la_magnific_ai"),
    "adobe": find_latest_art("la_adobe_cc_ai"),
    "grammarly": find_latest_art("la_grammarly_ai"),
    "crunchyroll": find_latest_art("la_crunchyroll_ai"),
    "chatgpt": find_latest_art("la_chatgpt_ai"),
    "netflix": find_latest_art("la_netflix_ai")
}

print("[*] Bulunan AI Sanat Dosyalari:")
for k, v in ART_SOURCES.items():
    print(f" - {k}: {v.name if v else 'YOK'}")

# 1. Update LisansArena
la_dir = BASE_DIR / "miniapp_lisansarena"
la_assets_dir = la_dir / "assets" / "products"
la_assets_dir.mkdir(parents=True, exist_ok=True)

with open(BASE_DIR / "lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    raw_la = json.load(f)

la_products = []
seen = set()

for item in raw_la:
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

    # Determine best visual
    src_file = None
    if "fc26" in t_low:
        src_file = ART_SOURCES["fc26"]
    elif "zula" in t_low:
        src_file = ART_SOURCES["zula"]
    elif "steam" in t_low and "random" in t_low:
        src_file = ART_SOURCES["steam_key"]
    elif "steam" in t_low:
        src_file = ART_SOURCES["steam_game"]
    elif "canva" in t_low:
        src_file = ART_SOURCES["canva"]
    elif "shell" in t_low or "akaryakıt" in t_low:
        src_file = ART_SOURCES["shell"]
    elif "gemini" in t_low:
        src_file = ART_SOURCES["gemini"]
    elif "gamma" in t_low:
        src_file = ART_SOURCES["gamma"]
    elif "grok" in t_low:
        src_file = ART_SOURCES["grok"]
    elif "windows" in t_low or "office" in t_low:
        src_file = ART_SOURCES["windows"]
    elif "telegram" in t_low:
        src_file = ART_SOURCES["telegram"]
    elif "perplexity" in t_low:
        src_file = ART_SOURCES["perplexity"]
    elif "duolingo" in t_low:
        src_file = ART_SOURCES["duolingo"]
    elif "deepl" in t_low:
        src_file = ART_SOURCES["deepl"]
    elif "scribd" in t_low:
        src_file = ART_SOURCES["scribd"]
    elif "magnific" in t_low:
        src_file = ART_SOURCES["magnific"]
    elif "adobe" in t_low:
        src_file = ART_SOURCES["adobe"]
    elif "grammarly" in t_low:
        src_file = ART_SOURCES["grammarly"]
    elif "crunchyroll" in t_low:
        src_file = ART_SOURCES["crunchyroll"]
    elif "chatgpt" in t_low:
        src_file = ART_SOURCES["chatgpt"]
    else:
        src_file = ART_SOURCES["gemini"]

    dest_name = f"art_{pid}.jpg"
    dest_path = la_assets_dir / dest_name
    if src_file and src_file.exists():
        shutil.copy2(src_file, dest_path)

    if any(k in t_low for k in ["fc26", "zula", "steam"]):
        cat = "gaming"
    elif any(k in t_low for k in ["gemini", "grok", "chatgpt", "perplexity", "deepl", "gamma", "magnific", "grammarly"]):
        cat = "ai"
    elif any(k in t_low for k in ["canva", "adobe", "capcut"]):
        cat = "design"
    elif any(k in t_low for k in ["windows", "office", "kaspersky"]):
        cat = "software"
    elif any(k in t_low for k in ["telegram", "discord"]):
        cat = "social"
    elif any(k in t_low for k in ["crunchyroll", "netflix", "hbo", "prime"]):
        cat = "cinema"
    elif any(k in t_low for k in ["shell", "trendyol", "kupon"]):
        cat = "coupons"
    else:
        cat = "ai"

    is_vitrin = any(k in t_low for k in ["canva", "fc26", "gemini", "grok", "telegram", "windows", "steam", "perplexity", "adobe"])

    prod = {
        "id": pid,
        "title": title,
        "price": price,
        "price_num": p_num,
        "category": cat,
        "image": f"assets/products/{dest_name}",
        "badge": "💎 Arena VIP" if is_vitrin else "⚡ Orijinal",
        "url": item.get("url", f"https://www.shopier.com/lisansarena/{pid}"),
        "description": item.get("description", f"{title} - LisansArena güvencesiyle anında teslimat ve 7/24 garanti."),
        "showcase": is_vitrin,
        "is_vitrin": is_vitrin
    }
    la_products.append(prod)

with open(la_dir / "products_db.json", "w", encoding="utf-8") as f:
    json.dump(la_products, f, ensure_ascii=False, indent=2)

print(f"[OK] LisansArena: {len(la_products)} urun guncellendi.")

# 2. Update KeyVadi with AI Artworks as well
kv_dir = BASE_DIR / "miniapp"
kv_assets_dir = kv_dir / "assets" / "products"
kv_assets_dir.mkdir(parents=True, exist_ok=True)

with open(kv_dir / "products_db.json", "r", encoding="utf-8") as f:
    kv_products = json.load(f)

for p in kv_products:
    t_low = p["title"].lower()
    pid = str(p["id"])
    src_file = None
    if "fc26" in t_low or "fifa" in t_low:
        src_file = ART_SOURCES["fc26"]
    elif "zula" in t_low:
        src_file = ART_SOURCES["zula"]
    elif "steam" in t_low and "cüzdan" in t_low:
        src_file = ART_SOURCES["steam_key"]
    elif "steam" in t_low:
        src_file = ART_SOURCES["steam_game"]
    elif "canva" in t_low:
        src_file = ART_SOURCES["canva"]
    elif "gemini" in t_low:
        src_file = ART_SOURCES["gemini"]
    elif "grok" in t_low:
        src_file = ART_SOURCES["grok"]
    elif "chatgpt" in t_low or "openai" in t_low:
        src_file = ART_SOURCES["chatgpt"]
    elif "windows" in t_low or "office" in t_low:
        src_file = ART_SOURCES["windows"]
    elif "telegram" in t_low:
        src_file = ART_SOURCES["telegram"]
    elif "adobe" in t_low:
        src_file = ART_SOURCES["adobe"]
    elif "netflix" in t_low:
        src_file = ART_SOURCES["netflix"]
    elif "crunchyroll" in t_low:
        src_file = ART_SOURCES["crunchyroll"]
    elif "trendyol" in t_low or "kupon" in t_low or "yemeksepeti" in t_low:
        src_file = ART_SOURCES["shell"]

    if src_file and src_file.exists():
        dest_name = f"kv_art_{pid}.jpg"
        dest_path = kv_assets_dir / dest_name
        shutil.copy2(src_file, dest_path)
        p["image"] = f"assets/products/{dest_name}"

with open(kv_dir / "products_db.json", "w", encoding="utf-8") as f:
    json.dump(kv_products, f, ensure_ascii=False, indent=2)

print(f"[OK] KeyVadi: {len(kv_products)} urun guncellendi.")
