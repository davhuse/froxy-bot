# -*- coding: utf-8 -*-
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Update miniapp/products_db.json
with open('miniapp/products_db.json', 'r', encoding='utf-8') as f:
    kv_db = json.load(f)

for p in kv_db:
    if p.get('id') == 'kv_disney_ortak_49':
        p['title'] = 'Disney+ 1 Aylık Ortak Hesap'
        p['price'] = '49,90 TL'
        p['price_num'] = 49.9
        p['url'] = 'https://www.shopier.com/51358329'
        p['shopier_url'] = 'https://www.shopier.com/51358329'
        p['shopier_product_id'] = '51358329'
        p['description'] = 'Disney+ 1 Aylık Ortak Hesap. 4K Ultra HD kalitesinde, 30 gün kesintisiz telafi garantilidir. Satın alım sonrası anında teslim edilir.'
        p['badge'] = 'Fırsat Ürünü'
        p['category_label'] = 'EĞLENCE'
    elif p.get('id') == 'kv_disney_ozel_99':
        p['title'] = 'Disney+ 1 Aylık Özel Profil'
        p['price'] = '99,90 TL'
        p['price_num'] = 99.9
        p['url'] = 'https://www.shopier.com/51358330'
        p['shopier_url'] = 'https://www.shopier.com/51358330'
        p['shopier_product_id'] = '51358330'
        p['description'] = 'Disney+ 1 Aylık Kişisel Özel Profil. Size özel PIN korumalı profil, 4K Ultra HD, 30 gün kesintisiz garanti.'
        p['badge'] = 'VIP Özel Profil'
        p['category_label'] = 'EĞLENCE'

