# Satış akışı için sonraki geliştirmeler

1. **Katalogdan otomatik yayın ve tutarlılık kontrolü:** Fiyat, başlık, garanti, kapak ve reklam metinleri tek katalogdan doğrulansın. KeyVadi'de `47669105` ve `47669159` ürünlerinin yerel katalog ile Shopier bağlantı önbelleğindeki fiyatı farklı; canlı fiyat görülmeden reklama alınmasın.
2. **Stok ve teslimat durumu:** Ürün kartında gerçek stok, manuel teslimat zamanı ve varsa aktivasyon koşulları görünsün.
3. **Ürün bazlı dönüşüm:** Reklam gönderimi, bot açılışı, ürün detayı, satın alma tıklaması ve Shopier siparişi aynı ürün kimliğiyle ölçülsün.
4. **Reklam karşılaştırması:** Her ürün grubu için iki metin varyantı dönüşümlü yayımlansın; tıklama ve sipariş oranına göre karar verilsin.
5. **Gerçek değerlendirmeler:** Yalnız doğrulanmış müşteri yorumları, izin alınarak ilgili ürün kartında gösterilsin.
6. **Mobil satın alma adımı:** Ürün detayından tek belirgin satın alma çağrısı ile doğrudan doğru Shopier ilanına gidilsin.

## Ölçüm notu

Yerel `sales_metrics.jsonl` dosyasında bu çalışma öncesi KeyVadi için 1 gelen mesaj, 1 ürün eşleşmesi ve 2 satın alma çağrısı var; Shopier siparişi kaydı yok. Bu örnek satış etkisi çıkarmak için yeterli değil. Yeni rotasyonlar canlıya alındığında aynı olaylar ve gerçek Shopier siparişleri en az yedi gün boyunca toplanıp önceki dönemle karşılaştırılmalı. Jarvis için yerel satış hunisi kaydı bulunmadığından ilk dönem başlangıç ölçümü olacaktır.
