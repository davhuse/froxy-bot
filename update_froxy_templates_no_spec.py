import glob
import sys

sys.stdout.reconfigure(encoding='utf-8')

master_froxy_text = """Birden fazla yapay zeka aracına para vermek yerine, hepsini tek panelden denemek ister misiniz?

Froxy AI'da güncel GPT, Claude Sonnet 5, Gemini 3.5 Flash, DeepSeek V4 ve 1.100+ model aynı kredi sistemiyle çalışır.

Neler yapabilirsiniz?
✓ Kod yazdırma, hata analizi ve proje desteği
✓ Makale, özet, çeviri ve araştırma
✓ PDF, görsel ve dosya analizi
✓ Reklam/sosyal medya metni ve görsel üretimi
✓ Hazır AI ajanlarıyla daha hızlı iş akışları

🛒 GÜNCEL ÜRÜN VE FİYAT LİSTESİ:
• Gemini Pro (12 Ay Davet: 59.99₺ | 18 Ay Davet: 99.99₺)*
• Gemini Pro + Antigravity (12 Ay: 169.99₺ | 18 Ay: 249.99₺)*
• ChatGPT Plus (Kişisel: 479.99₺ | Ortak: 39.99₺ | + Codex: 199.99₺)**
• Codex SMS Doğrulama Kodu: 29.99₺
• Gemini Ultra (1 Ay Kredisiz: 299.99₺ | 2.5K Kredili: 399.99₺)*
• ChatGPT Go (3 Aylık İndirim Kodu): 49.99₺
• Perplexity Pro (1 Aylık Ortak Hesap): 69.99₺

*(Not: Tüm Gemini ürünlerinde maksimum 1 ay garanti mevcuttur.)
**(Not: ChatGPT ürünlerinde garanti bulunmamaktadır.)

⚡ 7/24 Anında Otomatik Teslimat
Önce 100 ücretsiz krediyle dene: @FroxyDestekBOT"""

froxy_files = sorted(glob.glob("messages/froxy_*.txt"))

for fpath in froxy_files:
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(master_froxy_text)
    print(f"✅ Updated Froxy Template: {fpath}")

print("SUCCESS: Updated all Froxy message templates (Perplexity Special Profile removed)!")
