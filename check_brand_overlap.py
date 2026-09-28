import json, re

catalogs = {
    'keyvadi': 'keyvadi_shopier_links.json',
    'froxy': 'froxy_shopier_links.json',
    'lisansarena': 'miniapp_lisansarena/products_db.json',
    'jarvis': 'jarvis_shopier_products.json'
}

data = {}
for brand, path in catalogs.items():
    try:
        data[brand] = json.load(open(path, encoding='utf-8', errors='ignore'))
    except Exception as e:
        print(f"Error loading {brand}: {e}")

# Extract URLs for each brand
brand_urls = {}
for brand, items in data.items():
    brand_urls[brand] = set()
    for it in items:
        u = it.get('shopier_url') or it.get('url') or it.get('link') or ''
        if u:
            brand_urls[brand].add(u.strip())

# Check overlap
print("=== URL Overlap Across Brands ===")
brands = list(brand_urls.keys())
for i in range(len(brands)):
    for j in range(i+1, len(brands)):
        b1, b2 = brands[i], brands[j]
        common = brand_urls[b1].intersection(brand_urls[b2])
        print(f"{b1} <--> {b2}: {len(common)} common URLs")
        if common:
            print(f"   Examples: {list(common)[:3]}")
