import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


os.environ["APP_ENV"] = "test"
os.environ["FROXY_STORE_BACKEND"] = "memory"
os.environ["FROXY_ALLOW_DEV_AUTH"] = "1"

from miniapp_froxy import server  # noqa: E402
from miniapp_froxy.froxy_gateway import FroxyGateway  # noqa: E402
from miniapp_froxy.froxy_store import FroxyStore  # noqa: E402


class CatalogGateway:
    def public_catalog(self):
        rows = [
            {"id": f"vendor/model-{index}", "name": f"Model {index}", "provider": "vendor", "family": "Test", "kind": "chat", "capabilities": ["chat", "reasoning"] if index % 2 or index == 0 else ["chat"], "availability": "active", "selectable": True, "estimated_1k_credits": index + 1}
            for index in range(7)
        ]
        return {"models": rows, "count": len(rows), "active_model_count": len(rows), "catalog_model_count": 0, "unavailable_model_count": 0, "providers": {}}

    def image_models(self):
        return []

    def media_models(self, modality):
        return [{"id": "catalog-video", "name": "Catalog Video", "provider": "vendor", "kind": modality, "availability": "catalog_only", "selectable": False, "active": False}]


class FroxyV2ApiTests(unittest.TestCase):
    def setUp(self):
        FroxyStore.reset_memory()
        server.store = FroxyStore("memory")
        server.gateway = CatalogGateway()
        server._rate_buckets.clear()
        self.client = server.app.test_client()
        self.headers = {"X-Dev-User-Id": "90210", "Content-Type": "application/json"}

    def test_model_library_is_cursor_paginated_and_filterable(self):
        first = self.client.get("/api/models?limit=3&capability=reasoning")
        self.assertEqual(200, first.status_code)
        body = first.get_json()
        self.assertEqual(3, len(body["models"]))
        self.assertEqual("3", body["next_cursor"])
        second = self.client.get("/api/models?limit=3&capability=reasoning&cursor=3").get_json()
        self.assertEqual(1, len(second["models"]))
        self.assertIsNone(second["next_cursor"])

    def test_model_detail_contains_health_pricing_and_schema(self):
        body = self.client.get("/api/models/vendor/model-1").get_json()
        self.assertTrue(body["success"])
        self.assertIn("health", body)
        self.assertIn("pricing", body)
        self.assertEqual(["adaptive"], body["input_schema"]["reasoning_levels"])

    def test_media_catalog_does_not_fake_activation(self):
        body = self.client.get("/api/media/models?modality=video").get_json()
        self.assertEqual(1, body["count"])
        self.assertEqual(0, body["active_count"])
        self.assertFalse(body["models"][0]["selectable"])

    def test_watchlist_crud_is_scoped_to_user(self):
        created = self.client.post("/api/research/watchlists", headers=self.headers, json={"topic": "Yapay zekâ düzenlemeleri"})
        self.assertEqual(201, created.status_code)
        watch_id = created.get_json()["watchlist"]["watch_id"]
        listed = self.client.get("/api/research/watchlists", headers=self.headers).get_json()["watchlists"]
        self.assertEqual(watch_id, listed[0]["watch_id"])
        deleted = self.client.delete(f"/api/research/watchlists/{watch_id}", headers=self.headers).get_json()
        self.assertTrue(deleted["deleted"])

    def test_credit_package_can_be_bought_through_unified_wallet_checkout(self):
        product = next(row for row in server.load_products() if row.get("store_category") == "credits")
        price_kurus = int(round(float(product["price_num"]) * 100))
        server.store.get_or_create_user({"id": 90210, "first_name": "V2"})
        server.store.credit_balance(90210, wallet_kurus=price_kurus, idempotency_key="fund-v2", title="test")
        response = self.client.post("/api/checkout", headers=self.headers, json={"mode": "wallet", "items": [{"id": product["id"], "qty": 1}], "idempotency_key": "credits-cart-v2"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["completed"])
        user = server.store.get_user(90210)
        self.assertEqual(0, user["wallet_kurus"])
        self.assertEqual(server._credit_amount_for_product(product), user["ai_credits"])


class FroxyCatalogCacheTests(unittest.TestCase):
    def test_non_chat_modalities_never_enter_chat_picker(self):
        self.assertFalse(FroxyGateway._is_chat_model({"kind": "audio", "provider_model_id": "gpt-audio", "modality": "text->text"}))
        self.assertFalse(FroxyGateway._is_chat_model({"kind": "image", "provider_model_id": "qwen-image", "modality": "text->text"}))

    def test_sqlite_cache_survives_provider_failure(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {"FROXY_CATALOG_DB": str(Path(directory) / "catalog.db")}, clear=False):
            gateway = FroxyGateway(session=mock.Mock())
            gateway._catalog = [{"id": "cached/model", "name": "Cached", "availability": "catalog_only", "selectable": False}]
            gateway._models = {"cached/model": dict(gateway._catalog[0])}
            gateway._provider_status = {"cached": {"healthy": False}}
            gateway._refreshed_at = time.time() - gateway.CATALOG_TTL - 1
            gateway._save_catalog_cache()
            restarted = FroxyGateway(session=mock.Mock())
            self.assertEqual("cached/model", restarted._catalog[0]["id"])
            with mock.patch.object(restarted, "providers", return_value=[]):
                self.assertEqual("cached/model", restarted.refresh_catalog(force=True)[0]["id"])


class FroxyFirestoreFallbackTests(unittest.TestCase):
    def test_firestore_outage_uses_sqlite_for_user_mutations(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {"FROXY_FALLBACK_DB": str(Path(directory) / "state.db")}, clear=False), mock.patch("miniapp_froxy.froxy_store.firestore_helper.remote_credentials_configured", return_value=True), mock.patch("miniapp_froxy.froxy_store.firestore_helper.get_document_with_meta", return_value=(None, None)), mock.patch("miniapp_froxy.froxy_store.firestore_helper.claim_remote_document", return_value=None):
            store = FroxyStore("firestore")
            created = store.get_or_create_user({"id": 42, "first_name": "Çevrimdışı"})
            self.assertEqual("Çevrimdışı", created["first_name"])
            self.assertEqual(1, store.fallback_state()["dirty_documents"])
            restarted = FroxyStore("firestore")
            loaded = restarted.get_user(42)
            self.assertEqual("Çevrimdışı", loaded["first_name"])


if __name__ == "__main__":
    unittest.main()
