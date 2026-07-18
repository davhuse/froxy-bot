import shutil
import os

brain_dir = r"C:\Users\habil\.gemini\antigravity\brain\f2391100-266d-44df-bd11-d165b03a374d"
static_dir = r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\static"

mappings = {
    "exxen_premium_mockup_1783808947596.png": "lisansarena_exxen.png",
    "office_365_mockup_1783808510588.png": "lisansarena_office365.png",
    "shell_puan_mockup_1783809063688.png": "lisansarena_shell.png",
    "steam_game_mockup_1783808536421.png": "lisansarena_steam.png",
    "trendyol_market_mockup_1783809056746.png": "lisansarena_trendyol_market.png",
    "trendyol_yemek_mockup_1783809047496.png": "lisansarena_trendyol_yemek.png",
}

print("Copying target product cover images to static folder...")
for src_name, dst_name in mappings.items():
    src_path = os.path.join(brain_dir, src_name)
    dst_path = os.path.join(static_dir, dst_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print(f"Copied: {src_name} -> {dst_name}")
    else:
        print(f"Warning: Source not found: {src_path}")

print("Copy completed successfully.")
