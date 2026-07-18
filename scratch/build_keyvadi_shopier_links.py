import json
import os

parsed_path = "parsed_keyvadi_products.json"
target_path = "keyvadi_shopier_links.json"

products = []
if os.path.exists(parsed_path):
    with open(parsed_path, "r", encoding="utf-8") as f:
        products = json.load(f)

# The new KeyVadi products we created recently
new_products = [
    {
        "id": "49002143",
        "title": "HBO Max 1 Aylık Profil",
        "price": "39.90 TL",
        "url": "https://www.shopier.com/49002143"
    },
    {
        "id": "49002144",
        "title": "Prime Video (1 Aylık) - Özel Profil",
        "price": "29.90 TL",
        "url": "https://www.shopier.com/49002144"
    },
    {
        "id": "49002145",
        "title": "Prime Video (1 Aylık) - Ortak Profil",
        "price": "19.90 TL",
        "url": "https://www.shopier.com/49002145"
    }
]

# Avoid duplicates
existing_ids = {p["id"] for p in products}
for np in new_products:
    if np["id"] not in existing_ids:
        products.append(np)

# Save both keyvadi_shopier_links.json and parsed_keyvadi_products.json
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

with open(parsed_path, "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

print(f"Successfully wrote {len(products)} products to {target_path} and {parsed_path}!")
