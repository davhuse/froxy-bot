# Satış artırma planı — KeyVadi, Froxy, LisansArena

## Mevcut durum

Kodda satış hunisi ölçümü mevcut: DM, ürün eşleşmesi, CTA, tıklama, sipariş, iade ve insan desteğine aktarım olayları anonim anahtarlarla tutuluyor. Son yerel kayıtlarda sipariş olayı görünmediği için ilk hedef trafik değil, ölçülebilir şekilde “DM → doğru ürün → Shopier tıklaması → sipariş” zincirini tamamlamak.

## 1. Hafta: güven ve dönüşüm temeli

1. Her ürün kartında tek ürün adı, doğru fiyat, doğru kapak ve tek bir doğrudan Shopier/Mini App bağlantısı gösterilecek.
2. Ürün adı olmayan ilk DM’de anında kısa karşılama + mağaza butonu + canlı destek butonu gönderilecek; destek bildirimi yanıtı bloke etmeyecek.
3. Shopier webhook ve sipariş eşleştirmesi günlük kontrol edilecek. `purchase_cta_sent`, `purchase_click`, `shopier_order` ve `shopier_refund` olayları aynı ürün kimliğiyle eşleşmeli.
4. Reklam havuzunda yalnızca 30 veya daha fazla güvenli ve gönderilebilir grup varken blast çalışacak. Yeni gruplar kademeli eklenmeye devam edecek.

## 2. Hafta: teklif ve mesaj testi

- En çok aranan ürünlerde üç teklif denenecek: tek ürün, iki ürün paketi, süre uzatmalı paket.
- Reklam metninde aynı anda en fazla bir ana vaat kullanılacak: “anında teslim”, “en düşük fiyat” veya “garantili destek”.
- KeyVadi, Froxy ve LisansArena için CTA metni ayrı ölçülecek; marka karşılaştırması yerine ürün bazında `match_to_click_pct` ve `click_to_order_pct` izlenecek.
- Her varyant en az 100 nitelikli DM veya 30 Shopier tıklaması görmeden kazanan ilan edilmeyecek.

## 3. Hafta: tekrar satın alma ve yönlendirme

- Teslimat sonrası destek mesajı: kullanım/aktivasyon yardımı ve mağazaya dönüş bağlantısı.
- Mini App referral bağlantıları ürün ve marka bazında görünür tutulacak; referral sayısı tek başına değil, siparişe dönüşümüyle değerlendirilecek.
- Bakiye/AI kredi ürünlerinde küçük giriş paketi, orta paket ve avantajlı yüksek paket birlikte gösterilecek; kullanıcıya ilk satın almayı kolaylaştıran paket varsayılan seçilecek.

## Günlük sağlık panosu

Her marka için şu beş metrik raporlanacak:

- DM → ürün eşleşmesi
- Ürün eşleşmesi → CTA tıklaması
- CTA tıklaması → sipariş
- Sipariş geliri − tedarik maliyeti − iadeler
- 1.000 görünür reklam başına net kâr

Bir metrik iki gün üst üste düşerse önce ilgili ürün linki/stok/fiyat kontrol edilir; sonra mesaj metni değiştirilir. Aynı anda hem fiyatı hem görseli hem de mesajı değiştirmekten kaçınılır.

## Güvenlik sınırları

Sahte model, sahte stok, doğrulanmamış fiyat veya anahtarsız AI sağlayıcı satışa açılmayacak. API anahtarları yalnız Render ortamında tutulacak. Reklam blast’i, LisansArena havuzu 30 güvenli hedefe ulaşmadan açılmayacak.
