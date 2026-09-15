import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from announcement_delivery import (
    AnnouncementQueue,
    build_announcement_item,
    drain_queue,
    parse_stock_command,
    stock_card_text,
)
from shopier_campaigns import (
    PriceWriteUnavailable,
    ShopierPriceWriter,
    discounted_price,
    run_campaign_cycle,
)


class AnnouncementTests(unittest.TestCase):
    def test_parse_stock_command_examples(self):
        self.assertEqual(parse_stock_command("/stok ChatGPT Plus 0"), ("ChatGPT Plus", 0, None))
        self.assertEqual(parse_stock_command("/stok Netflix 3 99"), ("Netflix", 3, "99"))
        self.assertEqual(
            parse_stock_command("/stok Turna 600 TL Uçak Kuponu 1 100"),
            ("Turna 600 TL Uçak Kuponu", 1, "100"),
        )
        self.assertIsNone(parse_stock_command("/stok Netflix"))
        self.assertIsNone(parse_stock_command("/stok Netflix -1"))

    def test_stock_cards_distinguish_empty_and_remaining(self):
        self.assertIn("Stok Tükendi", stock_card_text("Yemeksepeti", 0, "50"))
        self.assertIn("Kalan stok: **3 adet**", stock_card_text("Netflix", 3, "99"))

    def test_stock_idempotency_key_ignores_display_price(self):
        first = build_announcement_item(
            "keyvadi", {"id": "p1", "title": "Ürün"},
            text="fiyat 99", kind="stock", marker="3", recipients=[],
        )
        second = build_announcement_item(
            "keyvadi", {"id": "p1", "title": "Ürün"},
            text="fiyat 89", kind="stock", marker="3", recipients=[],
        )
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])

    def test_queue_is_idempotent_and_resumable(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "announcement_delivery.firestore_helper.get_document", return_value={}
        ), patch("announcement_delivery.firestore_helper.set_document", return_value=True):
            queue = AnnouncementQueue("keyvadi", "stock")
            queue.path = Path(folder) / "queue.json"
            item = build_announcement_item(
                "keyvadi",
                {"id": "p1", "title": "Ürün", "url": "https://www.shopier.com/1"},
                text="test",
                kind="stock",
                marker="3:99",
                recipients=[101, 102],
            )
            first, created = queue.enqueue(item)
            second, duplicate = queue.enqueue(item)
            self.assertTrue(created)
            self.assertFalse(duplicate)
            self.assertEqual(first["id"], second["id"])

            sent = []

            async def send_one(uid, _item):
                sent.append(uid)
                return True

            result = asyncio.run(drain_queue(queue, send_one))
            self.assertEqual(sent, [101, 102])
            self.assertEqual(result["success"], 2)
            self.assertEqual(queue.pending(), [])

    def test_discount_is_bounded_and_price_writes_fail_closed(self):
        self.assertEqual(discounted_price("100 TL", 10), "90.00")
        self.assertEqual(discounted_price("1.000,00 TL", 5), "950.00")
        with patch.dict("os.environ", {"SHOPIER_PRICE_WRITES_ENABLED": "0"}, clear=False):
            with self.assertRaises(PriceWriteUnavailable):
                ShopierPriceWriter().update("keyvadi", "p1", "90.00")

    def test_discount_cycle_skips_empty_stock(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "shopier_campaigns.STATE_PATH", Path(folder) / "campaigns.json"
        ), patch("shopier_campaigns.firestore_helper.get_document", return_value={}), patch(
            "shopier_campaigns.firestore_helper.set_document", return_value=True
        ), patch.dict("os.environ", {"SHOPIER_PRICE_WRITES_ENABLED": "1"}, clear=False):
            class Writer:
                def __init__(self):
                    self.calls = []

                def update(self, brand, product_id, new_price):
                    self.calls.append((brand, product_id, new_price))

            writer = Writer()
            result = run_campaign_cycle(
                lambda brand: [
                    {"id": "empty", "title": "Empty", "price": "100", "stockQuantity": 0},
                    {"id": "live", "title": "Live", "price": "100", "stockQuantity": 2},
                ],
                price_writer=writer,
                now=1_700_000_000,
            )
            self.assertEqual(result["updated"], 3)
            self.assertTrue(all(product_id == "live" for _, product_id, _ in writer.calls))


if __name__ == "__main__":
    unittest.main()
