import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs("messages", exist_ok=True)

# 1. froxy_compare.txt: Focus on having all models in one place
TEXT_COMPARE = """Ayrı ayrı yapay zeka aboneliklerine servet ödemekten sıkılmadınız mı? 💡

ChatGPT, Gemini, Claude ve daha birçok premium AI modelini tek bir panelden yönetin! Froxy AI ile sadece çalışan ve doğrulanmış modellere erişirsiniz. Kredi sistemimiz sayesinde sadece kullandığınız kadar ödersiniz.

🚀 POPÜLER DİJİTAL LİSANSLARIMIZ:
🔹 ChatGPT Plus (Kişisel 499.90 ₺ | Ortak 39.99 ₺)
🔹 Gemini Pro 12 Ay (Davet) Sadece 59.99 ₺
🔹 Perplexity Pro (1 Aylık Ortak) 69.99 ₺
🔹 Codex SMS Onay 29.99 ₺
🔹 ChatGPT Go (3 Aylık) 49.99 ₺

Resmi Shopier güvencesiyle kolayca sipariş verin.

📲 Hemen Başla: @FroxyDestekBOT"""

# 2. froxy_hook.txt: Catchy intro, cost savings
TEXT_HOOK = """Yapay zekanın tüm gücünü cebinizde taşıyın! ⚡️

Kod yazmaktan görsel üretmeye, PDF analizinden makale yazımına kadar her şey Froxy AI panelinde. Neden tek bir yapay zekaya bağlı kalasınız ki?

🔥 GÜNCEL KAMPANYALI FİYATLAR:
• Gemini Pro (12 Ay Davet): 59.99 ₺
• Gemini Pro + Antigravity: 169.99 ₺'den başlayan fiyatlar
• ChatGPT Plus Ortak Hesap: 39.99 ₺
• Perplexity Pro Ortak (1 Ay): 69.99 ₺
• Gemini Ultra (2.5K Kredili): 399.99 ₺

Shopier 3D Secure ile güvenli ödeme (Gemini ürünlerinde 1 ay garanti mevcuttur).

🔗 Panel Uygulaması ve Sipariş: @FroxyDestekBOT"""

# 3. froxy_price.txt: Focus on the price list
TEXT_PRICE = """FROXY DİJİTAL ÜRÜN MAĞAZASI AÇILDI 🛍️

En sevdiğiniz yapay zeka araçları artık tek ekranda ve en uygun fiyatlarla:

🏷️ LİSTE FİYATLARIMIZ:
➖ ChatGPT Plus (Kişisel): 499.90 ₺
➖ ChatGPT Plus (Ortak): 39.99 ₺
➖ Gemini Pro (12 Ay Davet): 59.99 ₺
➖ Gemini Pro (18 Ay Davet): 99.99 ₺
➖ Gemini Pro + Antigravity 12 Ay: 169.99 ₺
➖ Perplexity Pro Ortak (1 Ay): 69.99 ₺
➖ Codex SMS Doğrulama Kodu: 29.99 ₺

Shopier 3D Secure ile güvenli ödeme. Teslimatlar stok durumuna göre gerçekleşir.

👉 Güvenli Ödeme ve Panel İçin: @FroxyDestekBOT"""

# 4. froxy_question.txt: Question based
TEXT_QUESTION = """Yapay zeka araçları için aylık 20$ (yaklaşık 650 ₺) ödemek size de fazla gelmiyor mu? 🤔

Froxy AI ile bütçenizi yormadan en güçlü modellere (ChatGPT, Gemini, Codex) aynı anda erişebilirsiniz. 

🔥 ÖNE ÇIKAN FIRSATLAR:
✅ Gemini Pro 12 Ay Davet: Sadece 59.99 ₺
✅ ChatGPT Plus Ortak Hesap: 39.99 ₺
✅ Perplexity Pro (1 Aylık Ortak): 69.99 ₺
✅ Gemini Ultra (2.5K Kredili): 399.99 ₺

Panel üzerinden bakiye alabilir veya lisans satın alabilirsiniz. Ödemeler Shopier üzerinden güvenle gerçekleşir.

🤖 Bilgi, Destek ve Satın Alım: @FroxyDestekBOT"""

# 5. froxy_short.txt: Short and punchy
TEXT_SHORT = """🚀 FROXY AI YAYINDA!

Tüm premium yapay zeka modelleri (ChatGPT, Gemini, Claude, Codex) tek bir panelde birleşti!

🔹 Gemini Pro 12 Ay (Davet): 59.99 ₺
🔹 ChatGPT Plus Ortak: 39.99 ₺
🔹 Perplexity Pro Ortak: 69.99 ₺

Shopier ile hızlı ve güvenli ödeme! 
📲 Mini-app panelini açmak için: @FroxyDestekBOT"""

# 6. froxy_social.txt: Emojis and hype
TEXT_SOCIAL = """🌟 DİJİTAL İŞ AKIŞINIZI HIZLANDIRIN! 🌟

Kod yazdırma, görsel üretimi, detaylı veri analizi ve fazlası... Hepsi Froxy AI'nin akıllı panelinde! Farklı yerlere ayrı ayrı üye olmanıza gerek yok.

🔥 FİYATLARI DİBE ÇEKTİK:
💥 Gemini Pro 12 Ay: 59.99 ₺
💥 ChatGPT Plus Ortak: 39.99 ₺
💥 Perplexity Pro Ortak: 69.99 ₺
💥 Gemini Pro + Antigravity: 169.99 ₺
💥 Codex SMS Onay: 29.99 ₺

Günün her saati çalışan Shopier altyapımız hizmetinizde.

👉 Tıkla ve Keşfet: @FroxyDestekBOT"""

variations = {
    "messages/froxy_compare.txt": TEXT_COMPARE,
    "messages/froxy_hook.txt": TEXT_HOOK,
    "messages/froxy_price.txt": TEXT_PRICE,
    "messages/froxy_question.txt": TEXT_QUESTION,
    "messages/froxy_short.txt": TEXT_SHORT,
    "messages/froxy_social.txt": TEXT_SOCIAL
}

for path, content in variations.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {path}")

print("All variations regenerated!")
