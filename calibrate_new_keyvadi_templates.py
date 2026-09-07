# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("messages/keyvadi_1.txt", "r", encoding="utf-8") as f:
    orig_1 = f.read()

t1 = orig_1
t1 = t1.replace("• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺", "• Canva Pro 1 Yıl (Kendi Mail): 49,90₺ | Öğretmen: 79,90₺")
t1 = t1.replace("• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺", "• ChatGPT Plus Ortak: 39,90₺ | Kişisel: 499,90₺")
t1 = t1.replace("- +100'den fazla başarılı işlem ve referansımız mevcuttur.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")
t1 = t1.replace("- Kapanma ve sorunlara karşı süre boyunca telafi garantilidir.", "- Kapanmaya karşı süre boyunca telafi garantilidir.")
t1 = t1.replace("- Shopier ile 3D Secure kart veya havale ile güvenli ödeme.", "- Shopier ile 3D Secure kart veya havale güvencesi.")
t1 = t1.replace("💡 Elinizdeki kuponlar, kodlar ve hesaplar değerinde nakit alınır!", "💡 Elinizdeki kuponlar ve kodlar değerinde nakit alınır!")

old_kupon1 = """İndirim Kuponları & Oyun:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Turna 600 TL Uçak Bileti Kuponu: 70₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺
• Trendyol Market ve Yemek Kuponları: 49,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺"""

new_kupon1 = """İndirim Kuponları & Oyun:
• Yemeksepeti 200/200: 50₺ | 450/350 İndirim Kodu: 60₺
• Coffy 2 Kahve Alana 1 Bedava: 45₺ | Migros 100 TL Bakiye: 50₺
• Turna 600 TL Uçak Bileti Kuponu: 70₺ | Tıkla Gelsin: 50₺
• Trendyol Market ve Yemek Kuponları: 49,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺"""

t1 = t1.replace(old_kupon1, new_kupon1)

# Template 2
with open("messages/keyvadi_2.txt", "r", encoding="utf-8") as f:
    orig_2 = f.read()

t2 = orig_2
old_kupon2 = """Spor, Eğlence & Kuponlar:
• S Sport Plus (1 Ay): 70₺ | Netflix 4K UHD Profil: 79,90₺
• YouTube Premium 3 Ay Kod: 19,90₺ | Spotify: 34,99₺
• Yemeksepeti 450/350 İndirim Kodu: 60₺ | Tıkla Gelsin: 50₺
• Turna 600 TL Uçak Bileti Kuponu: 70₺
• Office 365: 70₺ | Windows 10/11 Pro: 70₺
• Minecraft + Game Pass: 49,90₺ | Trendyol Kupon: 49,99₺"""

new_kupon2 = """Spor, Eğlence & Kuponlar:
• S Sport Plus (1 Ay): 70₺ | Netflix 4K UHD: 79,90₺
• Yemeksepeti 200/200: 50₺ | 450/350: 60₺ | Turna: 70₺
• Coffy 2 Al 1 Öde: 45₺ | Migros 100 TL Bakiye: 50₺ | Tıkla Gelsin: 50₺
• YouTube Premium 3 Ay: 19,90₺ | Spotify: 34,99₺
• Office 365: 70₺ | Windows 10/11 Pro: 70₺
• Minecraft + Game Pass: 49,90₺ | Trendyol Kupon: 49,99₺"""

t2 = t2.replace(old_kupon2, new_kupon2)
t2 = t2.replace("• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺", "• Canva Pro 1 Yıl (Kendi Mail): 49,90₺ | Öğretmen: 79,90₺")
t2 = t2.replace("• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺", "• ChatGPT Plus Ortak: 39,90₺ | Kişisel: 499,90₺")
t2 = t2.replace("- +100'den fazla başarılı işlem ve referansımız mevcuttur.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")
t2 = t2.replace("Detaylı bilgi, referanslar ve işlem için: @KeyvadiDestek", "Detaylı bilgi, referans ve işlem için: @KeyvadiDestek")
t2 = t2.replace("💡 Elinizdeki kuponlar, yemek kodları ve hesaplar nakit alınır!", "💡 Elinizdeki kuponlar, kodlar ve hesaplar nakit alınır!")

# Template 3
with open("messages/keyvadi_3.txt", "r", encoding="utf-8") as f:
    orig_3 = f.read()

t3 = orig_3
old_kupon3 = """Yemek & Seyahat Kuponları:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Turna 600 TL Uçak Kuponu: 70₺ | Tıkla Gelsin: 50₺
• Trendyol Market ve Yemek Kuponları: 49,99₺"""

new_kupon3 = """Yemek & Seyahat & Market Kuponları:
• Yemeksepeti 200/200: 50₺ | 450/350: 60₺ | Turna: 70₺
• Coffy 2 Al 1 Öde: 45₺ | Migros 100 TL Bakiye: 50₺
• Tıkla Gelsin: 50₺ | Trendyol Kuponları: 49,99₺"""

t3 = t3.replace(old_kupon3, new_kupon3)
t3 = t3.replace("• Disney+ UHD Reklamsız: 99,90₺", "• Disney+ UHD: 99,90₺")
t3 = t3.replace("Popüler eğlence üyelikleri, spor paketleri ve dijital lisanslar:", "Popüler eğlence üyelikleri, spor ve dijital lisanslar:")
t3 = t3.replace("- +100'den fazla başarılı işlem ve referansımız bulunmaktadır.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")
t3 = t3.replace("- Donma veya kapanmaya karşı süre boyunca anında telafi garantisi.", "- Donmaya ve kapanmaya karşı süre boyunca telafi garantisi.")

