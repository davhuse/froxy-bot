import json

with open('miniapp_lisansarena/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f'Total items: {len(products)}')
for i, p in enumerate(products, 1):
    pid = p.get('id')
    title = p.get('title')
    price = p.get('price')
    cat = p.get('category')
    vitrin = p.get('is_vitrin') or p.get('showcase')
    img = p.get('image')
    print(f"{i:2d}. [{pid}] {title} | {price} | {cat} | Vitrin:{vitrin} | {img}")
