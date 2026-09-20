"""Canonical campaign definitions shared by Shopier sync, bots and Mini Apps.

The campaign list deliberately lives in one small module so a price/title change
cannot silently drift between the two storefronts or an automatic message.
"""

from __future__ import annotations


RAW_MEDIA_BASE = "https://raw.githubusercontent.com/davhuse/froxy-bot/main/miniapp/assets/"


CAMPAIGNS = {
    "yemeksepeti_360": {
        "title": "Yemeksepeti İlk Sipariş 360₺'ye 270₺ İndirim Kodu",
        "prices": {"keyvadi": 45.0, "lisansarena": 55.0},
        "category": "coupons",
        "image": "products/campaign_yemeksepeti_360.png",
        "description": (
            "🍔 Yemeksepeti ilk siparişe özel 360 TL ve üzeri sepette 270 TL indirim kodu.\n\n"
            "• Yalnızca Yemeksepeti'nde daha önce sipariş vermemiş kullanıcılar içindir.\n"
            "• İlk siparişinizde, 360 TL ve üzeri sepet tutarında 270 TL indirim sağlar.\n"
            "• Ödeme adımındaki kupon alanına girilir; tek kullanımlıktır.\n"
            "• Kod satın alım sonrası otomatik teslim edilir. Kampanya koşulları ve stoklarla sınırlıdır."
        ),
    },
    "yemeksepeti_450": {
        "title": "Yemeksepeti İlk Sipariş 450₺'ye 350₺ İndirim Kodu",
        "prices": {"keyvadi": 50.0, "lisansarena": 60.0},
        "category": "coupons",
        "image": "products/campaign_yemeksepeti_450.png",
        "description": (
            "🍔 Yemeksepeti ilk siparişe özel 450 TL ve üzeri sepette 350 TL indirim kodu.\n\n"
            "• Yalnızca Yemeksepeti'nde daha önce sipariş vermemiş kullanıcılar içindir.\n"
            "• İlk siparişinizde, 450 TL ve üzeri sepet tutarında 350 TL indirim sağlar.\n"
            "• Ödeme adımındaki kupon alanına girilir; tek kullanımlıktır.\n"
            "• Kod satın alım sonrası otomatik teslim edilir. Kampanya koşulları ve stoklarla sınırlıdır."
        ),
    },
    "positive_110": {
        "title": "Positive 2.000 TL Alışverişe 110 TL Puan",
        "prices": {"keyvadi": 30.0, "lisansarena": 35.0},
        "category": "coupons",
        "image": "products/campaign_positive_110.png",
        "description": (
            "⛽ Positive kampanyası: 2.000 TL ve üzeri akaryakıt ve/veya otogaz alışverişinizde "
            "110 TL değerinde Positive Puan kazanın. Kampanyadan 2 kez yararlanarak toplam "
            "220 TL puan kazanabilirsiniz.\n\n"
            "Kampanya uygulama ve kullanıcı uygunluk koşullarına tabidir. Kod, satın alım sonrası "
            "otomatik teslim edilir; Positive uygulamasındaki kampanya alanından tanımlanır."
        ),
    },
    "gastroclub_200": {
        "title": "GastroClub 200 TL Hediye + %20 Puan",
        "prices": {"keyvadi": 20.0, "lisansarena": 25.0},
        "category": "coupons",
        "image": "products/campaign_gastroclub_200.png",
        "description": (
            "🍽️ Hepsiburada Premium'a özel GastroClub üyeliğiyle 1.500'den fazla restoran ve kafede "
            "ilk Gastro harcamanıza 200 TL'ye kadar puan, sonraki harcamalarınızda iki ay boyunca "
            "%20 puan kazanın.\n\n"
            "Nasıl kullanılır? GastroClub uygulamasını https://gastroclub.com.tr/apps/gastroclub "
            "adresinden indirin, Üye Olmak İstiyorum ile hesap açın ve Hepsiburada Premium'dan "
            "aldığınız aktivasyon kodunu girin. Üyelik tamamlanınca cüzdan > Kart Ekle adımından "
            "kartınızı ekleyip anlaşmalı restoranda QR ile ödeme yapın.\n\n"
            "Kampanya koşulları: Üyelik tarihinden itibaren 60 gün ücretsiz üyelik ve ilk üyelikten "
            "itibaren 2 ay hizmet bedeli alınmaz. İlk harcama 200 TL altındaysa harcanan tutar, "
            "200 TL ve üzerindeyse 200 TL puan yüklenir. %20 geri kazanım işlem başına 1.000 TL'ye "
            "kadar ve en fazla 200 TL'dir. Haklar devredilemez, nakde çevrilemez ve başka tekliflerle "
            "birleştirilemez; kullanıcı yalnızca 1 aktivasyon kodu kullanabilir. Kampanya Premium üyelerine "
            "özeldir; GastroClub ve Hepsiburada koşulları değiştirme/sonlandırma hakkını saklı tutar."
        ),
    },
    "enterprise_40": {
        "title": "Enterprise %40 Araç Kiralama İndirimi",
        "prices": {"keyvadi": 30.0, "lisansarena": 35.0},
        "category": "coupons",
        "image": "products/campaign_enterprise_40.png",
        "description": (
            "🚗 Enterprise'dan araç kiralamalarında liste fiyatı üzerinden %40 indirim. Kampanya "
            "31.12.2026 tarihine kadar online kiralamalarda ve tüm ofislerde geçerlidir.\n\n"
            "1-30 Eylül örnek kampanyaları: Hyundai Bayon Benzinli Otomatik 2.290 TL ve Volvo XC60 "
            "6.990 TL. Adana, Ankara, Antalya, Aydın, Balıkesir, Çanakkale, Denizli, İstanbul, İzmir, "
            "Kayseri, Kırıkkale, Kocaeli, Konya, Manisa, Mersin, Muğla, Ordu, Rize, Sakarya, Samsun ve "
            "Trabzon ofislerinde geçerlidir; Antalya Belek ve Muğla Fethiye hariçtir.\n\n"
            "Her kullanımda yeni şifre gerekir. Diğer kampanyalarla birleşmez, tek seferde en fazla 15 gün "
            "kiralanabilir. İndirim yalnız araç kiralamada geçerlidir; ek hizmetleri kapsamaz. Enterprise "
            "filo/stokları ve genel kiralama koşulları geçerlidir; uygunluk yoksa muadil grup sunulabilir. "
            "Enterprise koşulları önceden bildirmeden değiştirebilir."
        ),
    },
    "garenta_40": {
        "title": "Garenta %40 Araç Kiralama İndirimi",
        "prices": {"keyvadi": 20.0, "lisansarena": 30.0},
        "category": "coupons",
        "image": "products/campaign_garenta_40.png",
        "description": (
            "🚗 Trendyol Plus üyelerine özel Garenta araç kiralamalarında %40 indirim. Kampanya kodunu "
            "Trendyol Plus > Garenta avantaj sayfasından kopyalayıp Garenta'da Kampanya Kodu alanına "
            "girin; lokasyon/tarih seçip araçta Şimdi Öde ile tamamlayın. Satış ofisi ve 444 5 478 "
            "çağrı merkezi üzerinden de kullanılabilir.\n\n"
            "Kampanya 12.06.2026-31.12.2026 arasında tüm Garenta satış kanallarında, filo ve stoklarla "
            "sınırlı geçerlidir. Günlük limit 500 km, aylık limit 4.000 km'dir. Kod tek kullanımlık, "
            "tek kiralama içindir; başka indirimlerle birleşmez. Teminat, kiralayanın kendi adına kredi "
            "kartından alınır; ehliyette T.C. kimlik numarası bulunmalıdır. Kod Ofiste Öde fiyatına uygulanır. "
            "İptal/iade kodu geçersiz kılar. KDV, 7/24 yol yardım, zorunlu trafik sigortası, bakım ve ikame "
            "araç dahildir; Garenta genel kiralama koşulları geçerlidir."
        ),
    },
    "enuygun_plus_10": {
        "title": "ENUYGUN Trendyol Plus %10 İndirim",
        "prices": {"keyvadi": 20.0, "lisansarena": 30.0},
        "category": "coupons",
        "image": "products/campaign_enuygun_plus_10.png",
        "description": (
            "✈️ Trendyol Plus üyelerine ENUYGUN.com uçak, otobüs, otel ve araç kiralamalarında %10 indirim. "
            "Trendyol Plus > ENUYGUN avantaj sayfasındaki kodu kopyalayın; ENUYGUN hesabınıza giriş yapıp "
            "ödeme sayfasındaki İndirim Kodunu Kullan alanına girin.\n\n"
            "Kampanya 17.07.2026-31.12.2026 tarihleri arasında ENUYGUN web ve mobilde geçerlidir. Kodlar "
            "15.01.2027'ye kadar kullanılmalı, seyahat/konaklama 17.07.2026-31.03.2027 arasında olmalıdır. "
            "Maksimum indirim otobüs/otel/araçta 1.500 TL, uçakta 500 TL'dir. Daha önce ENUYGUN'dan satın "
            "almamış kullanıcılar yararlanabilir. Kod tek kullanımlık, bölünemez, nakde çevrilemez; iptal/iade "
            "kodunu geçersiz kılar. Metro Turizm, Avis, Budget ve Rent Go hariçtir. Stok ve firma koşulları "
            "geçerlidir; destek: 0850 333 88 88."
        ),
    },
    "trendyol_market_800": {
        "title": "Trendyol Market 800/300 İndirim Kodu",
        "prices": {"keyvadi": 50.0, "lisansarena": 60.0},
        "category": "coupons",
        "image": "products/campaign_trendyol_market_800.png",
        "description": "🛒 Trendyol Go/Market'te 800 TL ve üzeri siparişe 300 TL indirim kodu. Kod tek kullanımlıktır ve stoklarla sınırlıdır.",
    },
    "trendyol_yemek_750": {
        "title": "Trendyol Yemek 750/250 İndirim Kodu",
        "prices": {"keyvadi": 50.0, "lisansarena": 60.0},
        "category": "coupons",
        "image": "products/campaign_trendyol_yemek_750.png",
        "description": "🍔 Trendyol Yemek'te 750 TL ve üzeri siparişe 250 TL indirim kodu. Kod tek kullanımlıktır ve kampanya stoklarla sınırlıdır.",
    },
    "duolingo_super_12_personal": {
        "title": "Duolingo Super 12 Ay - Kendi Hesabına Aktivasyon",
        "prices": {"keyvadi": 199.90, "lisansarena": 249.90},
        "category": "ai",
        "image": "products/campaign_duolingo_12_personal.png",
        "badge": "🦉 12 AY KİŞİSEL",
        "description": (
            "🦉 Duolingo Super 12 aylık kişisel plan aktivasyonu. Üyelik kendi Duolingo hesabınıza "
            "tanımlanır; ortak hesap değildir.\n\n"
            "• Satın alım sonrası Duolingo hesabınızın e-posta adresini destek ekibine iletmeniz gerekir.\n"
            "• Aktivasyon tamamlandığında Super özellikleri 12 ay boyunca hesabınızda kullanılır.\n"
            "• Hesap bilgileriniz paylaşılmaz; yalnızca aktivasyon için gerekli e-posta adresi kullanılır.\n"
            "• Ürün kişiye özeldir, devredilemez ve ödeme sonrası aktivasyon süreci başlatılır."
        ),
    },
    "adobe_express_12_personal": {
        "title": "Adobe Express 12 Ay - Kendi Hesabına Aktivasyon",
        "prices": {"keyvadi": 499.90, "lisansarena": 599.90},
        "category": "design",
        "image": "products/campaign_adobe_express_12.png",
        "badge": "🎨 12 AY TASARIM",
        "description": (
            "🎨 Adobe Express 12 aylık kişisel plan aktivasyonu. Üyelik kendi Adobe hesabınıza "
            "tanımlanır; ortak hesap değildir.\n\n"
            "• Satın alım sonrası Adobe hesabınızın e-posta adresini destek ekibine iletmeniz gerekir.\n"
            "• Aktivasyon tamamlandığında Adobe Express premium tasarım araçları 12 ay boyunca hesabınızda kullanılır.\n"
            "• Hesap bilgileriniz paylaşılmaz; yalnızca aktivasyon için gerekli e-posta adresi kullanılır.\n"
            "• Ürün kişiye özeldir, devredilemez ve ödeme sonrası aktivasyon süreci başlatılır."
        ),
    },
}


def api_media_url(campaign_key: str) -> str:
    campaign = CAMPAIGNS[campaign_key]
    return RAW_MEDIA_BASE + campaign["image"]


def price_text(value: float, comma: bool = False) -> str:
    formatted = f"{float(value):.2f}"
    if comma:
        formatted = formatted.replace(".", ",")
    return f"{formatted} TL"