# Template 4
with open("messages/keyvadi_4.txt", "r", encoding="utf-8") as f:
    orig_4 = f.read()

t4 = orig_4
old_kupon4 = """Yemek, Seyahat ve Eğlence:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺
• Turna 600 TL Uçak Kuponu: 70₺ | Trendyol Kupon: 49,99₺
• S Sport Plus (1 Ay): 70₺ | Netflix 4K Profil: 79,90₺
• YouTube Premium 3 Ay: 19,90₺ | Spotify Premium: 34,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | Steam Oyun: 60₺"""

new_kupon4 = """Yemek, Market, Seyahat ve Eğlence:
• Yemeksepeti 200/200: 50₺ | 450/350: 60₺ | Turna: 70₺
• Coffy 2 Al 1 Öde: 45₺ | Migros 100 TL Bakiye: 50₺
• Tıkla Gelsin: 50₺ | Trendyol Kupon: 49,99₺
• S Sport Plus (1 Ay): 70₺ | Netflix 4K Profil: 79,90₺
• YouTube Premium 3 Ay: 19,90₺ | Spotify: 34,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | Steam: 60₺"""

t4 = t4.replace(old_kupon4, new_kupon4)
t4 = t4.replace("• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺", "• Canva Pro 1 Yıl (Kendi Mail): 49,90₺ | Öğretmen: 79,90₺")
t4 = t4.replace("- +100'den fazla başarılı işlem ve referansımız mevcuttur.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")

# Template 5
with open("messages/keyvadi_5.txt", "r", encoding="utf-8") as f:
    orig_5 = f.read()

t5 = orig_5
old_kupon5 = """Kuponlar & Fırsatlar:
• Yemeksepeti 450₺/350₺ İndirim Kodu: 60₺
• Turna 600 TL Uçak Kuponu: 70₺
• Tıkla Gelsin® 400/200 Yemek Kuponu: 50₺
• Trendyol Market 800/300 Kuponu: 49,99₺ | Yemek: 49,99₺
• S Sport Plus 1 Aylık Premium: 70₺
• Minecraft Premium + Game Pass (1 Ay): 49,90₺ | 3 Ay: 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺"""

new_kupon5 = """Kuponlar & Fırsatlar:
• Yemeksepeti 200/200: 50₺ | 450/350 İndirim Kodu: 60₺
• Turna 600 TL Uçak Kuponu: 70₺ | Tıkla Gelsin: 50₺
• Coffy 2 Kahve Alana 1'i Bedava: 45₺ | Migros 100 TL Bakiye: 50₺
• Trendyol Market 800/300: 49,99₺ | Yemek: 49,99₺
• S Sport Plus 1 Aylık Premium: 70₺
• Minecraft Premium + Game Pass (1 Ay): 49,90₺ | 3 Ay: 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺"""

t5 = t5.replace(old_kupon5, new_kupon5)
t5 = t5.replace("- +100'den fazla başarılı işlem ve müşteri referansımız mevcuttur.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")
t5 = t5.replace("💡 Elinizdeki tüm indirim kuponları ve hesaplar değerinde nakit alınır!", "💡 Elinizdeki tüm indirim kuponları ve kodlar nakit alınır!")

# Template 6
with open("messages/keyvadi_6.txt", "r", encoding="utf-8") as f:
    orig_6 = f.read()

t6 = orig_6
old_kupon6 = """• S Sport Plus (1 Ay): 70₺ (Premier League & EuroLeague)
• Yemeksepeti 450₺/350₺ İndirim Kodu: 60₺
• Turna 600 TL Uçak Bileti Kuponu: 70₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺"""

new_kupon6 = """• S Sport Plus (1 Ay): 70₺ (Premier League & EuroLeague)
• Yemeksepeti 200/200: 50₺ | 450/350 Kodu: 60₺ | Turna: 70₺
• Coffy 2 Al 1 Öde: 45₺ | Migros 100 TL Bakiye: 50₺ | Tıkla Gelsin: 50₺"""

t6 = t6.replace(old_kupon6, new_kupon6)
t6 = t6.replace("- +100'den fazla başarılı işlem ve müşteri referansı mevcuttur.", "- +100'den fazla başarılı işlem ve referans mevcuttur.")
t6 = t6.replace("💡 Elinizdeki kupon kodları, yemek çekleri ve hesaplar nakit alınır!", "💡 Elinizdeki kupon kodları, kodlar ve hesaplar nakit alınır!")

templates = [
    ("keyvadi_1.txt", orig_1, t1),
    ("keyvadi_2.txt", orig_2, t2),
    ("keyvadi_3.txt", orig_3, t3),
    ("keyvadi_4.txt", orig_4, t4),
    ("keyvadi_5.txt", orig_5, t5),
    ("keyvadi_6.txt", orig_6, t6)
]

for name, o, n in templates:
    diff = len(n) - len(o)
    print(f"{name}: Old={len(o)}, New={len(n)}, Diff={diff:+d} chars")
    assert len(n) > 1100, f"{name} must be > 1100"
    assert "@KeyVadiSatisBot" in n
    assert "Netflix" in n
    assert "79,90" in n
    assert "ChatGPT" in n
    assert "Canva" in n
    assert "Yemeksepeti" in n
    assert "Coffy" in n
    assert "Migros" in n

# Save tuned files
for name, o, n in templates:
    with open(f"messages/{name}", "w", encoding="utf-8") as f:
        f.write(n)

print("\nAll 6 KeyVadi templates successfully updated and verified!")
