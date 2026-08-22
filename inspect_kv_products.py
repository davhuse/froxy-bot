import json

with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f"Total KeyVadi products: {len(products)}")
for p in products[:15]:
    print(f"[{p.get('id')}] {p.get('title')} -> {p.get('image')} (vitrin: {p.get('is_vitrin')})")
