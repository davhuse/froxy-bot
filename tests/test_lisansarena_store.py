import base64
from datetime import timedelta
import hashlib
import hmac
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_full_50_product_catalog_is_sellable_in_the_mini_app(self):
        with self.store.engine.connect() as conn:
            count = conn.execute(select(func.count()).select_from(store_module.products)).scalar_one()
            published = conn.execute(select(func.count()).select_from(store_module.products).where(store_module.products.c.published.is_(True))).scalar_one()
        self.assertEqual(count, 50)
        self.assertEqual(published, 50)

    def test_storefront_has_a_real_cart_action_and_generated_cover_for_every_product(self):
        catalog = self.store.storefront_catalog()
        self.assertEqual(len(catalog), 50)
        self.assertTrue(all(item["available"] is True for item in catalog))
        self.assertTrue(all(item["category"] != "Taslak aktarım" for item in catalog))
        self.assertTrue(all(item["image_url"].startswith("/static/la-cover-") for item in catalog))
        self.assertTrue(all(item["image_url"].endswith(".webp") for item in catalog))
        self.assertTrue(all(item["request_enabled"] is False for item in catalog))
        self.assertTrue(all(item["action"] == "buy" for item in catalog))
        root = Path(__file__).resolve().parents[1]
        self.assertTrue(all(
            (root / item["image_url"].lstrip("/")).is_file()
            for item in catalog
        ))
        self.assertGreater(sum(1 for item in catalog if item["featured"]), 0)

    def test_approved_advert_products_and_prices_match_the_storefront(self):
        by_name = {
            item["name"]: item["price_cents"]
            for item in self.store.storefront_catalog()
        }
        expected = {
            "ChatGPT Plus 30 Gün - Kişisel": 49990,
            "ChatGPT Plus 30 Gün - Ortak": 6990,
            "Gemini Pro 3 Aylık": 5990,
            "Gemini Ultra (2.5k Kredili Hesap)": 59999,
            "Gamma Pro (1 Aylık Hesap)": 29999,
            "Canva Pro (1 Yıllık Yetki)": 8399,
            "Discord Nitro 14X Boost - 1 Aylık": 22499,
            "Xbox Game Pass Ultimate 3 Aylık": 8990,
            "Windows 10/11 Pro Lisans Anahtarı (Key)": 7000,
            "Microsoft Office 365 (1 Yıllık Hesap)": 7000,
            "Kaspersky Premium 1 Yıl - 1 Cihaz": 24499,
            "Shell 75 TL Akaryakıt Puanı": 1499,
        }
        for name, price_cents in expected.items():
            with self.subTest(product=name):
                self.assertEqual(by_name.get(name), price_cents)

    def test_seed_migration_does_not_overwrite_later_admin_decisions(self):
        with self.store.engine.begin() as conn:
            product_id = conn.execute(select(store_module.products.c.id).limit(1)).scalar_one()
            conn.execute(update(store_module.products).where(
                store_module.products.c.id == product_id
            ).values(published=False))
            conn.execute(update(store_module.product_display).where(
                store_module.product_display.c.product_id == product_id
            ).values(featured=False, display_order=777))
        self.store.import_legacy_drafts()
        self.store.backfill_product_display()
        with self.store.engine.connect() as conn:
            product = conn.execute(select(store_module.products.c.published).where(
                store_module.products.c.id == product_id
            )).scalar_one()
            display = conn.execute(select(
                store_module.product_display.c.featured,
                store_module.product_display.c.display_order,
            ).where(
                store_module.product_display.c.product_id == product_id
            )).one()
        self.assertFalse(product)
        self.assertFalse(display.featured)
        self.assertEqual(display.display_order, 777)

    def test_legacy_turkish_text_is_repaired_for_storefront(self):
        self.assertEqual(store_module.clean_storefront_text("Canva Pro Ã–ÄŸretmen"), "Canva Pro Öğretmen")

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

    def test_cart_checkout_rolls_back_everything_when_one_item_has_no_stock(self):
        stocked_id = self.add_product(price=10000)
        empty_id = self.add_product(price=12000)
        nonce, encrypted = self.store.encrypt_stock(stocked_id, "ROLLBACK-LICENSE")
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.inventory).values(
                product_id=stocked_id, nonce=nonce, ciphertext=encrypted,
                sold_order_id=None, created_at=store_module.utcnow(),
            ))
        self.credit(50000, "cart-rollback")
        with self.assertRaisesRegex(ValueError, "Stok tükendi"):
            self.store.checkout(self.user_id, [
                {"product_id": stocked_id, "quantity": 1},
                {"product_id": empty_id, "quantity": 1},
            ])
        with self.store.engine.connect() as conn:
            self.assertEqual(self.store.balance(conn, self.user_id), 50000)
            self.assertEqual(conn.execute(select(func.count()).select_from(
                store_module.orders
            )).scalar_one(), 0)
            self.assertIsNone(conn.execute(select(
                store_module.inventory.c.sold_order_id
            ).where(store_module.inventory.c.product_id == stocked_id)).scalar_one())

    def test_ticket_referral_and_draw_features_are_persistent(self):
        requested_product = self.store.storefront_catalog()[0]
        ticket = self.store.create_ticket(
            self.user_id, "request", "Bu ürün ne zaman gelir?",
            product_id=requested_product["id"],
        )
        self.assertEqual(self.store.list_tickets(self.user_id)[0]["id"], ticket["id"])
        self.store.update_ticket(ticket["id"], status="resolved", admin_reply="Stok gelince haber verilecek")
        self.assertEqual(self.store.list_tickets(self.user_id)[0]["status"], "resolved")

        referred_id = self.store.get_or_create_user({"id": 84, "first_name": "Arkadaş"})
        code = self.store.referral_profile(self.user_id)["code"]
        self.assertTrue(self.store.apply_referral_code(referred_id, code))
        self.assertFalse(self.store.apply_referral_code(referred_id, code))
        self.assertEqual(self.store.referral_profile(self.user_id)["count"], 1)

        with self.store.engine.begin() as conn:
            draw_id = conn.execute(insert(store_module.draws).values(
                title="Test çekilişi", description="", status="active",
                ends_at=store_module.utcnow() + timedelta(hours=1),
                created_at=store_module.utcnow(),
            ).returning(store_module.draws.c.id)).scalar_one()
        self.assertFalse(self.store.enter_draw(self.user_id, draw_id)["already_entered"])
        self.assertTrue(self.store.enter_draw(self.user_id, draw_id)["already_entered"])
        self.assertTrue(self.store.active_draws(self.user_id)[0]["entered"])

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

    def test_missing_topup_note_stays_manual_review_and_manual_credit_is_idempotent(self):
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.topup_intents).values(
                code="LA-B2C3D4", user_id=self.user_id, amount_cents=50000,
                shopier_product_id="balance-500", status="pending",
                expires_at=store_module.utcnow() + timedelta(hours=1), created_at=store_module.utcnow(),
            ))
        self.store.ingest_webhook({
            "id": "order-missing-note", "paymentStatus": "paid", "total": "500.00",
            "note": "", "lineItems": [{"productId": "balance-500", "quantity": 1}],
        }, "webhook-missing-note")
        self.assertEqual(self.store.process_webhooks(), 1)
        snapshot = self.store.inspect_topup_code("LA-B2C3D4")
        self.assertEqual(snapshot["manual_review_candidates"][0]["status"], "manual_review")
        self.assertFalse(snapshot["manual_review_candidates"][0]["code_in_note"])
        self.assertEqual(snapshot["balance_cents"], 0)

        first = self.store.apply_manual_credit_once(
            self.user_id, 5000, "LA-B2C3D4:manual-50tl", "test correction", 1
        )
        second = self.store.apply_manual_credit_once(
            self.user_id, 5000, "LA-B2C3D4:manual-50tl", "test correction", 1
        )
        self.assertTrue(first["applied"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(self.store.inspect_topup_code("LA-B2C3D4")["balance_cents"], 5000)

    def test_one_lira_release_topup_uses_temporary_product(self):
        result = self.store.create_topup(self.user_id, 100)
        self.assertEqual(result["amount"], "1,00 TL")
        self.assertTrue(result["shopier_url"].endswith("/49853325"))

    def test_custom_topup_creates_a_coverless_one_use_listing(self):
        with patch.object(self.store, "_shopier_api", return_value={"id": "custom-750"}) as api:
            result = self.store.create_topup(self.user_id, 75000, "custom")
        self.assertEqual(result["mode"], "custom")
        self.assertFalse(result["note_required"])
        self.assertTrue(result["shopier_url"].endswith("/custom-750"))
        payload = api.call_args.args[2]
        self.assertEqual(payload["media"], [])
        self.assertEqual(payload["stockQuantity"], 1)
        self.assertTrue(payload["customListing"])
        self.assertIn("Test", payload["title"])
        self.assertIn(result["code"], payload["description"])
        with self.store.engine.connect() as conn:
            intent = conn.execute(select(store_module.topup_intents).where(
                store_module.topup_intents.c.code == result["code"]
            )).mappings().one()
        self.assertEqual(intent["topup_mode"], "custom")
        self.assertEqual(intent["listing_state"], "open")
        self.assertEqual(intent["shopier_product_id"], "custom-750")

    def test_custom_topup_matches_product_without_note_and_rejects_wrong_note(self):
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.topup_intents).values(
                code="LA-C0FFEE", user_id=self.user_id, amount_cents=123400,
                shopier_product_id="custom-1234", status="pending", topup_mode="custom",
                listing_state="open", expires_at=store_module.utcnow() + timedelta(hours=1),
                created_at=store_module.utcnow(),
            ))
        with patch.object(self.store, "_close_shopier_listing"):
            self.store.ingest_webhook({
                "id": "custom-paid", "paymentStatus": "paid", "total": "1234.00",
                "note": "", "lineItems": [{"productId": "custom-1234", "quantity": 1}],
            }, "custom-webhook")
            self.assertEqual(self.store.process_webhooks(), 1)
        with self.store.engine.connect() as conn:
            self.assertEqual(self.store.balance(conn, self.user_id), 123400)
            intent = conn.execute(select(store_module.topup_intents).where(
                store_module.topup_intents.c.code == "LA-C0FFEE"
            )).mappings().one()
        self.assertEqual(intent["status"], "completed")
        self.assertEqual(intent["listing_state"], "closed")

        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.topup_intents).values(
                code="LA-ABC123", user_id=self.user_id, amount_cents=123400,
                shopier_product_id="custom-other", status="pending", topup_mode="custom",
                listing_state="open", expires_at=store_module.utcnow() + timedelta(hours=1),
                created_at=store_module.utcnow(),
            ))
        self.store.ingest_webhook({
            "id": "custom-wrong-note", "paymentStatus": "paid", "total": "1234.00",
            "note": "LA-ABC123", "lineItems": [{"productId": "custom-1234", "quantity": 1}],
        }, "custom-wrong-note")
        self.assertEqual(self.store.process_webhooks(), 1)
        with self.store.engine.connect() as conn:
            self.assertEqual(self.store.balance(conn, self.user_id), 123400)

    def test_custom_topup_range_and_expiry_close_listing(self):
        with self.assertRaises(ValueError):
            self.store.create_topup(self.user_id, 999, "custom")
        with self.assertRaises(ValueError):
            self.store.create_topup(self.user_id, 5_000_100, "custom")
        with self.store.engine.begin() as conn:
            conn.execute(insert(store_module.topup_intents).values(
                code="LA-DEAD01", user_id=self.user_id, amount_cents=1000,
                shopier_product_id="custom-expired", status="pending", topup_mode="custom",
                listing_state="open", expires_at=store_module.utcnow() - timedelta(seconds=1),
                created_at=store_module.utcnow(),
            ))
        with patch.object(self.store, "_close_shopier_listing") as close:
            self.assertEqual(self.store.close_due_custom_topups(), 1)
        close.assert_called_once_with("custom-expired")
        with self.store.engine.connect() as conn:
            intent = conn.execute(select(store_module.topup_intents).where(
                store_module.topup_intents.c.code == "LA-DEAD01"
            )).mappings().one()
        self.assertEqual(intent["status"], "expired")
        self.assertEqual(intent["listing_state"], "closed")

    def test_api_reconciliation_filters_unpaid_and_is_idempotent(self):
        paid = {
            "id": "order-api-1", "paymentStatus": "paid", "total": "100.00",
            "note": "LA-A1B2C3", "lineItems": [{"productId": "balance-100", "quantity": 1}],
        }
        payload = json.dumps({"data": [paid, {"id": "unpaid", "paymentStatus": "waiting"}]}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return payload

        with patch.object(store_module.urllib.request, "urlopen", return_value=Response()):
            self.assertEqual(self.store.reconcile_shopier_orders("secret"), 1)
            self.assertEqual(self.store.reconcile_shopier_orders("secret"), 1)
        with self.store.engine.connect() as conn:
            count = conn.execute(select(func.count()).select_from(store_module.shopier_orders)).scalar_one()
        self.assertEqual(count, 1)

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

    def test_telegram_auth_remains_valid_during_same_day_reopen(self):
        token = "123:bot-secret"
        user = json.dumps({"id": 42}, separators=(",", ":"))
        fields = {"auth_date": str(int(time.time()) - 1800), "user": user}
        check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        encoded = "&".join(f"{key}={__import__('urllib.parse').parse.quote(value)}" for key, value in fields.items())
        self.assertEqual(store_module.verify_telegram_init_data(encoded, token)["id"], 42)


if __name__ == "__main__":
    unittest.main()
