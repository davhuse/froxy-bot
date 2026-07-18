import json

FROXY_BOT_PY = "froxy_bot.py"
BOT_CONFIG_JSON = "bot_config.json"

# 1. Update froxy_bot.py
print("Updating froxy_bot.py...")
with open(FROXY_BOT_PY, "r", encoding="utf-8") as f:
    content = f.read()

replacements = {
    '49002084': '49002143',
    '49002085': '49002144',
    '49002088': '49002145'
}

for k, v in replacements.items():
    content = content.replace(k, v)

with open(FROXY_BOT_PY, "w", encoding="utf-8") as f:
    f.write(content)
print("  [SUCCESS] Updated froxy_bot.py with final KeyVadi IDs!")

# 2. Update bot_config.json
print("\nUpdating bot_config.json...")
with open(BOT_CONFIG_JSON, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

cfg["shopier_links"]["hbo_max"] = "https://www.shopier.com/49002143"
cfg["shopier_links"]["prime_video_ozel"] = "https://www.shopier.com/49002144"
cfg["shopier_links"]["prime_video_ortak"] = "https://www.shopier.com/49002145"

with open(BOT_CONFIG_JSON, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("  [SUCCESS] Updated bot_config.json shopier_links!")
