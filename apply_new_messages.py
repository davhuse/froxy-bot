# -*- coding: utf-8 -*-
import os

keyvadi_t1 = """[ KEYVADİ | GÜNCEL DİJİTAL ÜRÜN & LİSANS LİSTESİ ]

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
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam: 60₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Güven ve Garanti:
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Kapanma ve sorunlara karşı süre boyunca telafi garantilidir.
- Shopier ile 3D Secure kart veya havale ile güvenli ödeme.

Sorularınız ve doğrudan sipariş için: @KeyvadiDestek
7/24 Otomatik Sipariş Botu: @KeyVadiSatisBot"""

keyvadi_t2 = """[ KEYVADİ | YAPAY ZEKÂ, TASARIM VE İÇERİK ARAÇLARI ]

İş, okul, içerik üretimi ve tasarım için popüler yazılımlar:

Yapay Zekâ ve Tasarım:
• ChatGPT Plus Ortak: 39,90₺ | Kişisel Hesap: 499,90₺
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Gemini Pro 18 Ay Davet: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Ortak: 49,90₺ | Kişisel Hesap: 199,90₺
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
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Süre boyunca kapanmaya karşı %100 telafi ve değişim garantisi.
- Shopier altyapısıyla 3D Secure kart ve havale güvencesi.

Detaylı bilgi, referanslar ve doğrudan alım için: @KeyvadiDestek
Hızlı Sipariş Botu: @KeyVadiSatisBot"""

keyvadi_t3 = """[ KEYVADİ | FİLM, DİZİ, MÜZİK VE EĞLENCE SERVİSLERİ ]

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
- +100'den fazla başarılı işlem ve referansımız bulunmaktadır.
- Donma veya kapanmaya karşı süre boyunca anında telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale geçerlidir.

Canlı destek, referanslar ve sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

keyvadi_t4 = """[ KEYVADİ | ÖĞRENCİ VE ÇALIŞAN DİJİTAL İHTİYAÇLARI ]

Ders, sunum, proje ve iş akışınız için temel dijital lisanslar:

