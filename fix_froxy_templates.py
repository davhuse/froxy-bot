import glob
import os

master_text = """Birden fazla yapay zeka aracına para vermek yerine, hepsini tek panelden denemek ister misiniz?

Froxy AI, yalnızca o anda çalışan ve doğrulanmış modelleri gösterir. Model sayısı sağlayıcıların sağlık durumuna göre güncellenir.

Neler yapabilirsiniz?
✅ Kod yazdırma, hata analizi ve proje desteği
✅ Makale, özet, çeviri ve araştırma
✅ PDF, görsel ve dosya analizi
✅ Reklam/sosyal medya metni ve görsel üretimi
✅ Hazır AI ajanlarıyla daha hızlı iş akışları

📌 GÜNCEL ÜRÜN VE FİYAT LİSTESİ:
🔹 Gemini Pro (12 Ay Davet: 59.99₺ | 18 Ay Davet: 99.99₺)*
🔹 Gemini Pro + Antigravity (12 Ay: 169.99₺ | 18 Ay: 249.99₺)*
🔹 ChatGPT Plus (Kişisel: 499.90₺ | Ortak: 39.99₺ | + Codex: 599.90₺)**
🔹 Codex SMS Doğrulama Kodu: 29.99₺
🔹 Gemini Ultra (1 Ay Kredisiz: 299.99₺ | 2.5K Kredili: 399.99₺)*
🔹 ChatGPT Go (3 Aylık İndirim Kodu): 49.99₺
🔹 Perplexity Pro (Ortak: 69.99₺ | Özel Profil: 79.99₺)

*(Not: Tüm Gemini ürünlerinde maksimum 1 ay garanti mevcuttur.)
**(Not: ChatGPT ürünlerinde garanti bulunmamaktadır.)

💳 Ödeme onayından sonra AI kredileri hesabınıza yüklenir.
Stok yoksa ürünler 1–3 iş günü içinde manuel teslim edilir.
Uygulamayı aç: @FroxyDestekBOT"""

files = glob.glob("messages/froxy_*.txt")
for f in files:
    with open(f, "w", encoding="utf-8") as file:
        file.write(master_text)
    print(f"Updated {f}")
