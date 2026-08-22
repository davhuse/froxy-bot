# -*- coding: utf-8 -*-
"""
Restore all original LisansArena products from Git and merge with newly added products,
ensuring all categories (AI, Cinema, Gaming, Design, Software, Social, Coupons) have their
complete full catalog with verified images, descriptions, badges, and pricing.
"""

import json
import subprocess
import os

# 1. Fetch original 34 products from Git commit c7042b2
raw_old = subprocess.check_output(
    ['git', 'show', 'c7042b2:miniapp_lisansarena/products_db.json'],
    text=True,
    encoding='utf-8'
)
old_products = json.loads(raw_old)

# 2. Fetch current 26 products
with open('miniapp_lisansarena/products_db.json', 'r', encoding='utf-8') as f:
    current_products = json.load(f)

# Normalize old products and fix any image references
merged = []
seen_titles = set()

# Process old original products first
for p in old_products:
    pid = str(p.get('id', ''))
    title = p.get('title', '').strip()
    
    # Check best image available
    cover_img = f"assets/products/la_cover_{pid}.jpg"
    gold_img = f"assets/products/la_gold_{pid}.jpg"
    v7_img = f"assets/products/la_v7_{pid}.jpg"
    art_img = f"assets/products/art_{pid}.jpg"
    
    selected_img = p.get('image', art_img)
    if os.path.exists(os.path.join('miniapp_lisansarena', cover_img)):
        selected_img = cover_img
    elif os.path.exists(os.path.join('miniapp_lisansarena', gold_img)):
        selected_img = gold_img
    elif os.path.exists(os.path.join('miniapp_lisansarena', v7_img)):
        selected_img = v7_img
    elif os.path.exists(os.path.join('miniapp_lisansarena', art_img)):
        selected_img = art_img

    item = {
        "id": pid,
        "title": title,
        "price": p.get('price', '49,90 TL'),
        "price_num": float(p.get('price_num', 49.9)),
        "category": p.get('category', 'ai'),
        "image": selected_img,
        "badge": p.get('badge', '💎 Arena VIP' if p.get('showcase') else '⚡ Orijinal'),
        "url": p.get('url', f"https://www.shopier.com/lisansarena/{pid}"),
        "description": p.get('description', f"{title} - LisansArena güvencesiyle anında teslimat."),
        "showcase": bool(p.get('showcase', False)),
        "is_vitrin": bool(p.get('is_vitrin', False))
    }
    merged.append(item)
    seen_titles.add(title.lower())

# Process newly added products
for p in current_products:
    title = p.get('title', '').strip()
    # If the product title isn't a direct duplicate of an existing old product
    norm_title = title.lower()
    if norm_title not in seen_titles:
        merged.append(p)
        seen_titles.add(norm_title)

print(f"Total merged products for LisansArena: {len(merged)}")
cat_counts = {}
for p in merged:
    c = p.get('category', 'unknown')
    cat_counts[c] = cat_counts.get(c, 0) + 1

print("Categories breakdown:")
for c, cnt in cat_counts.items():
    print(f"  - {c}: {cnt} items")

with open('miniapp_lisansarena/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print("Saved miniapp_lisansarena/products_db.json successfully!")
