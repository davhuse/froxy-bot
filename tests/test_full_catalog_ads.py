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

    def test_keyvadi_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp/products_db.json", "full_keyvadi_*.txt")

    def test_lisansarena_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp_lisansarena/products_db.json", "full_lisansarena_*.txt")

    def test_froxy_catalog_is_present_across_long_rotation(self):
        self.assert_catalog_covered("miniapp_froxy/products_db.json", "full_froxy_*.txt")


if __name__ == "__main__":
    unittest.main()
