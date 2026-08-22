import json, os

with open('miniapp_lisansarena/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f'Total products: {len(products)}')
missing = 0
vitrin_list = []
for p in products:
    img = p.get('image', '')
    path = os.path.join('miniapp_lisansarena', img)
    if not os.path.exists(path):
        print(f"MISSING: {p.get('id')} -> {path}")
        missing += 1
    if p.get('is_vitrin'):
        vitrin_list.append(f"[{p.get('id')}] {p.get('title')} ({p.get('price')})")

print(f'Missing images count: {missing}')
print(f'Vitrin products ({len(vitrin_list)} items):')
for i, v in enumerate(vitrin_list, 1):
    print(f"  {i}. {v}")
