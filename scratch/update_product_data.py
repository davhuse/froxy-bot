import json
import re
import os

def update_keyvadi():
    path = "keyvadi_shopier_links.json"
    if not os.path.exists(path):
        print(f"{path} not found.")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    updated = 0
    for item in data:
        pid = item.get("id")
        title = item.get("title", "")
        
        # 1. Netflix UHD Kişisel Profil -> 79.99 TL
        if pid == "47669117" or "netflix" in title.lower() and "profil" in title.lower():
            item["price"] = "79.99 TL"
            updated += 1
            print(f"Updated KV: {item['title']} price to 79.99 TL")
            
        # 2. Gemini Pro Davet -> Gemini Pro 12 Aylık (Davet Linki) & 69.99 TL
        if pid == "47669164" or (title == "Gemini Pro (Davet Linki)"):
            item["title"] = "Gemini Pro 12 Aylık (Davet Linki)"
            item["price"] = "69.99 TL"
            updated += 1
            print(f"Updated KV: {item['title']} to Gemini Pro 12 Aylık (Davet Linki) & 69.99 TL")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"KeyVadi JSON updated ({updated} items).")

def update_lisansarena():
    path = "lisansarena_shopier_links.json"
    if not os.path.exists(path):
        print(f"{path} not found.")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    updated = 0
    for item in data:
        pid = item.get("id")
        title = item.get("title", "")
        
        # 1. Canva Pro 1 Yıllık Yetki -> 79.99
        if pid == "48973858" or "canva pro" in title.lower() and "yıllık" in title.lower():
            item["priceData"]["price"] = "79.99"
            item["priceData"]["discountedPrice"] = "79.99"
            item["description"] = "Canva Pro 1 Yıllık Yetkilendirme. Kendi kişisel hesabınıza Pro özellikleri tanımlanır."
            updated += 1
            print(f"Updated LA: {item['title']} price to 79.99")
            
        # 2. Duolingo Ortak -> Duolingo 1 Aylık (Ortak Hesap) & 29.99
        if pid == "48901876" or "duolingo" in title.lower():
            item["title"] = "Duolingo 1 Aylık (Ortak Hesap)"
            item["priceData"]["price"] = "29.99"
            item["priceData"]["discountedPrice"] = "29.99"
            item["description"] = "Super Duolingo Premium 1 Aylık Ortak Kullanım Hesabı. UYARI: Ortak hesaptır."
            updated += 1
            print(f"Updated LA: {item['title']} to 1 Aylık (Ortak Hesap) & 29.99")
            
        # 3. Gemini Pro Davet (12 Aylık) -> 99.99
        if pid == "48945492" or title == "Gemini Pro Davet (12 Aylık)":
            item["priceData"]["price"] = "99.99"
            item["priceData"]["discountedPrice"] = "99.99"
            item["description"] = "Gemini Pro Davet Linki ile kendi 12 aylık üyeliğinizi aktifleştirme."
            updated += 1
            print(f"Updated LA: {item['title']} price to 99.99")
            
        # 4. Gemini Pro Premium Hesap (12 Aylık) -> 99.99
        if pid == "48945493" or title == "Gemini Pro Premium Hesap (12 Aylık)":
            item["priceData"]["price"] = "99.99"
            item["priceData"]["discountedPrice"] = "99.99"
            updated += 1
            print(f"Updated LA: {item['title']} price to 99.99")
            
        # 5. YouTube Premium 3 Aylık Kod description warning
        if pid == "48973855" or "youtube premium" in title.lower():
            item["description"] = "YouTube Premium 3 Aylık Aktivasyon Kodu. Reklamsız video izleme ve YouTube Music Premium dahildir. UYARI: Yeni hesaplarda veya daha önce Premium alınmamış hesaplarda aktifleştirilmelidir."
            updated += 1
            print(f"Updated LA description: {item['title']}")
            
        # 6. Spotify Premium 4 Aylık description warning
        if pid == "48973857" or "spotify premium" in title.lower():
            item["description"] = "Spotify Premium 4 Aylık Aktivasyon Kodu. Kendi kişisel hesabınıza tanımlanır. UYARI: Daha önce Premium üyeliği aktif edilmemiş (yeni/bireysel) hesaplarda geçerlidir."
            updated += 1
            print(f"Updated LA description: {item['title']}")
            
        # 7. Perplexity Pro description warning
        if "perplexity" in title.lower():
            item["description"] = "Perplexity Pro Yapay Zeka Arama Motoru 1 Aylık Ortak Hesap. Giriş garantilidir. UYARI: Ortak hesaptır."
            updated += 1
            print(f"Updated LA description: {item['title']}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"LisansArena JSON updated ({updated} items).")

def update_froxy_bot():
    path = "froxy_bot.py"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Update INJECTED_PRODUCTS in froxy_bot.py
    # "id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "49.99 TL" -> "price": "79.99 TL"
    # "id": "47669164", "title": "Gemini Pro (Davet Linki)", "price": "124.99 TL" -> "title": "Gemini Pro 12 Aylık (Davet Linki)", "price": "69.99 TL"
    
    pattern1 = r'\{"id": "47669117", "title": "Netflix 4K Ultra HD \(Kişisel Profil\)", "price": "49.99 TL"'
    replacement1 = '{"id": "47669117", "title": "Netflix 4K Ultra HD (Kişisel Profil)", "price": "79.99 TL"'
    
    pattern2 = r'\{"id": "47669164", "title": "Gemini Pro \(Davet Linki\)", "price": "124.99 TL"'
    replacement2 = '{"id": "47669164", "title": "Gemini Pro 12 Aylık (Davet Linki)", "price": "69.99 TL"'
    
    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replacement2, content)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("froxy_bot.py updated.")

