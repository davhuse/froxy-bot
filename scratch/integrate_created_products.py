import json
import re

# File Paths
LISANSARENA_JSON = "lisansarena_shopier_links.json"
FROXY_BOT_PY = "froxy_bot.py"
BOT_CONFIG_JSON = "bot_config.json"

# 1. Update lisansarena_shopier_links.json
print("Updating lisansarena_shopier_links.json...")
with open(LISANSARENA_JSON, "r", encoding="utf-8") as f:
    catalog = json.load(f)

updated_la = 0
for p in catalog:
    if p["id"] == "48901849":
        p["id"] = "49000419"
        p["url"] = "https://www.shopier.com/49000419"
        p["priceData"]["price"] = "39.90"
        p["priceData"]["discountedPrice"] = "39.90"
        updated_la += 1
    elif p["id"] == "48901864":
        p["id"] = "49000421"
        p["url"] = "https://www.shopier.com/49000421"
        p["priceData"]["price"] = "29.90"
        p["priceData"]["discountedPrice"] = "29.90"
        updated_la += 1
    elif p["id"] == "48901866":
        p["id"] = "49000422"
        p["url"] = "https://www.shopier.com/49000422"
        p["priceData"]["price"] = "19.90"
        p["priceData"]["discountedPrice"] = "19.90"
        updated_la += 1

if updated_la == 3:
    with open(LISANSARENA_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print("  [SUCCESS] Updated all 3 products in LisansArena links json!")
else:
    print(f"  [ERROR] Updated only {updated_la} products in LisansArena links json!")

# 2. Update froxy_bot.py
print("\nUpdating froxy_bot.py INJECTED_PRODUCTS...")
with open(FROXY_BOT_PY, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the injected lines
old_hbo = '{"id": "48901849", "title": "HBO Max 1 Aylık Profil", "price": "39.90 TL", "url": "https://www.shopier.com/48901849"}'
new_hbo = '{"id": "49000411", "title": "HBO Max 1 Aylık Profil", "price": "39.90 TL", "url": "https://www.shopier.com/49000411"}'

old_pv_ozel = '{"id": "48901864", "title": "Prime Video (1 Aylık) - Özel Profil", "price": "29.90 TL", "url": "https://www.shopier.com/48901864"}'
new_pv_ozel = '{"id": "49000412", "title": "Prime Video (1 Aylık) - Özel Profil", "price": "29.90 TL", "url": "https://www.shopier.com/49000412"}'

old_pv_ortak = '{"id": "48901866", "title": "Prime Video (1 Aylık) - Ortak Profil", "price": "19.90 TL", "url": "https://www.shopier.com/48901866"}'
new_pv_ortak = '{"id": "49000414", "title": "Prime Video (1 Aylık) - Ortak Profil", "price": "19.90 TL", "url": "https://www.shopier.com/49000414"}'

if old_hbo in content and old_pv_ozel in content and old_pv_ortak in content:
    content = content.replace(old_hbo, new_hbo)
    content = content.replace(old_pv_ozel, new_pv_ozel)
    content = content.replace(old_pv_ortak, new_pv_ortak)
    with open(FROXY_BOT_PY, "w", encoding="utf-8") as f:
        f.write(content)
    print("  [SUCCESS] Updated all 3 injected products in froxy_bot.py!")
else:
    print("  [ERROR] Could not find the target injected product lines in froxy_bot.py!")

# 3. Update bot_config.json
print("\nUpdating bot_config.json shopier_links...")
with open(BOT_CONFIG_JSON, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

cfg["shopier_links"]["hbo_max"] = "https://www.shopier.com/49000411"
cfg["shopier_links"]["prime_video_ozel"] = "https://www.shopier.com/49000412"
cfg["shopier_links"]["prime_video_ortak"] = "https://www.shopier.com/49000414"

with open(BOT_CONFIG_JSON, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("  [SUCCESS] Updated shopier_links in bot_config.json!")
