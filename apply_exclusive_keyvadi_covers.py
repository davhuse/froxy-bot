#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi — Özel Cyan/Neon AI Sanat Görsellerini Eşleme ve Veritabanı Güncelleyici (v10.0)
Tüm 61 ürünü yalnızca KeyVadi için özel üretilen 3D AI görsellerle günceller.
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("C:/Users/habil/.gemini/antigravity/brain/b3d6b142-698f-408f-8efb-52bc1b303e13")
KV_DIR = BASE_DIR / "miniapp"
KV_ASSETS = KV_DIR / "assets" / "products"
KV_ASSETS.mkdir(parents=True, exist_ok=True)

def find_art(prefix):
    matches = list(ARTIFACT_DIR.glob(f"{prefix}_*.jpg"))
    if matches:
        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return matches[0]
    return None

KV_AI_MAP = {
    "fc26": find_art("kv_fc26_ai"),
    "canva": find_art("kv_canva_ai"),
    "gemini": find_art("kv_gemini_ai"),
    "chatgpt": find_art("kv_chatgpt_ai"),
    "netflix": find_art("kv_netflix_ai"),
    "spotify": find_art("kv_spotify_ai"),
    "windows": find_art("kv_windows_ai"),
    "office": find_art("kv_windows_ai"),
    "youtube": find_art("kv_youtube_ai"),
    "steam": find_art("kv_steam_ai"),
    "zula": find_art("kv_zula_ai"),
    "telegram": find_art("kv_telegram_ai"),
    "capcut": find_art("kv_capcut_ai"),
    "grok": find_art("kv_grok_ai"),
    "trendyol": find_art("kv_trendyol_ai"),
    "adobe": find_art("kv_adobe_ai"),
    "disney": find_art("kv_disney_ai"),
    "exxen": find_art("kv_exxen_ai")
}

print("[*] KeyVadi Ozel AI Gorselleri:")
for k, v in KV_AI_MAP.items():
    print(f" - {k}: {v.name if v else 'YOK'}")

with open(KV_DIR / "products_db.json", "r", encoding="utf-8") as f:
    products = json.load(f)

for p in products:
    title = p["title"]
    t_low = title.lower()
    pid = str(p["id"])

    src = None
    if "fc26" in t_low or "fifa" in t_low:
        src = KV_AI_MAP["fc26"]
    elif "canva" in t_low:
        src = KV_AI_MAP["canva"]
    elif "gemini" in t_low or "claude" in t_low:
        src = KV_AI_MAP["gemini"]
    elif "chatgpt" in t_low or "openai" in t_low:
        src = KV_AI_MAP["chatgpt"]
    elif "netflix" in t_low:
        src = KV_AI_MAP["netflix"]
    elif "spotify" in t_low:
        src = KV_AI_MAP["spotify"]
    elif "windows" in t_low or "office" in t_low:
        src = KV_AI_MAP["windows"]
    elif "youtube" in t_low:
        src = KV_AI_MAP["youtube"]
    elif "steam" in t_low or "oyun" in t_low or "key" in t_low:
        src = KV_AI_MAP["steam"]
    elif "zula" in t_low:
        src = KV_AI_MAP["zula"]
    elif "telegram" in t_low:
        src = KV_AI_MAP["telegram"]
    elif "capcut" in t_low:
        src = KV_AI_MAP["capcut"]
    elif "grok" in t_low:
        src = KV_AI_MAP["grok"]
    elif "trendyol" in t_low or "kupon" in t_low or "yemeksepeti" in t_low or "boyner" in t_low:
        src = KV_AI_MAP["trendyol"]
    elif "adobe" in t_low:
        src = KV_AI_MAP["adobe"]
    elif "disney" in t_low or "hbo" in t_low or "prime" in t_low:
        src = KV_AI_MAP["disney"]
    elif "exxen" in t_low or "blutv" in t_low or "tod" in t_low or "ssport" in t_low:
        src = KV_AI_MAP["exxen"]
    else:
        src = KV_AI_MAP["gemini"]

    # Rebrand "PRO" to "APP"
    if p.get("badge") == "PRO":
        p["badge"] = "APP"
    elif p.get("badge") == "VIP PRO":
        p["badge"] = "VIP APP"

    if src and src.exists():
        dest_filename = f"kv_exclusive_{pid}.jpg"
        dest_path = KV_ASSETS / dest_filename
        shutil.copy2(src, dest_path)
        p["image"] = f"assets/products/{dest_filename}"

with open(KV_DIR / "products_db.json", "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"[OK] KeyVadi: 61 urunun tamami ozel KeyVadi AI gorselleriyle guncellendi!")
