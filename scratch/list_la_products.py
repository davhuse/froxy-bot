import json

with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"LisansArena mevcut urun sayisi: {len(data)}\n")
for p in data:
    title = p.get("title", "?")
    price = p.get("priceData", {}).get("price", "?")
    pid = p.get("id", "?")
    print(f"ID: {pid} | {title} | {price} TL")
