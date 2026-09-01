import hashlib
import hmac
import json
import os
import threading
import time
import unittest
from urllib.parse import urlencode
from unittest import mock


os.environ["APP_ENV"] = "test"
os.environ["FROXY_STORE_BACKEND"] = "memory"
os.environ["FROXY_ALLOW_DEV_AUTH"] = "1"
os.environ["FROXY_BOT_TOKEN"] = "test-froxy-token"

from miniapp_froxy import server  # noqa: E402
from miniapp_froxy.froxy_gateway import FroxyGateway, GatewayError, Provider  # noqa: E402
from miniapp_froxy.froxy_store import (  # noqa: E402
    FroxyStore,
    InsufficientBalance,
    QuotaExceeded,
)


class FakeGateway:
    paid_model = {
        "id": "openrouter/test-paid",
        "provider": "openrouter",
        "provider_model_id": "test-paid",
        "is_froxy": False,
        "known_pricing": True,
    }

    def public_catalog(self):
        return {
            "models": [{"id": "froxy-fast", "name": "Froxy Hızlı", "is_froxy": True}],
            "count": 1,
            "active_provider_count": 1,
            "verified_total": 3,
            "refreshed_at": int(time.time()),
        }

    def get_model(self, model_id):
        if model_id == "froxy-fast":
            return {"id": model_id, "is_froxy": True}
        return dict(self.paid_model)

    def reservation_for_chat(self, model, messages, max_tokens):
        return 50

    def actual_chat_credits(self, model, usage, input_text, output_text):
        return 30

    def stream_chat(self, model, messages, **kwargs):
        yield {"type": "delta", "content": "Gerçek "}
        yield {"type": "delta", "content": "yanıt"}
        yield {"type": "provider_done", "usage": {"prompt_tokens": 5, "completion_tokens": 2}, "provider": "fake", "provider_model": "test"}

    def image_credit_cost(self):
        return 40

    def provider_status(self):
        return {"fake": {"healthy": True}}


class FailingGateway(FakeGateway):
    def stream_chat(self, model, messages, **kwargs):
        raise GatewayError("sağlayıcı kapalı")
        yield  # pragma: no cover


