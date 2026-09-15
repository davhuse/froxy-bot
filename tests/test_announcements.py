import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from announcement_delivery import (
    AnnouncementQueue,
    build_announcement_item,
    drain_queue,
    parse_stock_command,
    record_stock_changes,
    stock_card_text,
)
from shopier_campaigns import (
    DynamicListingUnavailable,
    PriceWriteUnavailable,
    ShopierPriceWriter,
    cleanup_dynamic_sale_listings,
    create_dynamic_sale_listing,
    discounted_price,
    run_dynamic_campaign_cycle,
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

    def test_stock_transition_queues_threshold_once(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "announcement_delivery.ROOT", Path(folder)
        ), patch("announcement_delivery.firestore_helper.get_document", return_value={}), patch(
            "announcement_delivery.firestore_helper.set_document", return_value=True
        ):
            product = {
                "id": "p1",
                "name": "Ürün",
                "price": "100 TL",
                "link": "https://www.shopier.com/1",
                "stockStatus": "inStock",
                "stockQuantity": 4,
            }
            first = record_stock_changes("keyvadi", [product])
            self.assertEqual(first["queued"], 0)
            product["stockQuantity"] = 3
            second = record_stock_changes("keyvadi", [product])
            self.assertEqual(second["queued"], 1)
            third = record_stock_changes("keyvadi", [product])
            self.assertEqual(third["queued"], 0)

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

    def test_shopier_writer_uses_documented_product_put_payload(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"id": "p1", "priceData": {"price": "90.00"}}).encode()

        with patch.dict(
            "os.environ",
            {
                "SHOPIER_PRICE_WRITES_ENABLED": "1",
                "SHOPIER_KEYVADI_ACCESS_TOKEN": "pat",
            },
            clear=False,
        ), patch("shopier_campaigns.urllib.request.urlopen", return_value=Response()) as opener:
            result = ShopierPriceWriter().update("keyvadi", "p1", "90.00")
            request = opener.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.shopier.com/v1/products/p1")
            self.assertEqual(request.method, "PUT")
            self.assertEqual(json.loads(request.data), {"priceData": {"price": "90.00"}})
            self.assertTrue(result["ok"])

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

    def test_dynamic_listing_is_fail_closed_when_disabled(self):
        with patch.dict("os.environ", {"SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED": "0"}, clear=False):
            with self.assertRaises(DynamicListingUnavailable):
                create_dynamic_sale_listing(
                    "keyvadi", {"id": "p1", "title": "Ürün", "price": "100 TL"},
                    idempotency_key="cta-1",
                )

    def test_dynamic_listing_creates_exact_title_price_and_is_idempotent(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"id": "dynamic-1", "url": "https://www.shopier.com/dynamic-1"}).encode()

        with tempfile.TemporaryDirectory() as folder, patch(
            "shopier_campaigns.DYNAMIC_STATE_PATH", Path(folder) / "dynamic.json"
        ), patch("shopier_campaigns.firestore_helper.get_document", return_value={}), patch(
            "shopier_campaigns.firestore_helper.set_document", return_value=True
        ), patch.dict(
            "os.environ",
            {
                "SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED": "1",
                "SHOPIER_KEYVADI_ACCESS_TOKEN": "pat",
            },
            clear=False,
        ), patch("shopier_campaigns.urllib.request.urlopen", return_value=Response()) as opener:
            product = {"id": "source-1", "title": "ChatGPT Plus", "price": "100 TL"}
            first = create_dynamic_sale_listing("keyvadi", product, price="90 TL", idempotency_key="cta-1", now=10)
            second = create_dynamic_sale_listing("keyvadi", product, price="90 TL", idempotency_key="cta-1", now=11)
            self.assertEqual(first["shopier_product_id"], "dynamic-1")
            self.assertEqual(first["amount"], "90.00")
            self.assertTrue(second["duplicate"])
            request = opener.call_args.args[0]
            self.assertEqual(request.method, "POST")
            payload = json.loads(request.data)
            self.assertEqual(payload["title"], "ChatGPT Plus")
            self.assertEqual(payload["priceData"]["price"], 90.0)

    def test_dynamic_campaign_and_expired_listing_cleanup(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "shopier_campaigns.STATE_PATH", Path(folder) / "campaigns.json"
        ), patch("shopier_campaigns.DYNAMIC_STATE_PATH", Path(folder) / "dynamic.json"), patch(
            "shopier_campaigns.firestore_helper.get_document", return_value={}
        ), patch("shopier_campaigns.firestore_helper.set_document", return_value=True), patch.dict(
            "os.environ",
            {
                "SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED": "1",
                "SHOPIER_KEYVADI_ACCESS_TOKEN": "pat",
            },
            clear=False,
        ), patch("shopier_campaigns.random.choice", side_effect=lambda values: values[0]), patch(
            "shopier_campaigns.random.randint", return_value=10
        ):
            now = __import__("time").time()
            result = run_dynamic_campaign_cycle(
                lambda brand: [{"id": "live", "title": "Live", "price": "100 TL", "stockQuantity": 2}],
                now=now,
            )
            self.assertEqual(result["updated"], 3)
            self.assertEqual(
                __import__("shopier_campaigns").campaign_price_for_product(
                    "keyvadi", {"id": "live", "price": "100 TL"}
                ),
                "90.00",
            )

            module = __import__("shopier_campaigns")
            module.DYNAMIC_STATE_PATH.write_text(json.dumps({
                "listings": {
                    "cta-expired": {
                        "brand": "keyvadi",
                        "shopier_product_id": "dynamic-1",
                        "status": "pending",
                        "expires_at": 1,
                    }
                }
            }), encoding="utf-8")
            with patch("shopier_campaigns._dynamic_delete") as delete:
                cleanup = cleanup_dynamic_sale_listings(now=2)
            self.assertEqual(cleanup["closed"], 1)
            delete.assert_called_once_with("keyvadi", "dynamic-1")


if __name__ == "__main__":
    unittest.main()
