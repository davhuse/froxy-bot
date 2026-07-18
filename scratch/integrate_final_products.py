import json

LISANSARENA_JSON = "lisansarena_shopier_links.json"
FROXY_BOT_PY = "froxy_bot.py"
BOT_CONFIG_JSON = "bot_config.json"

# 1. Update lisansarena_shopier_links.json
print("Updating lisansarena_shopier_links.json...")
with open(LISANSARENA_JSON, "r", encoding="utf-8") as f:
    catalog = json.load(f)

updated_la = 0
for p in catalog:
    # Use previous IDs as targets to replace them
    if p["id"] in ["49000419", "49000910"]:
        p["id"] = "49000910"
        p["url"] = "https://www.shopier.com/49000910"
        p["media"] = [{"id": "1", "type": "image", "url": "https://veridia-bot.onrender.com/static/la_hbo.png", "placement": 1}]
        updated_la += 1
    elif p["id"] in ["49000421", "49000911"]:
        p["id"] = "49000911"
        p["url"] = "https://www.shopier.com/49000911"
        p["media"] = [{"id": "1", "type": "image", "url": "https://veridia-bot.onrender.com/static/la_prime.png", "placement": 1}]
        updated_la += 1
    elif p["id"] in ["49000422", "49000912"]:
        p["id"] = "49000912"
        p["url"] = "https://www.shopier.com/49000912"
        p["media"] = [{"id": "1", "type": "image", "url": "https://veridia-bot.onrender.com/static/la_prime.png", "placement": 1}]
        updated_la += 1

with open(LISANSARENA_JSON, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)
print(f"  [SUCCESS] Updated {updated_la} products in LisansArena links json!")

# 2. Update froxy_bot.py
print("\nUpdating froxy_bot.py...")
with open(FROXY_BOT_PY, "r", encoding="utf-8") as f:
    content = f.read()

# Replace injected products list items
# We'll use regex to make it extremely robust and replace by slug/title match
injected_block_start = "INJECTED_PRODUCTS = ["
injected_block_end = "]"
start_idx = content.find(injected_block_start)
end_idx = content.find(injected_block_end, start_idx)

if start_idx != -1 and end_idx != -1:
    new_injected = """INJECTED_PRODUCTS = [{"id": "47669105", "title": "YouTube Premium (3 Aylık Kod)", "price": "29.99 TL", "url": "https://www.shopier.com/keyvadi/47669105"},
    {"id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "49.99 TL", "url": "https://www.shopier.com/keyvadi/47669117"},
    {"id": "48114807", "title": "XBOX Game Pass Ultimate (3 Aylık Üyelik)", "price": "80.00 TL", "url": "https://www.shopier.com/keyvadi/48114807"},
    {"id": "48114802", "title": "Steam İstediğiniz Oyun (Ortak Hesap)", "price": "60.00 TL", "url": "https://www.shopier.com/keyvadi/48114802"},
    {"id": "48943148", "title": "Crunchyroll Ortak Hesap (1 Aylık)", "price": "39.90 TL", "url": "https://www.shopier.com/48943148"},
    {"id": "48943150", "title": "Grammarly Pro (1 Haftalık) - Kendi Hesabınıza", "price": "79.90 TL", "url": "https://www.shopier.com/48943150"},
    {"id": "48943151", "title": "Grammarly Pro (1 Aylık) - Ortak Hesap", "price": "49.90 TL", "url": "https://www.shopier.com/48943151"},
    {"id": "49002084", "title": "HBO Max 1 Aylık Profil", "price": "39.90 TL", "url": "https://www.shopier.com/49002084"},
    {"id": "49002085", "title": "Prime Video (1 Aylık) - Özel Profil", "price": "29.90 TL", "url": "https://www.shopier.com/49002085"},
    {"id": "49002088", "title": "Prime Video (1 Aylık) - Ortak Profil", "price": "19.90 TL", "url": "https://www.shopier.com/49002088"}
]"""
    content = content[:start_idx] + new_injected + content[end_idx+1:]
    with open(FROXY_BOT_PY, "w", encoding="utf-8") as f:
        f.write(content)
    print("  [SUCCESS] Updated froxy_bot.py INJECTED_PRODUCTS!")
else:
    print("  [ERROR] Could not find INJECTED_PRODUCTS block in froxy_bot.py!")

# 3. Update bot_config.json
print("\nUpdating bot_config.json...")
with open(BOT_CONFIG_JSON, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

cfg["shopier_links"]["hbo_max"] = "https://www.shopier.com/49002084"
cfg["shopier_links"]["prime_video_ozel"] = "https://www.shopier.com/49002085"
cfg["shopier_links"]["prime_video_ortak"] = "https://www.shopier.com/49002088"

with open(BOT_CONFIG_JSON, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("  [SUCCESS] Updated bot_config.json shopier_links!")
