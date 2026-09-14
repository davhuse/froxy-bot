import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FullCatalogAdTests(unittest.TestCase):
    def assert_catalog_covered(self, database, pattern):
        products = json.loads((ROOT / database).read_text(encoding="utf-8"))
        files = sorted((ROOT / "messages").glob(pattern))
        self.assertTrue(files, pattern)
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        missing = [item["title"] for item in products if item["title"] not in combined]
        self.assertEqual([], missing)
        self.assertTrue(all(900 <= len(path.read_text(encoding="utf-8")) < 4096 for path in files))
        for path in files:
            heading = path.read_text(encoding="utf-8").splitlines()[0].upper()
            self.assertNotIn("TAM KATALOG", heading)
            self.assertNotIn("TAM VİTRİN", heading)
            self.assertNotIn("TAM MODEL", heading)

    def test_keyvadi_turna_copy_has_requested_name_and_price(self):
        text = (ROOT / "messages" / "keyvadi_3.txt").read_text(encoding="utf-8")
        self.assertIn("Turna 600 TL Uçak Kuponu: 100₺", text)
        self.assertNotIn("Turna.com", text)

    def test_keyvadi_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp/products_db.json", "full_keyvadi_*.txt")

    def test_lisansarena_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp_lisansarena/products_db.json", "full_lisansarena_*.txt")

    def test_froxy_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp_froxy/products_db.json", "full_froxy_*.txt")


if __name__ == "__main__":
    unittest.main()
