import json

with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

targets = ["YouTube Premium (3 Aylık Kod)", "Spotify Premium (4 Aylık Kod)", "Canva 1 Yıllık Pro Davet", "Netflix 4K Ultra HD (Kişisel Profil)"]
for p in catalog:
    title = p.get("title")
    if title in targets:
        print(f"Match: {title} -> ID: {p.get('id')} | Price: {p.get('priceData', {}).get('price')} TRY")
