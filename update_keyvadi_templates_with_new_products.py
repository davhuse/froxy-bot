# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# KeyVadi Template 1: Genel Liste
t1 = """[ KEYVADİ | GÜNCEL DİJİTAL ÜRÜN & LİSANS LİSTESİ ]

Popüler abonelik, yapay zekâ, oyun ve yazılımlar tek adreste:

Film, Dizi & Spor:
• Netflix 4K UHD Profil: 79,90₺ | Ortak: 39,99₺
• S Sport Plus (1 Ay): 70₺ | Exxen: 34,99₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Spotify Premium (4 Ay): 34,99₺ | Prime Video: 29,90₺
• Disney+ UHD: 99,90₺ | HBO Max: 39,90₺

Yapay Zekâ, Tasarım & Ofis:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro: 49,90₺ | Adobe CC 1 Ay: 119,99₺
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• Perplexity Pro: 119,90₺ | DeepL Pro: 29,90₺

İndirim Kuponları & Oyun:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Turna.com 600 TL Uçak Bileti Kuponu: 70₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺
• Trendyol Market ve Yemek Kuponları: 49,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺

Güven ve Garanti:
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Kapanma ve sorunlara karşı süre boyunca telafi garantilidir.
- Shopier ile 3D Secure kart veya havale ile güvenli ödeme.

💡 Elinizdeki kuponlar, kodlar ve hesaplar değerinde nakit alınır!
Sorularınız, alım ve satış için: @KeyvadiDestek
7/24 Otomatik Sipariş Botu: @KeyVadiSatisBot"""

# KeyVadi Template 2: Yapay Zekâ, Tasarım ve İçerik Odaklı
t2 = """[ KEYVADİ | YAPAY ZEKÂ, TASARIM VE İÇERİK ARAÇLARI ]

İş, okul, içerik üretimi ve tasarım için popüler yazılımlar:

Yapay Zekâ ve Tasarım:
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Gemini Pro 18 Ay Davet: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Ortak: 49,90₺ | Kişisel Hesap: 199,90₺
• Perplexity Pro: 119,90₺ | DeepL Pro Çeviri: 29,90₺
• Adobe Creative Cloud (1 Ay): 119,99₺ | 1 Hafta: 49,99₺
• Adobe Express Premium 3 Ay: 99,99₺ | Grammarly Pro: 49,90₺

Spor, Eğlence & Kuponlar:
• S Sport Plus (1 Ay): 70₺ | Netflix 4K UHD Profil: 79,90₺
• YouTube Premium 3 Ay Kod: 19,90₺ | Spotify: 34,99₺
• Yemeksepeti 450/350 İndirim Kodu: 60₺ | Tıkla Gelsin: 50₺
• Turna.com 600 TL Uçak Bileti Kuponu: 70₺
• Office 365: 70₺ | Windows 10/11 Pro: 70₺
• Minecraft + Game Pass: 49,90₺ | Trendyol Kupon: 49,99₺

Güvenilirlik ve Satış Şartlarımız:
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Süre boyunca kapanmaya karşı %100 telafi ve değişim garantisi.
- Shopier altyapısıyla 3D Secure kart ve havale güvencesi.

💡 Elinizdeki kuponlar, yemek kodları ve hesaplar nakit alınır!
Detaylı bilgi, referanslar ve işlem için: @KeyvadiDestek
Hızlı Sipariş Botu: @KeyVadiSatisBot"""

# KeyVadi Template 3: Film, Dizi, Spor & Eğlence
t3 = """[ KEYVADİ | FİLM, DİZİ, SPOR VE EĞLENCE SERVİSLERİ ]

Popüler eğlence üyelikleri, spor paketleri ve dijital lisanslar:

Spor, Streaming & Müzik:
• S Sport Plus (1 Ay): 70₺ (Canlı Maçlar & Tekrar İzle)
• Netflix 4K UHD Profil: 79,90₺ | Ortak Hesap: 39,99₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Spotify Premium (4 Ay): 34,99₺ | Prime Video: 29,90₺
• Disney+ UHD Reklamsız: 99,90₺ | HBO Max: 39,90₺ | Exxen: 34,99₺
• Crunchyroll Ortak: 39,90₺ | Özel Hesap: 59,90₺

Yemek & Seyahat Kuponları:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Turna.com 600 TL Uçak Kuponu: 70₺ | Tıkla Gelsin: 50₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

AI, Yazılım ve Oyun:
• Canva Pro 1 Yıl: 49,90₺ | ChatGPT Plus Ortak: 39,90₺
• Gemini Pro 18 Ay: 99,90₺ | CapCut Pro: 49,90₺ | Adobe CC: 119,99₺
• Windows 10/11 Pro: 70₺ | Office 365: 70₺
• Minecraft + Game Pass: 49,90₺ | Discord Nitro 14X: 224,99₺

Hizmet ve İşlem Güvencemiz:
- +100'den fazla başarılı işlem ve referansımız bulunmaktadır.
- Donma veya kapanmaya karşı süre boyunca anında telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale geçerlidir.

💡 Elinizdeki indirim kuponları ve hesaplar değerinde nakit alınır!
Canlı destek, kupon satışı ve sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

# KeyVadi Template 4: Öğrenci, Çalışan & Günlük İhtiyaçlar
t4 = """[ KEYVADİ | ÖĞRENCİ VE ÇALIŞAN DİJİTAL İHTİYAÇLARI ]

