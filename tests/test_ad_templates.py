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
        required_prices = (
            "499,90 TL", "69,90 TL", "59,90 TL", "99,99 TL", "599,99 TL",
            "119,90 TL", "149,99 TL", "83,99 TL", "224,99 TL", "94,49 TL",
            "47,24 TL", "36,74 TL", "36,99 TL", "39,90 TL", "29,90 TL",
            "89,90 TL", "63 TL", "70 TL", "244,99 TL", "49,99 TL", "14,99 TL",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("@LisansArenaBot"), 1, path.name)
            self.assertNotIn("KeyVadi", text, path.name)
            for price in required_prices:
                self.assertIn(price, text, (path.name, price))


if __name__ == "__main__":
    unittest.main()
