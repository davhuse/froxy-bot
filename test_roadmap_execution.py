# -*- coding: utf-8 -*-
import sys
import sales_conversion as sc

sys.stdout.reconfigure(encoding='utf-8')
cat = sc.load_sales_catalog('keyvadi')

print("--- ROADMAP TESTS ---")
for q in ['3 aylık', 'ortak', 'kişisel', 'kupon', 'yemek', 'market', 'fiyat listesi', 'netflix']:
    res = sc.resolve_smart_roadmap_reply(q)
    print(f"Query: '{q}' -> Has Roadmap: {bool(res)}")

print("\n--- MULTI-VARIANT TESTS ---")
test_queries = [
    'netflix', 'netflix ortak', 'netflix kişisel',
    'yemeksepeti', 'yemeksepeti kupon',
    'minecraft', 'minecraft 3 aylık',
    'coffy', 'migros'
]
for q in test_queries:
    matches = sc.match_sales_products(q, cat)
    titles = [f"{m['title']} ({m['price']})" for m in matches]
    print(f"Query: '{q}' -> Matches ({len(matches)}): {titles}")