Ders, sunum, proje, yemek ve seyahat için avantajlı lisanslar:

Üretkenlik ve Yazılım:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Ortak: 49,90₺ | Adobe CC 1 Ay: 119,99₺
• Perplexity Pro: 119,90₺ | DeepL Pro Çeviri: 29,90₺

Yemek, Seyahat ve Eğlence:
• Yemeksepeti 450/350 İndirim Kodu: 60₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺
• Turna.com 600 TL Uçak Kuponu: 70₺ | Trendyol Kupon: 49,99₺
• S Sport Plus (1 Ay): 70₺ | Netflix 4K Profil: 79,90₺
• YouTube Premium 3 Ay: 19,90₺ | Spotify Premium: 34,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | Steam Oyun: 60₺

Satış ve Garanti Şartlarımız:
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Satın aldığınız süre boyunca %100 değişim ve telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale güvencesi.

💡 Elinizdeki kupon kodları ve hesaplar nakit paraya çevrilir!
Sorularınız, alım ve satış için: @KeyvadiDestek
7/24 Sipariş Botu: @KeyVadiSatisBot"""

# KeyVadi Template 5: Oyun, Kupon & Alışveriş Fırsatları
t5 = """[ KEYVADİ | OYUN, KUPON VE ALIŞVERİŞ FIRSATLARI ]

İndirimli alışveriş kuponları, spor üyelikleri ve popüler lisanslar:

Kuponlar & Fırsatlar:
• Yemeksepeti 450₺/350₺ İndirim Kodu: 60₺
• Turna.com 600 TL Uçak Kuponu: 70₺
• Tıkla Gelsin® 400/200 Yemek Kuponu: 50₺
• Trendyol Market 800/300 Kuponu: 49,99₺ | Yemek: 49,99₺
• S Sport Plus 1 Aylık Premium: 70₺
• Minecraft Premium + Game Pass (1 Ay): 49,90₺ | 3 Ay: 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺

Popüler Lisanslar ve AI:
• Windows 10/11 Pro Lisans: 70₺ | Office 365 1 Yıl: 70₺
• Canva Pro (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Gemini Pro 18 Ay: 99,90₺
• Netflix 4K Profil: 79,90₺ | YouTube Premium 3 Ay: 19,90₺
• Spotify Premium (4 Ay): 34,99₺ | CapCut Pro: 49,90₺
• Adobe Creative Cloud 1 Ay: 119,99₺

Neden KeyVadi?
- +100'den fazla başarılı işlem ve müşteri referansımız mevcuttur.
- Tüm ürünlerde süre boyunca teknik destek ve telafi garantisi.
- Shopier 3D Secure güvencesiyle resmi kartla ödeme imkanı.

💡 Elinizdeki tüm indirim kuponları ve hesaplar değerinde nakit alınır!
Doğrudan sipariş, referanslar ve kupon satışı için: @KeyvadiDestek
Hızlı Alışveriş Botu: @KeyVadiSatisBot"""

# KeyVadi Template 6: Popüler Çok Satanlar & Yeni Ürünler
t6 = """[ KEYVADİ | ÇOK SATANLAR VE YENİ DİJİTAL KUPONLAR ]

Yemekten spora, yapay zekadan lisansa en popüler KeyVadi ürünleri:

Çok Satan Güncel Liste:
• S Sport Plus (1 Ay): 70₺ (Premier League & EuroLeague)
• Yemeksepeti 450₺/350₺ İndirim Kodu: 60₺
• Turna.com 600 TL Uçak Bileti Kuponu: 70₺
• Tıkla Gelsin 400/200 Yemek Kuponu: 50₺
• Canva Pro 1 Yıl Davet: 49,90₺ | Öğretmen 1 Yıl: 79,90₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Gemini Pro 18 Ay Davet: 99,90₺ | 3 Ay: 59,90₺
• Spotify Premium 4 Ay: 34,99₺ | Exxen: 34,99₺
• CapCut Pro Ortak: 49,90₺ | Adobe Creative Cloud 1 Ay: 119,99₺
• Windows 10/11 Pro: 70₺ | Office 365 1 Yıl: 70₺
• Minecraft Premium: 49,90₺ | Xbox Game Pass: 49,90₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Güvencelerimiz:
- +100'den fazla başarılı işlem ve müşteri referansı mevcuttur.
- Kapanma durumunda süre boyunca anında birebir telafi garantisi.
- Shopier 3D Secure ile kart veya havale ile güvenli alışveriş.

💡 Elinizdeki kupon kodları, yemek çekleri ve hesaplar nakit alınır!
Referanslar, kupon satışı ve doğrudan sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

templates = [t1, t2, t3, t4, t5, t6]

for i, t in enumerate(templates, 1):
    path = f"messages/keyvadi_{i}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(t)
    print(f"Written: {path} | Length: {len(t)} chars | Lines: {len(t.splitlines())}")

print("\nAll 6 templates updated!")
