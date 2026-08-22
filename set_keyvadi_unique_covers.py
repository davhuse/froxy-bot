import json, os

with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

updated = 0
for p in products:
    pid = str(p.get('id'))
    png_rel = f"assets/products/product_{pid}.png"
    png_full = os.path.join('miniapp', png_rel)
    if os.path.exists(png_full):
        p['image'] = png_rel
        updated += 1
    else:
        print(f"Warning: PNG not found for {pid}, keeping {p.get('image')}")

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"KeyVadi products_db.json updated: {updated}/{len(products)} products set to unique KeyVadi PNG covers!")
