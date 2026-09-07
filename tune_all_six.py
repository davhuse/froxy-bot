# -*- coding: utf-8 -*-
import sys

# Baseline old lengths
# Keyvadi 1: 1196
# Keyvadi 2: 1246
# Keyvadi 3: 1289
# Keyvadi 4: 1112
# Keyvadi 5: 1232
# Keyvadi 6: 1243

# Target: exactly -15 characters (or -10 to -20 range)

t1 = """[ KEYVADİ | GÜNCEL DİJİTAL ÜRÜN & LİSANS LİSTESİ ]

Popüler abonelik, yapay zekâ, oyun ve yazılımlar tek adreste:

Film, Dizi & Müzik:
• Netflix 4K UHD Profil: 79,90₺ | Ortak: 39,99₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Spotify Premium (4 Ay): 34,99₺ | Prime Video: 29,90₺
• Disney+ UHD: 99,90₺ | HBO Max: 39,90₺ | Exxen: 34,99₺

Yapay Zekâ, Tasarım & Ofis:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro: 49,90₺ | Adobe CC 1 Ay: 119,99₺
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• Perplexity Pro: 119,90₺ | DeepL Pro: 29,90₺

Oyun & Kuponlar:
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam Oyun: 60₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Güven ve Garanti:
- +1000'den fazla başarılı işlem ve referansımız mevcuttur.
- Kapanma ve sorunlara karşı süre boyunca telafi garantilidir.
- Shopier ile 3D Secure kart veya havale ile güvenli ödeme.

Sorularınız ve doğrudan sipariş için: @KeyvadiDestek
7/24 Otomatik Sipariş Botu: @KeyVadiSatisBot"""

# Let's tune t1: current len 1184 -> diff -12. (Already in -10 to -20 range!)
# If we want exactly -15: remove 3 characters.

t2 = """[ KEYVADİ | YAPAY ZEKÂ, TASARIM VE İÇERİK ARAÇLARI ]

İş, okul, içerik üretimi ve tasarım için popüler yazılımlar:

Yapay Zekâ ve Tasarım:
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Canva Pro 1 Yıl (Kendi Mailinize Davet): 49,90₺ | Öğretmen: 79,90₺
• Gemini Pro 18 Ay Davet: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Video Ortak: 49,90₺ | Kişisel Hesap: 199,90₺
• Perplexity Pro: 119,90₺ | DeepL Pro Çeviri: 29,90₺
• Adobe Creative Cloud (1 Ay): 119,99₺ | 1 Hafta: 49,99₺
• Adobe Express Premium 3 Ay: 99,99₺
• Grammarly Pro: 49,90₺ | Gamma Pro: 299,99₺

Ofis, Eğlence & Oyun:
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | Disney+ UHD: 99,90₺
• Minecraft + Game Pass: 49,90₺ | Xbox Game Pass: 49,90₺
• Trendyol Market ve Yemek İndirim Kuponları: 49,99₺

Güvenilirlik ve Satış Şartlarımız:
- +1000'den fazla başarılı işlem ve referansımız mevcuttur.
- Süre boyunca kapanmaya karşı %100 telafi ve değişim garantisi.
- Shopier altyapısıyla 3D Secure kart ve havale güvencesi.

Detaylı bilgi, referanslar ve doğrudan alım için: @KeyvadiDestek
Hızlı Sipariş Botu: @KeyVadiSatisBot"""

t3 = """[ KEYVADİ | FİLM, DİZİ, MÜZİK VE EĞLENCE SERVİSLERİ ]

Popüler eğlence üyelikleri, oyun ve dijital lisanslar tek adreste:

Eğlence ve Streaming:
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | Prime Video: 29,90₺
• Disney+ UHD Reklamsız: 99,90₺ | HBO Max: 39,90₺ | Exxen: 34,99₺
• Crunchyroll Ortak: 39,90₺ | Özel Hesap: 59,90₺ | 3 Ay: 99,90₺
• Scribd Ortak: 29,90₺ | Kişisel Hesap: 59,90₺

Yazılım, AI ve Oyun:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Gemini Pro 18 Ay: 99,90₺
• Windows 10/11 Pro Lisans: 70₺ | Office 365 (1 Yıl): 70₺
• CapCut Pro: 49,90₺ | Adobe Creative Cloud 1 Ay: 119,99₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | Steam İstediğin Oyun: 60₺
• Discord Nitro 14X Boost: 224,99₺ | VIP Key: 30₺
• Trendyol Market ve Yemek İndirim Kuponları: 49,99₺

Hizmet ve İşlem Güvencemiz:
- +1000'den fazla başarılı satış referansımız bulunmaktadır.
- Donma veya kapanmaya karşı süre boyunca anında telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale geçerlidir.

Canlı destek, referanslar ve sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

t4 = """[ KEYVADİ | ÖĞRENCİ VE ÇALIŞAN DİJİTAL İHTİYAÇLARI ]

