import unittest
from pathlib import Path
from unittest.mock import patch

from sales_conversion import apply_cta_experiment


ROOT = Path(__file__).resolve().parents[1]


class AdTemplateTests(unittest.TestCase):
    def test_froxy_templates_have_one_bot_handle_and_no_sender_tag(self):
        for path in sorted((ROOT / "messages").glob("froxy_*.txt")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("@FroxyDestekBOT"), 1, path.name)
            self.assertNotIn("@FroxyOnline", text, path.name)
            self.assertNotIn("#Froxy", text, path.name)
            self.assertIn("shopier", text.lower(), path.name)
            self.assertNotIn("froxyai.com", text.lower(), path.name)
            self.assertNotIn("1.100", text, path.name)
            self.assertNotIn("1100", text, path.name)
            self.assertNotIn("ücretsiz kredi", text.lower(), path.name)

    def test_froxy_support_public_flow_is_shopier_only(self):
        source = (ROOT / "froxy_destek_bot.py").read_text(encoding="utf-8")
        self.assertIn('FROXY_SHOPIER_URL = "https://www.shopier.com/froxyai"', source)
        self.assertIn('"text": "🛒 Shopier Mağazası"', source)
        self.assertNotIn("froxyai.com", source.lower())
        self.assertNotIn("1.100", source)
        self.assertNotIn("1100+", source)

    def test_froxy_cta_compatibility_helper_keeps_only_visible_handle(self):
        message = "Froxy AI paneli\nBilgi: @FroxyDestekBOT"
        with patch("sales_conversion.cta_experiment_status", return_value={"phase": "initial_3_days"}), patch(
            "sales_conversion.cta_experiment_arm", return_value="test"
        ):
            updated, arm = apply_cta_experiment(message, "froxy", "example-group")
        self.assertEqual(arm, "plain_mention")
        self.assertEqual(updated.count("@FroxyDestekBOT"), 1)
        self.assertNotIn("https://", updated)
        self.assertNotIn("?start=", updated)

    def test_lisansarena_templates_have_distinct_store_identity(self):
        paths = sorted((ROOT / "messages").glob("lisansarena_*.txt"))
        self.assertEqual([path.name for path in paths], [
            "lisansarena_1.txt", "lisansarena_2.txt", "lisansarena_3.txt"
        ])
        required_keywords = (
            "59.90", "84.90", "19.90", "39.90", "69.90",
            "179.90", "89.90", "49.90", "99.90", "149.90", "29.90"
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("@LisansArenaBot"), 1, path.name)
            self.assertNotIn("KeyVadi", text, path.name)
            for kw in required_keywords:
                self.assertIn(kw, text, (path.name, kw))

    def test_keyvadi_templates_are_long_distinct_catalog_variants(self):
        paths = sorted((ROOT / "messages").glob("keyvadi_[1-6].txt"))
        self.assertEqual(len(paths), 6)
        bodies = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertGreater(len(text), 1100, path.name)
            self.assertEqual(text.count("@KeyVadiSatisBot"), 1, path.name)
            self.assertIn("Netflix", text, path.name)
            self.assertIn("79,90", text, path.name)
            self.assertIn("ChatGPT", text, path.name)
            self.assertIn("Canva", text, path.name)
            bodies.append(text)
        self.assertEqual(len(set(bodies)), 6)


if __name__ == "__main__":
    unittest.main()
