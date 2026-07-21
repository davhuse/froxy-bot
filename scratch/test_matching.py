import json
import re
import os

def match_multiple_products_from_text(text, product_list):
    text_lower = text.lower()
    matched = []
    
    # 1. Birebir Baslik Eslestirme
    for p in product_list:
        title_lower = p['title'].lower()
        if title_lower in text_lower:
            matched.append(p)
            
    if matched:
        return matched
        
    # 2. Kelime Bazli Eslestirme
    for p in product_list:
        title_lower = p['title'].lower()
        title_words = set(re.findall(r'\w+', title_lower))
        text_words = set(re.findall(r'\w+', text_lower))
        
        # Ozel kelime agirliklari: bazi kelimeler urun ayirt etmek icin onemli
        important_keywords = {"netflix", "youtube", "canva", "adobe", "capcut", "gemini", "grok", "steam", "zula", "fc26", "hbo", "prime", "duolingo", "scribd", "deepl", "perplexity", "grammarly"}
        
        title_important = title_words.intersection(important_keywords)
        
        if title_important and title_important.issubset(text_words):
            # Alt varyasyon kontrolleri (aylik, ortak, ozel vb.)
            if "ortak" in title_words and "ortak" not in text_words:
                continue
            if "özel" in title_words and "özel" not in text_words and "kisisel" not in text_words:
                continue
                
            matched.append(p)
            
    return matched

# Test
with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
    keyvadi_products = json.load(f)

with open('lisansarena_shopier_links.json', 'r', encoding='utf-8') as f:
    lisansarena_products = json.load(f)

test_cases = [
    ("gemini pro 1 yillik davet alabilir miyim", keyvadi_products),
    ("lisansarena canva pro var mi", lisansarena_products),
    ("netflix ortak paket fiyat", keyvadi_products),
    ("steam random key almak istiyorum", lisansarena_products)
]

print("=== TEST SONUCLARI ===")
for msg, plist in test_cases:
    print(f"\nMesaj: '{msg}'")
    matched = match_multiple_products_from_text(msg, plist)
    if not matched:
        print("  - Bulunamadi")
    for p in matched:
        print(f"  + {p['title']} ({p.get('price', '0')}) -> {p['url']}")
