import os
import hashlib
import hmac
import json
import unittest
from datetime import timedelta
from unittest.mock import patch

from sales_conversion import (
    EXPERIMENT_START,
    apply_cta_experiment,
    cta_experiment_arm,
    cta_experiment_status,
    has_sales_query,
    apply_froxy_price_overrides,
    is_allowed_shopier_url,
    load_sales_catalog,
    make_purchase_token,
    match_sales_products,
    parse_cta_start_parameter,
    parse_purchase_token,
    listing_url,
    purchase_target_url,
)


class SalesCatalogMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keyvadi = load_sales_catalog("keyvadi")
        cls.froxy = load_sales_catalog("froxy")
        cls.all_products = cls.keyvadi + cls.froxy

    def test_all_79_active_products_match_their_own_name(self):
        self.assertEqual(len(self.keyvadi), 61)
        self.assertEqual(len(self.froxy), 18)
        for catalog in (self.keyvadi, self.froxy):
            for product in catalog:
                with self.subTest(product=product["title"]):
                    matches = match_sales_products(product["title"], catalog)
                    self.assertTrue(matches)
                    self.assertEqual(matches[0]["id"], product["id"])

    def test_common_aliases_and_turkish_ascii_queries_match(self):
        cases = {
            "netfilix": "netflix",
            "gpt kisisel": "chatgpt",
            "chat gbt plas uyeligi": "chatgpt",
            "market kuponu": "market",
            "marketü kuponu": "market",
            "disney": "disney",
            "discord": "discord",
            "ofis": "office",
            "office365": "office",
            "windows keyi": "windows",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                matches = match_sales_products(query, self.all_products)
                self.assertTrue(matches)
                self.assertIn(expected, matches[0]["title"].casefold())

    def test_generic_queries_return_at_most_three_relevant_variants(self):
        for query in ("Netflix", "Adobe", "Gemini"):
            with self.subTest(query=query):
                matches = match_sales_products(query, self.all_products)
                self.assertGreaterEqual(len(matches), 1)
                self.assertLessEqual(len(matches), 3)
                self.assertTrue(all(query.casefold() in item["title"].casefold() for item in matches))

    def test_specific_variant_returns_one_product(self):
        matches = match_sales_products("chatgpt plus 1 aylik kisisel", self.all_products)
        self.assertEqual(len(matches), 1)
        self.assertIn("kişisel", matches[0]["title"].casefold())

    def test_unrelated_message_does_not_select_random_product(self):
        self.assertEqual(match_sales_products("selam teslimat gecikti", self.all_products), [])
        self.assertFalse(has_sales_query("selam teslimat gecikti"))

    def test_windows_and_office_are_independent_sequential_products(self):
        windows = match_sales_products("windows keyi", self.keyvadi)
        office = match_sales_products("office 365", self.keyvadi)
        self.assertEqual(len(windows), 1)
        self.assertEqual(len(office), 1)
        self.assertNotEqual(windows[0]["id"], office[0]["id"])

    def test_lisansarena_catalog_supports_signed_purchase_links(self):
        from sales_conversion import make_purchase_token, parse_purchase_token
        catalog = load_sales_catalog("lisansarena")
        product = next(item for item in catalog if item["id"] == "la-approved-chatgpt-kisisel")
        self.assertEqual(product["price"], "499,90 TL")
        with patch.dict(os.environ, {"PURCHASE_LINK_SECRET": "unit-test-secret"}):
            token = make_purchase_token("lisansarena", product["id"], "ad_account_dm", "control")
            payload = parse_purchase_token(token)
        self.assertEqual(payload["b"], "lisansarena")
        self.assertEqual(payload["p"], product["id"])

    def test_lisansarena_auxiliary_products_get_internal_purchase_targets(self):
        from sales_conversion import make_purchase_token, parse_purchase_token
        catalog = load_sales_catalog("lisansarena")
        auxiliary_ids = {
            "la-email-netflix-ortak", "la-approved-chatgpt-ortak",
            "la-approved-gemini-pro-3ay", "la-approved-discord-nitro-14x",
        }
        products = [item for item in catalog if item["id"] in auxiliary_ids]
        self.assertEqual({item["id"] for item in products}, auxiliary_ids)
        for product in products:
            self.assertIn("/la/app?product=", product["url"])
            with patch.dict(os.environ, {"PURCHASE_LINK_SECRET": "unit-test-secret"}):
                token = make_purchase_token("lisansarena", product["id"], "support_bot_dm")
                payload = parse_purchase_token(token)
            self.assertEqual(payload["p"], product["id"])

    def test_froxy_chatgpt_prices_and_codex_variant_are_specific(self):
        froxy = load_sales_catalog("froxy")
        personal = match_sales_products("chat gbt plus kişisel", froxy)
        codex = match_sales_products("chatgpt codex dahil", froxy)
        self.assertEqual([(item["id"], item["price"]) for item in personal], [("49489691", "499,90 TL")])
        self.assertEqual([(item["id"], item["price"]) for item in codex], [("49489721", "599,90 TL")])


class PurchaseLinkTests(unittest.TestCase):
    def test_froxy_approved_prices_override_stale_showroom_values(self):
        personal = apply_froxy_price_overrides({"id": "49489691", "price": "499,99 TL"})
        codex = apply_froxy_price_overrides({"id": "49489721", "price": "599,99 TL"})
        self.assertEqual(personal["price"], "499,90 TL")
        self.assertEqual(codex["price"], "599,90 TL")

    def test_froxy_purchase_redirect_uses_product_shopier_listing(self):
        product = {"id": "49489691", "url": "https://www.shopier.com/froxyai/49489691"}
        self.assertEqual(purchase_target_url("froxy", product), product["url"])
        self.assertEqual(listing_url(product), product["url"])

    def test_other_brands_keep_their_configured_target(self):
        product = {"id": "x", "url": "https://www.shopier.com/keyvadi/x"}
        self.assertEqual(purchase_target_url("keyvadi", product), product["url"])

    def test_signed_token_round_trip_and_tamper_rejection(self):
        product = load_sales_catalog("keyvadi")[0]
        with patch.dict(os.environ, {"PURCHASE_LINK_SECRET": "unit-test-secret"}):
            token = make_purchase_token("keyvadi", product["id"], "support_bot_dm", "test")
            payload = parse_purchase_token(token)
            self.assertEqual(payload["p"], product["id"])
            self.assertEqual(payload["a"], "test")
            body, signature = token.split(".", 1)
            tampered_body = ("A" if body[0] != "A" else "B") + body[1:]
            self.assertIsNone(parse_purchase_token(f"{tampered_body}.{signature}"))

    def test_only_official_shopier_hosts_are_allowed(self):
        self.assertTrue(is_allowed_shopier_url("https://www.shopier.com/froxyai/123"))
        self.assertTrue(is_allowed_shopier_url("https://shopier.com/keyvadi/123"))
        self.assertFalse(is_allowed_shopier_url("https://shopier.com.evil.example/123"))
        self.assertFalse(is_allowed_shopier_url("http://www.shopier.com/froxyai/123"))

    def test_redirect_records_click_and_returns_froxy_shopier_302(self):
        import app as web_app

        product = load_sales_catalog("froxy")[0]
        with patch.dict(os.environ, {"PURCHASE_LINK_SECRET": "unit-test-secret"}):
            token = make_purchase_token("froxy", product["id"], "support_bot_dm", "control")
            with patch.object(web_app, "record_event") as record:
                response = web_app.app.test_client().get(f"/go/{token}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], product["url"])
        self.assertEqual(record.call_args.args[:2], ("purchase_click", "froxy"))

    def test_redirect_rejects_invalid_token(self):
        import app as web_app

        self.assertEqual(web_app.app.test_client().get("/go/not-signed").status_code, 404)


class ShopierOrderTests(unittest.TestCase):
    def test_order_ingestion_is_deduplicated_by_order_number(self):
        import shopier_orders

        order = {
            "id": "order-42",
            "paymentStatus": "paid",
            "totals": {"total": "99.90"},
            "shippingInfo": {"email": "buyer@example.com", "phone": "+905551112233"},
            "lineItems": [{"title": "ChatGPT Plus"}],
        }
        with patch.object(shopier_orders.firestore_helper, "claim_document", side_effect=[True, False]), patch.object(
            shopier_orders.firestore_helper, "get_document", return_value=None
        ), patch.object(shopier_orders.firestore_helper, "set_document"), patch.object(
            shopier_orders, "record_event"
        ) as record:
            self.assertTrue(shopier_orders.ingest_shopier_order(order, "KeyVadi", "webhook"))
            self.assertFalse(shopier_orders.ingest_shopier_order(order, "KeyVadi", "webhook"))
        record.assert_called_once()

    def test_current_shopier_webhook_signature_and_json_order(self):
        import app as web_app

        payload = json.dumps({"id": "order-43", "paymentStatus": "paid"}, separators=(",", ":")).encode()
        secret = "webhook-test-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        with patch.object(web_app, "SHOPIER_CALLBACK_SECRET", secret), patch.object(
            web_app, "ingest_shopier_order", return_value=True
        ) as ingest:
            response = web_app.app.test_client().post(
                "/api/shopier/callback",
                data=payload,
                content_type="application/json",
                headers={"Shopier-Signature": signature, "Shopier-Account-Id": "shop-1"},
            )
        self.assertEqual(response.status_code, 200)
        ingest.assert_called_once()


class CtaExperimentTests(unittest.TestCase):
    def test_assignment_is_deterministic_and_balanced(self):
        first = [cta_experiment_arm("keyvadi", f"group-{index}") for index in range(1000)]
        second = [cta_experiment_arm("keyvadi", f"group-{index}") for index in range(1000)]
        self.assertEqual(first, second)
        test_share = first.count("test") / len(first)
        self.assertGreater(test_share, 0.45)
        self.assertLess(test_share, 0.55)

    def test_three_day_test_automatically_extends_to_seven_days(self):
        self.assertEqual(
            cta_experiment_status(EXPERIMENT_START + timedelta(days=2))["phase"],
            "initial_3_days",
        )
        self.assertEqual(
            cta_experiment_status(EXPERIMENT_START + timedelta(days=4))["phase"],
            "extended_to_7_days",
        )
        self.assertEqual(
            cta_experiment_status(EXPERIMENT_START + timedelta(days=8))["phase"],
            "complete",
        )

    def test_legacy_cta_helper_no_longer_generates_deep_link(self):
        message = "Ürün listesi aynen kalır. İletişim: @KeyVadiSatisBot"
        with patch("sales_conversion.cta_experiment_status", return_value={"phase": "initial_3_days"}), patch(
            "sales_conversion.cta_experiment_arm", return_value="test"
        ):
            updated, arm = apply_cta_experiment(message, "keyvadi", "example-group")
        self.assertEqual(arm, "plain_mention")
        self.assertTrue(updated.startswith("Ürün listesi aynen kalır."))
        self.assertIn("@KeyVadiSatisBot", updated)
        self.assertNotIn("https://", updated)
        self.assertNotIn("?start=", updated)


if __name__ == "__main__":
    unittest.main()