class FroxyStoreTests(unittest.TestCase):
    def setUp(self):
        FroxyStore.reset_memory()
        self.store = FroxyStore("memory")
        self.store.get_or_create_user({"id": 101, "first_name": "Test"})

    def test_daily_quota_is_atomic_and_refundable(self):
        for index in range(3):
            self.store.consume_free_quota(101, "text", f"q{index}")
        with self.assertRaises(QuotaExceeded):
            self.store.consume_free_quota(101, "text", "q4")
        self.store.restore_free_quota(101, "text", "q2")
        self.store.consume_free_quota(101, "text", "q5")
        self.assertEqual(0, self.store.get_user(101)["free_text_remaining"])

    def test_parallel_reservations_cannot_overspend(self):
        self.store.credit_balance(101, ai_credits=100, idempotency_key="fund", title="test")
        outcomes = []

        def reserve(key):
            try:
                self.store.reserve_credits(101, key, 80, "chat")
                outcomes.append("ok")
            except InsufficientBalance:
                outcomes.append("insufficient")

        threads = [threading.Thread(target=reserve, args=(f"r{index}",)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(["ok", "insufficient"], outcomes)
        self.assertEqual(20, self.store.get_user(101)["ai_credits"])

    def test_duplicate_credit_is_applied_once(self):
        first = self.store.credit_balance(101, wallet_kurus=5000, idempotency_key="shopier:1", title="topup")
        second = self.store.credit_balance(101, wallet_kurus=5000, idempotency_key="shopier:1", title="topup")
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(5000, self.store.get_user(101)["wallet_kurus"])

    def test_pending_topup_idempotency_survives_store_restart(self):
        self.store.get_or_create_user({"id": 101, "first_name": "Test"})
        self.store.save_topup({
            "product_id": "shopier-1", "user_id": 101, "payment_url": "https://example.test/pay",
            "idempotency_key": "checkout-1", "status": "pending",
        })
        found = self.store.get_pending_topup_by_idempotency(101, "checkout-1")
        self.assertEqual("shopier-1", found["product_id"])


class FroxyApiTests(unittest.TestCase):
    def setUp(self):
        FroxyStore.reset_memory()
        server.store = FroxyStore("memory")
        server.gateway = FakeGateway()
        server._rate_buckets.clear()
        self.client = server.app.test_client()
        self.headers = {"X-Dev-User-Id": "202", "Content-Type": "application/json"}

    def test_signed_telegram_init_data_and_tampering(self):
        user = json.dumps({"id": 777, "first_name": "Froxy"}, separators=(",", ":"))
        fields = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
        check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
        secret = hmac.new(b"WebAppData", b"test-froxy-token", hashlib.sha256).digest()
        fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        raw = urlencode(fields)
        self.assertEqual(777, server.verify_telegram_init_data(raw)["id"])
        self.assertIsNone(server.verify_telegram_init_data(raw.replace("Froxy", "Hacker")))

    def test_me_exposes_two_balances_and_quota(self):
        response = self.client.get("/api/me", headers=self.headers)
        self.assertEqual(200, response.status_code)
        user = response.get_json()["user"]
        self.assertEqual(0, user["wallet_kurus"])
        self.assertEqual(0, user["ai_credits"])
        self.assertEqual(3, user["free_text_remaining"])
        self.assertEqual(1, user["free_image_remaining"])

    def test_paid_chat_stream_settles_actual_credits(self):
        server.store.get_or_create_user({"id": 202, "first_name": "Test"})
        server.store.credit_balance(202, ai_credits=100, idempotency_key="fund", title="test")
        response = self.client.post("/api/chat", headers=self.headers, json={
            "request_id": "chat-success",
            "model": "openrouter/test-paid",
            "messages": [{"role": "user", "content": "Merhaba"}],
        })
        body = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("Gerçek", body)
        self.assertIn("event: done", body)
        self.assertEqual(70, server.store.get_user(202)["ai_credits"])

    def test_failed_chat_refunds_reservation(self):
        server.gateway = FailingGateway()
        server.store.get_or_create_user({"id": 202, "first_name": "Test"})
        server.store.credit_balance(202, ai_credits=100, idempotency_key="fund", title="test")
        response = self.client.post("/api/chat", headers=self.headers, json={
            "request_id": "chat-fail",
            "model": "openrouter/test-paid",
            "messages": [{"role": "user", "content": "Merhaba"}],
        })
        self.assertIn("event: error", response.get_data(as_text=True))
        self.assertEqual(100, server.store.get_user(202)["ai_credits"])

    def test_wallet_purchase_is_idempotent_and_manual_when_stock_empty(self):
        server.store.get_or_create_user({"id": 202, "first_name": "Test"})
        server.store.credit_balance(202, wallet_kurus=100000, idempotency_key="fund", title="test")
        payload = {"product_id": "49489691", "idempotency_key": "purchase-1"}
        with mock.patch.object(server, "allocate_license", return_value={"status": "pending_delivery", "license_key": None}):
            first = self.client.post("/api/user/purchase", headers=self.headers, json=payload)
            second = self.client.post("/api/user/purchase", headers=self.headers, json=payload)
        self.assertEqual(200, first.status_code)
        self.assertEqual("manual_pending", first.get_json()["order"]["status"])
        self.assertTrue(second.get_json()["duplicate"])
        self.assertEqual(100000 - 49990, server.store.get_user(202)["wallet_kurus"])

    def test_together_catalog_prices_are_normalized_from_per_million_units(self):
        provider = Provider("together", "Together", "https://example.test", ("TOGETHER_API_KEY",))
        model = FroxyGateway._normalize_model(provider, {
            "id": "test-model",
            "pricing": {"input": 0.2, "output": 0.3},
        })
        self.assertAlmostEqual(0.2 / 1_000_000, model["prompt_usd_per_token"])
        self.assertAlmostEqual(0.3 / 1_000_000, model["completion_usd_per_token"])

    def test_shopier_products_keep_real_title_and_delivery_terms(self):
        products = server.load_products()
        self.assertEqual(18, len(products))
        for product in products:
            self.assertIn(product["title"], product["description"])
            if product["category"] != "credits":
                self.assertIn("1–3 iş günü", product["description"])
                self.assertNotIn("anında teslimat", product["description"].lower())


if __name__ == "__main__":
    unittest.main()
