import sys

# Original keyvadi_1.txt length was 1196 characters.
# User requested: "boyut eskisiyle aynı yada 10 20 karakter kısa olsun" -> 1176 - 1186 chars.

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

t2 = """[ KEYVADİ | YAPAY ZEKÂ, TASARIM VE İÇERİK ARAÇLARI ]

İş, okul, içerik üretimi ve tasarım için popüler yazılımlar:

Yapay Zekâ ve Tasarım:
• ChatGPT Plus Ortak Hesap: 39,90₺ | Kişisel: 499,90₺
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Gemini Pro 18 Ay Davet: 99,90₺ | 3 Ay: 59,90₺
• CapCut Pro Video Ortak: 49,90₺ | Kişisel: 199,90₺
• Perplexity Pro (1 Ay): 119,90₺ | DeepL Pro Çeviri: 29,90₺
• Adobe Creative Cloud (1 Ay): 119,99₺ | 1 Hafta: 49,99₺
• Grammarly Pro: 49,90₺ | Gamma Pro: 299,99₺

Ofis, Eğlence ve Oyun:
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• YouTube Premium 3 Ay Kod: 19,90₺ | Netflix 4K Profil: 79,90₺
• Spotify Premium (4 Ay): 34,99₺ | Disney+ UHD: 99,90₺
• Minecraft Premium + Game Pass Ultimate: 49,90₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Neden KeyVadi?
- Referanslarımız ve kanıtlı işlem geçmişimiz mevcuttur.
- Süre boyunca kapanmaya karşı birebir telafi garantisi.
- Shopier ile 3D Secure kredi kartı ve havale güvencesi.

Detaylı bilgi ve doğrudan alım için: @KeyvadiDestek
Hızlı Sipariş Botu: @KeyVadiSatisBot"""

t3 = """[ KEYVADİ | FİLM, DİZİ, MÜZİK VE EĞLENCE SERVİSLERİ ]

Popüler eğlence üyelikleri, oyun ve dijital lisanslar tek adreste:

Eğlence ve Streaming:
• YouTube Premium 3 Ay Kod: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | Prime Video: 29,90₺
• Disney+ UHD Reklamsız: 99,90₺ | HBO Max: 39,90₺
• Exxen (3 Ay): 34,99₺ | Crunchyroll Ortak: 39,90₺

Oyun, Yazılım ve AI:
• Minecraft + Xbox Ultimate (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam Oyun: 60₺
• Canva Pro 1 Yıl: 49,90₺ | ChatGPT Plus Ortak: 39,90₺
• Windows 10/11 Pro Key: 70₺ | Office 365 (1 Yıl): 70₺
• Trendyol Market 300 TL İndirim Kuponu: 49,99₺

Satış ve Güvence:
- +1000'den fazla başarılı satış referansımız bulunmaktadır.
- Donma veya kapanmaya karşı süre boyunca telafi garantilidir.
- Shopier altyapısında 3D Secure kart veya havale geçerlidir.

Canlı destek ve doğrudan sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

t4 = """[ KEYVADİ | ÖĞRENCİ VE ÇALIŞAN DİJİTAL İHTİYAÇLARI ]

Ders, sunum, proje ve iş akışınız için en çok aranan lisanslar:

Üretkenlik ve Yazılım:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Microsoft Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro: 70₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Montaj: 49,90₺ | Adobe CC 1 Ay: 119,99₺
• DeepL Pro: 29,90₺ | Perplexity Pro: 119,90₺

Medya, Eğlence ve Oyun:
• YouTube Premium 3 Ay: 19,90₺ | Netflix 4K Profil: 79,90₺
• Spotify Premium (4 Ay): 34,99₺ | Disney+ UHD: 99,90₺
• Trendyol Yemek ve Market Kuponları: 49,99₺
• Minecraft Premium ve Xbox Game Pass üyelikleri

Hizmet Şartları:
- Referanslarımız ve kanıtlı müşteri geçmişimiz mevcuttur.
- Satın aldığınız süre boyunca %100 telafi garantilidir.
- Shopier ile tüm banka/kredi kartlarıyla güvenli ödeme.

Sorularınız ve doğrudan alım için: @KeyvadiDestek
7/24 Sipariş Botu: @KeyVadiSatisBot"""

t5 = """[ KEYVADİ | OYUN, YAZILIM VE ALIŞVERİŞ KUPONLARI ]

Oyun üyelikleri, orijinal lisanslar ve indirimli alışveriş kuponları:

Oyun & İndirim Kuponları:
• Trendyol Market 800/300 İndirim Kuponu: 49,99₺
• Trendyol Yemek 700/250 İndirim Kuponu: 49,99₺
• Minecraft Premium + Game Pass Ultimate: 49,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam Oyun: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺

Popüler Lisanslar ve AI:
• Windows 10/11 Pro Lisans: 70₺ | Office 365 1 Yıl: 70₺
• Canva Pro 1 Yıl Kendi Mailinize: 49,90₺
• ChatGPT Plus Ortak: 39,90₺ | Gemini Pro 18 Ay: 99,90₺
• YouTube Premium 3 Ay Kod: 19,90₺ | Netflix 4K Profil: 79,90₺
• Spotify 4 Ay: 34,99₺ | CapCut Pro: 49,90₺

Neden KeyVadi?
- +1000 referansımız bulunmaktadır; sorunsuz teslimat.
- Tüm ürünlerde süre boyunca teknik destek ve telafi garantisi.
- Shopier 3D Secure güvencesiyle resmi kartla ödeme imkanı.

Doğrudan sipariş ve bilgi için: @KeyvadiDestek
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
• Windows 10/11 Pro: 70₺ | Office 365 1 Yıl: 70₺
• Xbox Game Pass 1 Ay: 49,90₺ | Minecraft Premium: 49,90₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Güvencelerimiz:
- +1000'den fazla başarılı işlem ve müşteri referansı.
- Kapanma durumunda süre boyunca anında telafi garantisi.
- Shopier 3D Secure ile kartla resmi ve güvenli alışveriş.

Referans kanıtları ve doğrudan sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

templates = [t1, t2, t3, t4, t5, t6]
for i, t in enumerate(templates, 1):
    diff = len(t) - 1196
    print(f"KeyVadi {i}: Karakter={len(t)} (Eskiye göre: {diff:+d}) | Satır={len(t.splitlines())}")