Üretkenlik ve Yazılım:
• Canva Pro 1 Yıl (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• Office 365 (1 Yıl): 70₺ | Windows 10/11 Pro Lisans: 70₺
• ChatGPT Plus Ortak: 39,90₺ | Kişisel: 499,90₺
• Gemini Pro 18 Ay: 99,90₺ | Gemini Advanced 3 Ay: 59,90₺
• CapCut Pro Ortak Hesap: 49,90₺ | Adobe CC 1 Ay: 119,99₺
• Perplexity Pro: 119,90₺ | DeepL Pro Çeviri: 29,90₺

Medya, Eğlence ve Oyun:
• YouTube Premium 3 Ay: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K UHD Profil: 79,90₺ | Ortak: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | Disney+ UHD: 99,90₺
• Minecraft + Game Pass (1 Ay): 49,90₺ | (3 Ay): 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | Steam: 60₺
• Trendyol Market ve Yemek Kuponları: 49,99₺

Satış ve Garanti Şartlarımız:
- +100'den fazla başarılı işlem ve referansımız mevcuttur.
- Satın aldığınız süre boyunca %100 değişim ve telafi garantisi.
- Shopier ile 3D Secure kredi kartı veya havale güvencesi.

Sorularınız ve doğrudan alım için: @KeyvadiDestek
7/24 Sipariş Botu: @KeyVadiSatisBot"""

keyvadi_t5 = """[ KEYVADİ | OYUN, LİSANS VE ALIŞVERİŞ FIRSATLARI ]

Oyun üyelikleri, orijinal lisanslar ve indirimli alışveriş kuponları:

Oyun & İndirim Kuponları:
• Trendyol Market 800/300 Kuponu: 49,99₺ | Yemek: 49,99₺
• Minecraft Premium + Game Pass Ultimate (1 Ay): 49,90₺ | 3 Ay: 119,90₺
• Xbox Game Pass 1 Ay: 49,90₺ | 3 Ay: 69,90₺ | Steam Oyun: 60₺
• Discord Nitro 14X Boost (1 Ay): 224,99₺ | VIP Key: 30₺
• FC 26: 299,99₺ | Kaspersky Premium 1 Yıl: 244,99₺

Popüler Lisanslar ve AI:
• Windows 10/11 Pro Orijinal Lisans: 70₺ | Office 365 1 Yıl: 70₺
• Canva Pro (Kendi Mailinize): 49,90₺ | Öğretmen: 79,90₺
• ChatGPT Plus Ortak: 39,90₺ | Gemini Pro 18 Ay: 99,90₺
• YouTube Premium 3 Ay: 19,90₺ | 1 Ay Davet: 30₺
• Netflix 4K Profil: 79,90₺ | Ortak Hesap: 39,99₺
• Spotify Premium (4 Ay): 34,99₺ | CapCut Pro: 49,90₺
• Adobe Creative Cloud 1 Ay: 119,99₺ | DeepL Pro: 29,90₺
• Prime Video: 29,90₺ | Disney+ UHD: 99,90₺

Neden KeyVadi?
- +100'den fazla başarılı işlem ve müşteri referansımız mevcuttur.
- Tüm ürünlerde süre boyunca teknik destek ve telafi garantisi.
- Shopier 3D Secure güvencesiyle resmi kartla ödeme imkanı.

Doğrudan sipariş, referanslar ve sorularınız için: @KeyvadiDestek
Hızlı Alışveriş Botu: @KeyVadiSatisBot"""

keyvadi_t6 = """[ KEYVADİ | UYGUN FİYATLI POPÜLER DİJİTAL LİSANSLAR ]

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
- +100'den fazla başarılı işlem ve müşteri referansı mevcuttur.
- Kapanma durumunda süre boyunca anında birebir telafi garantisi.
- Shopier 3D Secure ile kart veya havale ile güvenli alışveriş.

Referans kanıtları, soru ve doğrudan sipariş için: @KeyvadiDestek
Otomatik Mağaza Botu: @KeyVadiSatisBot"""

froxy_hook = """Yapay zekanın tüm gücünü cebinizde taşıyın! ⚡️

Kod yazmaktan görsel üretmeye, PDF analizinden makale yazımına kadar her şey Froxy AI panelinde. Neden tek bir yapay zekaya bağlı kalasınız ki?

🔥 GÜNCEL KAMPANYALI FİYATLAR:
• Gemini Pro (12 Ay Davet): 59.99 ₺
• Gemini Pro + Antigravity: 169.99 ₺'den başlayan fiyatlar
• ChatGPT Plus Ortak Hesap: 39.99 ₺
• Perplexity Pro Ortak (1 Ay): 69.99 ₺
• Gemini Ultra (2.5K Kredili): 399.99 ₺

Güven ve Garanti:
- +20'den fazla başarılı işlem ve müşteri referansı mevcuttur.
- Shopier 3D Secure ile güvenli ödeme (Gemini'de 1 ay telafi garantisi).

🔗 Panel & Sipariş: @FroxyDestekBOT
💬 Doğrudan Canlı Destek: @Froxy_Ai"""

froxy_compare = """Ayrı ayrı yapay zeka aboneliklerine servet ödemekten sıkılmadınız mı? 💡

ChatGPT, Gemini, Claude ve premium AI modellerini tek panelden yönetin! Froxy AI ile doğrulanmış modellere erişir, kredi sistemimizle kullandığınız kadar ödersiniz.

🚀 POPÜLER DİJİTAL LİSANSLARIMIZ:
🔹 ChatGPT Plus (Kişisel 499.90 ₺ | Ortak 39.99 ₺)
🔹 Gemini Pro 12 Ay (Davet) Sadece 59.99 ₺
🔹 Perplexity Pro (1 Aylık Ortak) 69.99 ₺
🔹 Codex SMS Onay 29.99 ₺
🔹 ChatGPT Go (3 Aylık) 49.99 ₺

Güven ve Garanti:
- +20'den fazla başarılı işlem ve referansımız mevcuttur.
- Resmi Shopier güvencesiyle kolayca sipariş verin.

📲 Sipariş & Panel: @FroxyDestekBOT | Canlı Destek: @Froxy_Ai"""

froxy_price = """FROXY DİJİTAL ÜRÜN MAĞAZASI AÇILDI 🛍️

En sevdiğiniz yapay zeka araçları artık tek ekranda ve en uygun fiyatlarla:

🏷️ LİSTE FİYATLARIMIZ:
➖ ChatGPT Plus (Kişisel): 499.90 ₺
➖ ChatGPT Plus (Ortak): 39.99 ₺
➖ Gemini Pro (12 Ay Davet): 59.99 ₺
➖ Gemini Pro (18 Ay Davet): 99.99 ₺
➖ Gemini Pro + Antigravity 12 Ay: 169.99 ₺
➖ Perplexity Pro Ortak (1 Ay): 69.99 ₺
➖ Codex SMS Doğrulama Kodu: 29.99 ₺

Güvencemiz:
- +20'den fazla başarılı işlem ve referansımız mevcuttur.
- Shopier 3D Secure ile güvenli ödeme ve hızlı teslimat.

👉 Güvenli Ödeme & Panel: @FroxyDestekBOT
💬 Canlı Destek ve Sipariş: @Froxy_Ai"""

froxy_question = """Yapay zeka araçları için aylık 20$ (yaklaşık 650 ₺) ödemek size de fazla gelmiyor mu? 🤔

Froxy AI ile bütçenizi yormadan en güçlü modellere (ChatGPT, Gemini, Codex) aynı anda erişebilirsiniz. 

🔥 ÖNE ÇIKAN FIRSATLAR:
✅ Gemini Pro 12 Ay Davet: Sadece 59.99 ₺
✅ ChatGPT Plus Ortak Hesap: 39.99 ₺
✅ Perplexity Pro (1 Aylık Ortak): 69.99 ₺
✅ Gemini Ultra (2.5K Kredili): 399.99 ₺

Güven ve Garanti:
- +20'den fazla başarılı işlem ve referansımız bulunmaktadır.
- Ödemeler Shopier üzerinden 3D Secure ile güvenle gerçekleşir.

🤖 Panel ve Sipariş: @FroxyDestekBOT
💬 Bilgi ve Canlı Destek: @Froxy_Ai"""

froxy_short = """🚀 FROXY AI YAYINDA!

Tüm premium yapay zeka modelleri (ChatGPT, Gemini, Claude, Codex) tek bir panelde birleşti!

🔹 Gemini Pro 12 Ay (Davet): 59.99 ₺
🔹 ChatGPT Plus Ortak: 39.99 ₺
🔹 Perplexity Pro Ortak: 69.99 ₺

+20'den fazla başarılı işlem ve referans güvencesi!
Shopier ile hızlı ve güvenli 3D Secure ödeme!

📲 Mini-app panelini aç: @FroxyDestekBOT
💬 Canlı Destek: @Froxy_Ai"""

froxy_social = """🌟 DİJİTAL İŞ AKIŞINIZI HIZLANDIRIN! 🌟

Kod yazdırma, görsel üretimi, detaylı veri analizi ve fazlası... Hepsi Froxy AI'nin akıllı panelinde! Farklı yerlere ayrı ayrı üye olmanıza gerek yok.

🔥 FİYATLARI DİBE ÇEKTİK:
💥 Gemini Pro 12 Ay: 59.99 ₺
💥 ChatGPT Plus Ortak: 39.99 ₺
💥 Perplexity Pro Ortak: 69.99 ₺
💥 Gemini Pro + Antigravity: 169.99 ₺
💥 Codex SMS Onay: 29.99 ₺

Güvence:
- +20'den fazla başarılı işlem ve referansımız mevcuttur.
- Günün her saati çalışan Shopier 3D Secure altyapımız hizmetinizde.

👉 Tıkla ve Keşfet: @FroxyDestekBOT
💬 Canlı Destek: @Froxy_Ai"""

# Write KeyVadi files
kv_templates = [keyvadi_t1, keyvadi_t2, keyvadi_t3, keyvadi_t4, keyvadi_t5, keyvadi_t6]
for i, content in enumerate(kv_templates, 1):
    path = f"messages/keyvadi_{i}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# Write Froxy files
froxy_templates = {
    "froxy_hook.txt": froxy_hook,
    "froxy_compare.txt": froxy_compare,
    "froxy_price.txt": froxy_price,
    "froxy_question.txt": froxy_question,
    "froxy_short.txt": froxy_short,
    "froxy_social.txt": froxy_social,
}
for name, content in froxy_templates.items():
    path = os.path.join("messages", name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("All templates written successfully.")
