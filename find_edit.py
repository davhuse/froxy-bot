import re

with open('shopier_page_products.html', 'r', encoding='utf-8') as f:
    content = f.read()

edit_links = re.findall(r'href=["\'](products\.php\?id=\d+)["\']', content, flags=re.IGNORECASE)
print('Found edit links:', edit_links[:10])

# Also let's find the product titles. Usually they are in an 'h3' or 'div' with class 'title' next to the edit link.
# Or we can just find 'shopier-store--store-product-card-title' in the page? No, listproduct.php is the admin panel.
