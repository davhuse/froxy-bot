import sys
from sales_conversion import load_sales_catalog, purchase_url

catalog = load_sales_catalog('lisansarena')
print(f'Catalog length: {len(catalog)}')
for p in catalog[:5]:
    u = purchase_url(p, 'lisansarena', 'bot_product_detail')
    print(f"{p.get('title')}: {u}")
