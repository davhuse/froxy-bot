import json

print("=== LISANSARENA CATALOG IMAGES ===")
try:
    with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
        la = json.load(f)
    for p in la:
        medias = p.get("media", [])
        media_url = medias[0].get("url") if medias else "N/A"
        print(f"{p['title']} ({p['id']}) -> {media_url}")
except Exception as e:
    print("Error:", e)

print("\n=== KEYVADI CATALOG IMAGES ===")
try:
    with open("bot_config.json", "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    links = cfg.get("shopier_links", {})
    for k, v in links.items():
        print(f"{k} -> {v}")
except Exception as e:
    print("Error:", e)