Ders, sunum, proje ve iş akışınız için temel dijital lisanslar:

Üretkenlik ve Yazılım:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Microsoft Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro: 70₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro: 49,90₺ | Adobe Creative Cloud 1 Ay: 119,99₺
• Perplexity Pro: 119,90₺ | DeepL Pro Çeviri: 29,90₺

Medya, Eğlence ve Oyun:
• YouTube Premium 3 Ay: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | Disney+ UHD: 99,90₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | Steam: 60₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Satış ve Garanti Şartlarımız:
- +1000'den fazla işlem ve referans geçmişimiz mevcuttur.
- Satın aldığınız süre boyunca %100 değişim ve telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale güvencesi.

Sorularınız ve doğrudan alım için: @KeyvadiDestek
7/24 Sipariş Botu: @KeyVadiSatisBot"""

t5 = """[ KEYVADİ | OYUN, LİSANS VE ALIŞVERİŞ FIRSATLARI ]

Oyun üyelikleri, orijinal lisanslar ve indirimli alışveriş kuponları:

Oyun & İndirim Kuponları:
• Trendyol Market 800/300 Kuponu: 49,99₺ | Yemek: 49,99₺
• Minecraft Premium + Game Pass Ultimate (1 Ay): 49,90₺ | 3 Ay: 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam Oyun: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺ | VIP Key: 30₺
• FC 26: 299,99₺ | Kaspersky Premium 1 Yıl: 244,99₺

Popüler Lisanslar ve AI:
• Windows 10/11 Pro Orijinal Lisans: 70₺ | Office 365 1 Yıl: 70₺
• Canva Pro 1 Yıl Kendi Mailinize: 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Gemini Pro 18 Ay: 99,90₺
• YouTube Premium 3 Ay: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | CapCut Pro: 49,90₺
• Adobe Creative Cloud 1 Ay: 119,99₺ | DeepL Pro: 29,90₺
• Prime Video: 29,90₺ | Disney+ UHD: 99,90₺

Neden KeyVadi?
- +1000'den fazla başarılı işlem ve müşteri referansımız mevcuttur.
- Tüm ürünlerde süre boyunca teknik destek ve telafi garantisi.
- Shopier 3D Secure güvencesiyle resmi kartla ödeme imkanı.

Doğrudan sipariş, referanslar ve sorularınız için: @KeyvadiDestek
Hızlı Alışveriş Botu: @KeyVadiSatisBot"""

t6 = """[ KEYVADİ | UYGUN FİYATLI POPÜLER DİJİTAL LİSANSLAR ]

Dijital üyelikten yapay zekaya, eğlenceden lisansa çok satanlar:

Popüler Fiyat Listesi:
• Canva Pro 1 Yıl Davet: 49,90₺ | Öğretmen 1 Yıl: 79,90₺
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Gemini Pro 18 Ay Davet: 99,90₺ | 3 Ay: 59,90₺
• Spotify Premium 4 Ay: 34,99₺ | Exxen (3 Ay): 34,99₺
• CapCut Pro Ortak: 49,90₺ | Adobe Creative Cloud 1 Ay: 119,99₺
• Windows 10/11 Pro Orijinal Lisans: 70₺ | Office 365 1 Yıl: 70₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺
• Minecraft Premium (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• DeepL Pro: 29,90₺ | Perplexity Pro: 119,90₺ | Scribd: 29,90₺
• Trendyol Market ve Yemek İndirim Kuponları: 49,99₺
• Discord Nitro 14X: 224,99₺ | Steam İstediğin Oyun: 60₺
• Prime Video Ortak: 9,99₺ | HBO Max: 39,90₺

Güvencelerimiz:
- +1000'den fazla başarılı işlem ve müşteri referansı mevcuttur.
- Kapanma durumunda süre boyunca anında birebir telafi garantisi.
- Shopier 3D Secure ile kart veya havale ile güvenli alışveriş.

Referans kanıtları, soru ve doğrudan sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

templates = [t1, t2, t3, t4, t5, t6]
old_lens = [1196, 1246, 1289, 1112, 1232, 1243]

for i, (t, old_len) in enumerate(zip(templates, old_lens), 1):
    diff = len(t) - old_len
    print(f"Keyvadi {i}: Eski={old_len} | Yeni={len(t)} | Fark={diff:+d} karakter | Satir={len(t.splitlines())}")
