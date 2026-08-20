# Satış Artırma Uygulama Raporu — 20 Ağustos 2026

## Ölçüm düzeltmesi

- Telegram reklam hesabı, destek botu ve web tıklaması marka başına `keyvadi`, `froxy`, `lisansarena` altında birleşir.
- `dm_received` ham mesaj sayısı yanında benzersiz konuşma ve nitelikli satış konuşması ayrı ölçülür.
- Mesaj sınıfları: `sales_lead`, `after_sales`, `delivery_problem`, `payment_question`, `human_support`.
- Sipariş numarası/Webhook ID tekilleştirilir; Shopier API mutabakatı üç marka için çalışır.
- Net sonuç; gelir, gerçekleşen tedarik maliyeti ve iadeler sonrası hesaplanır. Tek ürün reklamlarında net kâr / 1.000 görünür reklam raporlanır.

## Dönüşüm akışı

- Ürün sorgusu tek ürün kartına; belirsiz sorgu en fazla üç seçeneğe gider.
- Teslimat sorunu, ödeme sorusu ve satış sonrası mesaj yeni ürün kartı üretmez; insan kuyruğuna aktarılır.
- LisansArena mağazası sağlıklı değilse reklam CTA trafiği kapalı kalır; hesap ve checkpoint korunur.
- Ürün kartlarında yalnız doğrulanmış teslim türü, uygunluk ve garanti bilgisi kullanılabilir.

## Stoksuz tedarik

- Sekiz İtemSatış fırsatı `supplier_opportunities.json` içinde maliyet, hedef fiyat, teslim türü, garanti, risk ve son kontrol tarihiyle kayıtlıdır.
- Otomatik satın alma yoktur. Her talep `awaiting_price_stock_check` durumunda manuel admin kuyruğuna girer.
- Canlı stok ve maliyet doğrulanmadan satın alma onayı verilemez.
- Maliyet son doğrulamaya göre %10'dan fazla artarsa onay engellenir.
- Tek işlem 300 TL döner sermaye sınırını aşamaz.
- A öncelikli ürünlerde gerçek teslimat/kod denemesi tamamlanmadan tek ürün reklamları açılmaz.

## Reklam testi

- Duolingo 29,90 TL, CapCut ortak 49,90 TL ve Netflix profil 99,90 TL / YouTube kod 19,90 TL için üç kısa ürün reklamı hazırdır.
- Şablonlar `SALES_HERO_ADS_ENABLED=0` güvenlik bayrağı arkasındadır.
- Tedarik QA tamamlandığında kontrollü olarak açılır; mevcut uzun katalog rotasyonu korunur.
- Kazanan ürün en az 20 nitelikli DM sonrası, iade düşülmüş net kâr / 1.000 görünür reklam ile seçilir.

## Yeni grup adayları

- `@kuponfirsati`: katılım onayı ve kural okumasından sonra linksiz smoke adayı.
- `@kuponceksatis`: yüksek hacimli; en az 20 gerçek referans ve grubun satış konusu şartları tamamlanmadan hedef değil.
- `@toptan_wholesale_tr`: dijital ürün reklam izni doğrulanırsa ikincil aday.
- Hiçbiri otomatik katılım veya blast listesine eklenmez.

## 14 günlük sıra

1. Gün 1–2: sipariş mutabakatı, LisansArena DB ve DM sınıflandırma doğrulaması.
2. Gün 2–4: dört A ürününde canlı fiyat/stok ve birer gerçek teslimat denemesi.
3. Gün 4–7: geçen ürünlerde kontrollü tek ürün reklamları; grup başına tek varyasyon.
4. Gün 8–14: nitelikli DM, satın alma, teslimat sorunu, iade ve net kâr takibi.
5. En az 20 nitelikli DM oluşmayan test dağılımı değiştirilmeden 21 güne uzatılır.
