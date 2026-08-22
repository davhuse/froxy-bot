#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Nihai Temiz Ürün Kataloğu ve 3D Kart Eşleme Scripti
1. Çift ürünleri temizler (tekilleştirir).
2. Türkçe karakterleri UTF-8 düzeltir.
3. Vitrini kullanıcının tam istediği sıralamayla düzenler:
   1000 Takipçi, Canva Pro, Netflix, YouTube, Spotify, Exxen, Gemini Davet, CapCut, Steam...
4. Tüm ürünlere robotik olmayan saf 3D modern kart görsellerini bağlar.
"""

import os
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LA_DIR = BASE_DIR / "miniapp_lisansarena"
LA_ASSETS = LA_DIR / "assets" / "products"
LA_ASSETS.mkdir(parents=True, exist_ok=True)

ART_DIR_1 = Path("C:/Users/habil/.gemini/antigravity/brain/b3d6b142-698f-408f-8efb-52bc1b303e13")
ART_DIR_2 = Path("C:/Users/habil/.gemini/antigravity/brain/fbd09d2b-4007-40b6-be24-bbd2f7ab73dc")

def get_best_art(filename_pattern):
    for d in (ART_DIR_2, ART_DIR_1):
        if d.exists():
            matches = list(d.glob(filename_pattern))
            if matches:
                matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return matches[0]
    return None

# Definitive image mapping dictionary
IMAGE_MAP = {
    "instagram": get_best_art("instagram_followers_card_*.jpg") or get_best_art("la_ai_instagram_followers.jpg"),
    "canva": get_best_art("canva_pro_card_*.jpg") or get_best_art("kv_canva_ai_*.jpg"),
    "netflix": get_best_art("netflix_4k_card_*.jpg") or get_best_art("kv_netflix_ai_*.jpg"),
    "youtube": get_best_art("youtube_premium_card_*.jpg") or get_best_art("kv_youtube_ai_*.jpg"),
    "spotify": get_best_art("spotify_premium_card_*.jpg") or get_best_art("kv_spotify_ai_*.jpg"),
    "exxen": get_best_art("exxen_reklamsiz_card_*.jpg") or get_best_art("kv_exxen_ai_*.jpg"),
    "gemini": get_best_art("kv_gemini_ai_*.jpg") or get_best_art("la_gemini_ultra_ai_*.jpg"),
    "capcut": get_best_art("capcut_pro_card_*.jpg") or get_best_art("kv_capcut_ai_*.jpg"),
    "steam": get_best_art("steam_random_card_*.jpg") or get_best_art("kv_steam_ai_*.jpg"),
    "steam_game": get_best_art("la_steam_game_ai_*.jpg") or get_best_art("steam_random_card_*.jpg"),
    "fc26": get_best_art("kv_fc26_ai_*.jpg") or get_best_art("la_fc26_ai_*.jpg"),
    "grok": get_best_art("kv_grok_ai_*.jpg") or get_best_art("la_grok_ai_*.jpg"),
    "perplexity": get_best_art("la_perplexity_ai_*.jpg"),
    "gamma": get_best_art("la_gamma_ai_*.jpg"),
    "deepl": get_best_art("la_deepl_ai_*.jpg"),
    "duolingo": get_best_art("la_duolingo_ai_*.jpg"),
    "scribd": get_best_art("la_scribd_ai_*.jpg"),
    "magnific": get_best_art("la_magnific_ai_*.jpg"),
    "grammarly": get_best_art("la_grammarly_ai_*.jpg"),
    "crunchyroll": get_best_art("la_crunchyroll_ai_*.jpg"),
    "prime": get_best_art("prime_video_card_*.jpg"),
    "hbo": get_best_art("hbo_max_card_*.jpg"),
    "envato": get_best_art("envato_elements_card_*.jpg"),
    "freepik": get_best_art("freepik_premium_card_*.jpg"),
    "adobe": get_best_art("adobe_creative_card_*.jpg") or get_best_art("kv_adobe_ai_*.jpg"),
    "office": get_best_art("office365_card_*.jpg") or get_best_art("kv_windows_ai_*.jpg"),
    "windows": get_best_art("windows_pro_card_*.jpg") or get_best_art("kv_windows_ai_*.jpg"),
    "minecraft": get_best_art("minecraft_capes_card_*.jpg"),
    "roblox": get_best_art("roblox_offsale_card_*.jpg"),
    "gmail": get_best_art("gmail_account_card_*.jpg"),
    "telegram": get_best_art("kv_telegram_ai_*.jpg") or get_best_art("la_telegram_ai_*.jpg"),
    "shell": get_best_art("la_shell_fuel_ai_*.jpg") or get_best_art("kv_trendyol_ai_*.jpg"),
    "zula": get_best_art("kv_zula_ai_*.jpg") or get_best_art("la_zula_ai_*.jpg"),
}

print("=== IMAGE SOURCES MAPPED ===")
for k, v in IMAGE_MAP.items():
    print(f" - {k}: {v.name if v else 'MISSING'}")