def update_create_listings():
    path = "create_shopier_listings.py"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Update YouTube Premium (3 Aylık Kod) description
    content = content.replace(
        '"desc": "YouTube Premium 3 Aylık Aktivasyon Kodu. Reklamsız video izleme ve YouTube Music Premium dahildir. Kendi hesabınızda veya yeni hesapta aktifleştirebilirsiniz."',
        '"desc": "YouTube Premium 3 Aylık Aktivasyon Kodu. Reklamsız video izleme ve YouTube Music Premium dahildir. UYARI: Yeni hesaplarda veya daha önce Premium alınmamış hesaplarda aktifleştirilmelidir."'
    )
    
    # Update Spotify Premium (4 Aylık Kod) description
    content = content.replace(
        '"desc": "Spotify Premium 4 Aylık Aktivasyon Kodu. Kendi kişisel hesabınıza tanımlanır. Reklamsız ve yüksek kaliteli müzik keyfi."',
        '"desc": "Spotify Premium 4 Aylık Aktivasyon Kodu. Kendi kişisel hesabınıza tanımlanır. Reklamsız ve yüksek kaliteli müzik keyfi. UYARI: Daha önce Premium üyeliği aktif edilmemiş (yeni/bireysel) hesaplarda geçerlidir."'
    )
    
    # Update XBOX Game Pass Ultimate (3 Aylık Üyelik) description
    content = content.replace(
        '"desc": "3 Aylık XBOX Game Pass Ultimate üyeliği aktif hesap. PC ve konsolda yüzlerce oyuna ücretsiz erişim sağlar."',
        '"desc": "3 Aylık XBOX Game Pass Ultimate üyeliği aktif ortak hesap. PC ve konsolda yüzlerce oyuna ücretsiz erişim sağlar. UYARI: Ortak hesaptır."'
    )
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("create_shopier_listings.py updated.")

if __name__ == "__main__":
    update_keyvadi()
    update_lisansarena()
    update_froxy_bot()
    update_create_listings()
