import unittest

from miniapp_lisansarena import blueprint


class LisansArenaLegacyMiniAppTests(unittest.TestCase):
    def test_all_catalog_prices_are_positive_numeric_values(self):
        products = blueprint.load_products()
        self.assertEqual(len(products), 55)
        self.assertTrue(all(product.get("price_num", 0) > 0 for product in products))

    def test_turkish_display_price_is_parsed_without_becoming_free(self):
        self.assertEqual(
            blueprint.product_price_number({"price": "2.414,99 TL"}),
            2414.99,
        )
        netflix = next(
            product for product in blueprint.load_products()
            if product["id"] == "la_netflix_ortak"
        )
        self.assertEqual(netflix["price_num"], 59.90)


if __name__ == "__main__":
    unittest.main()
