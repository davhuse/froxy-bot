import json

with open("live_shopier_products.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"KeyVadi urun sayisi: {len(data)}\n")
for p in data:
    if isinstance(p, dict):
        title = p.get("title", "?")
        price = p.get("priceData", {}).get("price", "?") if isinstance(p.get("priceData"), dict) else p.get("price", "?")
        pid = p.get("id", "?")
        desc = p.get("description", "")[:100]
        print(f"ID: {pid} | {title} | {price} TL")
        print(f"  Desc: {desc}")
        print()
