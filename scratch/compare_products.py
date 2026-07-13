import json

with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
    la_products = json.load(f)

with open("parsed_keyvadi_products.json", "r", encoding="utf-8") as f:
    kv_products = json.load(f)

la_titles = {p["title"].strip().lower(): p for p in la_products}
kv_titles = {p["title"].strip().lower() for p in kv_products}

print("=== PRODUCTS IN LISANSARENA BUT NOT IN KEYVADI ===")
missing_count = 0
for title, p in la_titles.items():
    matched = False
    for kv_t in kv_titles:
        if title in kv_t or kv_t in title or title.split("(")[0].strip() == kv_t.split("(")[0].strip():
            matched = True
            break
    if not matched:
        print(f"- Title: {p['title']}")
        print(f"  Price: {p['priceData']['price']} TL")
        print(f"  Description: {p['description']}")
        print("---")
        missing_count += 1

print(f"Total missing products: {missing_count}")
