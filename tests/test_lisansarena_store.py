import base64
from datetime import timedelta
import hashlib
import hmac
import json
import tempfile
import time
import unittest
from pathlib import Path

from sqlalchemy import func, insert, select, update

import lisansarena_store as store_module


class LisansArenaStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "store.sqlite"
        self.key = base64.urlsafe_b64encode(b"K" * 32).decode().rstrip("=")
        self.store = store_module.LisansArenaStore(
            f"sqlite:///{self.db_path.as_posix()}", encryption_key=self.key
        )
        self.user_id = self.store.get_or_create_user({"id": 42, "first_name": "Test"})

    def tearDown(self):
        self.store.engine.dispose()
        self.temp.cleanup()

    def add_product(self, delivery="automatic", price=10000, cost=5000):
        now = store_module.utcnow()
        with self.store.engine.begin() as conn:
            return conn.execute(insert(store_module.products).values(
                name=f"Test {delivery}", description="Onaylı açıklama", category="Test",
                price_cents=price, cost_cents=cost, delivery_type=delivery,
                published=True, guide="Kullanım", created_at=now, updated_at=now,
            ).returning(store_module.products.c.id)).scalar_one()

    def credit(self, amount=50000, reference="seed"):
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.wallet_ledger).values(
                user_id=self.user_id, amount_cents=amount, entry_type="test_credit",
                reference_type="test", reference_id=reference, created_at=store_module.utcnow(),
            ))

    def test_legacy_34_products_are_imported_as_unpublished_drafts(self):
        with self.store.engine.connect() as conn:
            count = conn.execute(select(func.count()).select_from(store_module.products).where(store_module.products.c.legacy_shopier_id.is_not(None))).scalar_one()
            published = conn.execute(select(func.count()).select_from(store_module.products).where(store_module.products.c.published.is_(True))).scalar_one()
        self.assertEqual(count, 34)
        self.assertEqual(published, 0)

    def test_automatic_stock_is_delivered_only_once(self):
        product_id = self.add_product()
        nonce, encrypted = self.store.encrypt_stock(product_id, "LICENSE-ONE")
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.inventory).values(product_id=product_id, nonce=nonce, ciphertext=encrypted, sold_order_id=None, created_at=store_module.utcnow()))
        self.credit()
        result = self.store.purchase(self.user_id, product_id, 1)
        self.assertEqual(result["delivery"], ["LICENSE-ONE"])
        with self.assertRaisesRegex(ValueError, "Stok tükendi"):
            self.store.purchase(self.user_id, product_id, 1)

    def test_manual_order_refunds_wallet_after_deadline(self):
        product_id = self.add_product("manual")
        self.credit(10000)
        result = self.store.purchase(self.user_id, product_id, 1)
        with self.store.engine.begin() as conn:
            conn.execute(update(store_module.orders).where(store_module.orders.c.id == result["order_id"]).values(deadline_at=store_module.utcnow() - timedelta(seconds=1)))
        self.assertEqual(self.store.expire_manual_orders(), 1)
        with self.store.engine.connect() as conn:
            self.assertEqual(self.store.balance(conn, self.user_id), 10000)

    def test_webhook_requires_code_amount_product_and_quantity_and_is_idempotent(self):
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.topup_intents).values(
                code="LA-A1B2C3", user_id=self.user_id, amount_cents=10000,
                shopier_product_id="balance-100", status="pending",
                expires_at=store_module.utcnow() + timedelta(hours=1), created_at=store_module.utcnow(),
            ))
        payload = {
            "id": "order-1", "paymentStatus": "paid", "total": "100.00",
            "note": "LA-A1B2C3", "lineItems": [{"productId": "balance-100", "quantity": 1}],
        }
        self.store.ingest_webhook(payload, "webhook-1")
        self.store.ingest_webhook(payload, "webhook-1")
        self.assertEqual(self.store.process_webhooks(), 1)
        with self.store.engine.connect() as conn:
            self.assertEqual(self.store.balance(conn, self.user_id), 10000)
            self.assertEqual(conn.execute(select(func.count()).select_from(store_module.wallet_ledger).where(store_module.wallet_ledger.c.entry_type == "topup")).scalar_one(), 1)

    def test_margin_floor(self):
        self.assertTrue(store_module.margin_is_allowed(10000, 6000, "automatic", "0.05"))
        self.assertFalse(store_module.margin_is_allowed(10000, 7100, "automatic", "0.05"))
        self.assertFalse(store_module.margin_is_allowed(10000, 6500, "manual", "0.05"))

    def test_tampered_telegram_auth_is_rejected(self):
        token = "123:bot-secret"
        user = json.dumps({"id": 42, "first_name": "Test"}, separators=(",", ":"))
        fields = {"auth_date": str(int(time.time())), "query_id": "q", "user": user}
        check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        encoded = "&".join(f"{key}={__import__('urllib.parse').parse.quote(value)}" for key, value in fields.items())
        self.assertEqual(store_module.verify_telegram_init_data(encoded, token)["id"], 42)
        self.assertIsNone(store_module.verify_telegram_init_data(encoded.replace("Test", "Evil"), token))


if __name__ == "__main__":
    unittest.main()
