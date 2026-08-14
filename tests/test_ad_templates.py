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

    def test_froxy_test_cta_replaces_instead_of_duplicating_handle(self):
        message = "Froxy AI paneli\nBilgi: @FroxyDestekBOT"
        with patch("sales_conversion.cta_experiment_status", return_value={"phase": "initial_3_days"}), patch(
            "sales_conversion.cta_experiment_arm", return_value="test"
        ):
            updated, arm = apply_cta_experiment(message, "froxy", "example-group")
        self.assertEqual(arm, "test")
        self.assertEqual(updated.count("@FroxyDestekBOT"), 1)
        self.assertIn("100 ücretsiz krediyle dene", updated)

    def test_lisansarena_templates_have_distinct_store_identity(self):
        for path in sorted((ROOT / "messages").glob("lisansarena_*.txt")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("@LisansArenaBot"), 1, path.name)
            self.assertNotIn("KeyVadi", text, path.name)
            self.assertIn("mini app", text.casefold(), path.name)


if __name__ == "__main__":
    unittest.main()
