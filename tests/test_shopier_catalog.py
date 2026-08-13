import unittest

from shopier_catalog import match_catalog_products, parse_shopier_catalog


class ShopierCatalogTests(unittest.TestCase):
    def test_parse_shopier_catalog_extracts_product_details(self):
        body = """
        <div class="product-card shopier--product-card">
          <a href="https://www.shopier.com/froxyai/47408136">
            <h3 class="shopier-store--store-product-card-title">Başlangıç Paketi</h3>
            <span data-price="199,90 TL"></span>
          </a>
        </div>
        """

        self.assertEqual(
            parse_shopier_catalog(body, "froxyai"),
            [
                {
                    "id": "47408136",
                    "title": "Başlangıç Paketi",
                    "price": "199,90 TL",
                    "url": "https://www.shopier.com/froxyai/47408136",
                }
            ],
        )

    def test_match_catalog_products_understands_turkish_and_aliases(self):
        products = [
            {"title": "Başlangıç Paketi 5K", "url": "https://example.com/start"},
            {"title": "Profesyonel Paket 50K", "url": "https://example.com/pro"},
            {"title": "ChatGPT Plus Kişisel", "url": "https://example.com/gpt"},
        ]

        self.assertEqual(
            match_catalog_products("başlangıç paketini almak istiyorum", products)[0]["url"],
            "https://example.com/start",
        )
        self.assertEqual(
            match_catalog_products("gpt kişisel fiyatı nedir", products)[0]["url"],
            "https://example.com/gpt",
        )

    def test_match_catalog_products_ignores_unrelated_support_message(self):
        products = [{"title": "ChatGPT Plus Kişisel", "url": "https://example.com/gpt"}]
        self.assertEqual(match_catalog_products("ödeme yaptım ama hesabım açılmadı", products), [])


if __name__ == "__main__":
    unittest.main()
