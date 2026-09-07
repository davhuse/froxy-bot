import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from marketing_cards import (
    get_product_brand_icon,
    format_price_str,
    build_price_drop_card,
    build_selling_fast_card,
)


class MarketingCardsTests(unittest.TestCase):
    def test_brand_icon_mapping(self):
        self.assertEqual(get_product_brand_icon("Gemini AI Pro 1 Yıl"), "💠")
        self.assertEqual(get_product_brand_icon("CapCut Pro 1 Aylık"), "✂️")
        self.assertEqual(get_product_brand_icon("Netflix 4K UHD"), "🎬")
        self.assertEqual(get_product_brand_icon("Xbox Game Pass Ultimate"), "🎮")
        self.assertEqual(get_product_brand_icon("Windows 11 Pro Retail"), "💻")
        self.assertEqual(get_product_brand_icon("Diğer Dijital Ürün"), "⚡")

    def test_price_formatting(self):
        self.assertEqual(format_price_str("99"), "99 TL")
        self.assertEqual(format_price_str("49.90 TL"), "49.90 TL")
        self.assertEqual(format_price_str("$1.79"), "$1.79")

    def test_price_drop_card_formatting(self):
        text, buttons = build_price_drop_card(
            title="Gemini AI Pro",
            new_price="99",
            old_price="149",
            buy_url="https://www.shopier.com/49362708",
            bulk_price="89",
        )
        self.assertIn("🔥 **Price Drop! (Flaş Fiyat Düştü)**", text)
        self.assertIn("💠 **Gemini AI Pro**", text)
        self.assertIn("💵 **Şimdi: 99 TL** · ~~149 TL~~", text)
        self.assertIn("(%34 İndirim)", text)
        self.assertIn("💰 **Çok Al & Daha Çok Kazan:**", text)
        self.assertIn("• 2+ Adet: 89 TL/adet", text)
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0][0].url, "https://www.shopier.com/49362708")

    def test_selling_fast_card_formatting(self):
        text, buttons = build_selling_fast_card(
            title="CapCut Pro 1M",
            price="49.90",
            remaining_count=2,
            buy_url="https://www.shopier.com/50460458",
        )
        self.assertIn("🔥 **Selling Fast — Son 2 Stok Kaldı!**", text)
        self.assertIn("✂️ **CapCut Pro 1M**", text)
        self.assertIn("💵 **Fiyat: 49.90 TL**", text)
        self.assertIn("Stokta Son **2** Adet!", text)
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0][0].url, "https://www.shopier.com/50460458")

    def test_parse_fiyatdusur_args(self):
        from marketing_cards import parse_fiyatdusur_args
        self.assertEqual(
            parse_fiyatdusur_args("gemini ai pro 99 149"),
            ("gemini ai pro", "99", "149", None),
        )
        self.assertEqual(
            parse_fiyatdusur_args("capcut pro 49 79 39"),
            ("capcut pro", "49", "79", "39"),
        )
        self.assertIsNone(parse_fiyatdusur_args("gemini"))
        self.assertIsNone(parse_fiyatdusur_args("gemini 99"))

    def test_parse_sonstok_args(self):
        from marketing_cards import parse_sonstok_args
        self.assertEqual(
            parse_sonstok_args("capcut pro 2"),
            ("capcut pro", 2, None),
        )
        self.assertEqual(
            parse_sonstok_args("xbox game pass 1 129"),
            ("xbox game pass", 1, "129"),
        )
        self.assertIsNone(parse_sonstok_args("capcut"))


if __name__ == "__main__":
    unittest.main()