with open('miniapp/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(kv_db, f, ensure_ascii=False, indent=2)
print("Güncellendi: miniapp/products_db.json")

# 2. Update miniapp_lisansarena/products_db.json
with open('miniapp_lisansarena/products_db.json', 'r', encoding='utf-8') as f:
    la_db = json.load(f)

# Filter out old disney if any
la_db = [p for p in la_db if p.get('id') not in ('la_disney_ortak_69', 'la_disney_ozel_119')]

la_db.insert(0, {
    "id": "la_disney_ozel_119",
    "title": "Disney+ 1 Aylık Özel Profil",
    "price": "119.90 TL",
    "category": "entertainment",
    "is_vitrin": True,
    "showcase": True,
    "badge": "VIP ÖZEL PROFİL",
    "image": "assets/products/disney_ozel_99.jpg",
    "rating": 5.0,
    "sales_count": 0,
    "delivery": "Anında Otomatik Teslimat",
    "warranty": "30 Gün Tam Garanti",
    "desc": "Disney+ 1 Aylık Size Özel Profil. Size özel PIN korumalı profil, 4K Ultra HD kalitesi. 30 gün tam lisans ve destek güvencesi. Otomatik anında teslimat.",
    "shopier_url": "https://www.shopier.com/51358332",
    "shopier_product_id": "51358332",
    "shopier_owner": "lisansarena",
    "price_num": 119.9
})

la_db.insert(1, {
    "id": "la_disney_ortak_69",
    "title": "Disney+ 1 Aylık Ortak Profil",
    "price": "69.90 TL",
    "category": "entertainment",
    "is_vitrin": True,
    "showcase": True,
    "badge": "FIRSAT ÜRÜNÜ",
    "image": "assets/products/disney_ortak_49.jpg",
    "rating": 4.9,
    "sales_count": 0,
    "delivery": "Anında Otomatik Teslimat",
    "warranty": "30 Gün Telafi Garantili",
    "desc": "Disney+ 1 Aylık Ortak Profil Kullanımı. 4K Ultra HD, sınırsız dizi ve film keyfi. 30 gün kesintisiz telafi ve destek garantili. Otomatik anında teslimat.",
    "shopier_url": "https://www.shopier.com/51358331",
    "shopier_product_id": "51358331",
    "shopier_owner": "lisansarena",
    "price_num": 69.9
})

with open('miniapp_lisansarena/products_db.json', 'w', encoding='utf-8') as f:
    json.dump(la_db, f, ensure_ascii=False, indent=2)
print("Güncellendi: miniapp_lisansarena/products_db.json")

# 3. Update keyvadi_shopier_links.json
with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
    kv_links = json.load(f)

# Filter out old disney links
kv_links = [l for l in kv_links if 'disney' not in l.get('title', '').lower() and l.get('id') not in ('51358329', '51358330')]
kv_links.insert(0, {
    "id": "51358330",
    "title": "Disney+ 1 Aylık Özel Profil",
    "price": "99,90 TL",
    "url": "https://www.shopier.com/51358330"
})
kv_links.insert(1, {
    "id": "51358329",
    "title": "Disney+ 1 Aylık Ortak Hesap",
    "price": "49,90 TL",
    "url": "https://www.shopier.com/51358329"
})

with open('keyvadi_shopier_links.json', 'w', encoding='utf-8') as f:
    json.dump(kv_links, f, ensure_ascii=False, indent=2)
print("Güncellendi: keyvadi_shopier_links.json")

# 4. Update lisansarena_shopier_links.json
with open('lisansarena_shopier_links.json', 'r', encoding='utf-8') as f:
    la_links = json.load(f)

la_links = [l for l in la_links if 'disney' not in l.get('title', '').lower() and l.get('id') not in ('51358331', '51358332')]
la_links.insert(0, {
    "id": "51358332",
    "title": "Disney+ 1 Aylık Özel Profil",
    "price": "119.90 TL",
    "price_num": 119.9,
    "url": "https://www.shopier.com/51358332"
})
la_links.insert(1, {
    "id": "51358331",
    "title": "Disney+ 1 Aylık Ortak Profil",
    "price": "69.90 TL",
    "price_num": 69.9,
    "url": "https://www.shopier.com/51358331"
})

with open('lisansarena_shopier_links.json', 'w', encoding='utf-8') as f:
    json.dump(la_links, f, ensure_ascii=False, indent=2)
print("Güncellendi: lisansarena_shopier_links.json")

# 5. Update disney_products.json
disney_all = [
    {
        "key": "kv_disney_ortak",
        "brand": "keyvadi",
        "title": "Disney+ 1 Aylık Ortak Hesap",
        "display_title": "Disney+ 1 Aylık Ortak Hesap",
        "price": "49.90",
        "product_id": "51358329",
        "shopier_url": "https://www.shopier.com/51358329",
        "image": "assets/products/disney_ortak_49.jpg",
        "description": "Disney+ 1 aylık ortak profil erişimi. 4K UHD, 30 gün kesintisiz telafi garantili."
    },
    {
        "key": "kv_disney_ozel",
        "brand": "keyvadi",
        "title": "Disney+ 1 Aylık Özel Profil",
        "display_title": "Disney+ 1 Aylık Özel Profil",
        "price": "99.90",
        "product_id": "51358330",
        "shopier_url": "https://www.shopier.com/51358330",
        "image": "assets/products/disney_ozel_99.jpg",
        "description": "Disney+ 1 aylık kişisel özel profil. Size özel PIN korumalı, 4K UHD, 30 gün garantili."
    },
    {
        "key": "la_disney_ortak",
        "brand": "lisansarena",
        "title": "Disney+ 1 Aylık Ortak Profil",
        "display_title": "Disney+ 1 Aylık Ortak Profil",
        "price": "69.90",
        "product_id": "51358331",
        "shopier_url": "https://www.shopier.com/51358331",
        "image": "assets/products/disney_ortak_49.jpg",
        "description": "Disney+ 1 aylık ortak profil erişimi. 30 gün telafi garantili."
    },
    {
        "key": "la_disney_ozel",
        "brand": "lisansarena",
        "title": "Disney+ 1 Aylık Özel Profil",
        "display_title": "Disney+ 1 Aylık Özel Profil",
        "price": "119.90",
        "product_id": "51358332",
        "shopier_url": "https://www.shopier.com/51358332",
        "image": "assets/products/disney_ozel_99.jpg",
        "description": "Disney+ 1 aylık özel profil erişimi. PIN korumalı, 30 gün garantili."
    }
]

with open('disney_products.json', 'w', encoding='utf-8') as f:
    json.dump(disney_all, f, ensure_ascii=False, indent=2)
print("Güncellendi: disney_products.json")
