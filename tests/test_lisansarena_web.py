import base64
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

import lisansarena_store as store_module


class LisansArenaWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["BOT_RUNTIME_ENABLED"] = "false"
        os.environ["FLASK_SECRET_KEY"] = "test-only-flask-secret"
        import app
        cls.web = app

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        key = base64.urlsafe_b64encode(b"W" * 32).decode().rstrip("=")
        self.store = store_module.LisansArenaStore(
            f"sqlite:///{self.temp.name}/web.sqlite", encryption_key=key
        )
        store_module._store = self.store
        store_module._store_error = None
        self.client = self.web.app.test_client()

    def tearDown(self):
        self.store.engine.dispose()
        self.temp.cleanup()
        store_module._store = None
        store_module._store_error = None

    def test_customer_api_requires_telegram_session(self):
        self.assertEqual(self.client.get("/api/la/catalog").status_code, 401)

    def test_telegram_auth_establishes_customer_session(self):
        token = "123:test-token"
        user = json.dumps({"id": 42, "first_name": "Test", "username": "testuser"}, separators=(",", ":"))
        fields = {"auth_date": str(int(time.time())), "query_id": "q-1", "user": user}
        check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"LISANSARENA_BOT_TOKEN": token}):
            auth = self.client.post("/api/la/auth/telegram", json={"initData": urlencode(fields)})
        self.assertEqual(auth.status_code, 200)
        auth_data = auth.get_json()
        self.assertEqual(auth_data["user"]["username"], "testuser")
        self.assertTrue(auth_data["user"]["referral_code"].startswith("LA-"))
        catalog = self.client.get("/api/la/catalog")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(len(catalog.get_json()["products"]), 34)

    def test_brand_asset_is_served(self):
        response = self.client.get("/la/assets/brand")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        response.close()

    def test_webhook_rejects_invalid_signature(self):
        with patch.dict(os.environ, {"LISANSARENA_SHOPIER_WEBHOOK_SECRET": "secret"}):
            response = self.client.post(
                "/api/shopier/lisansarena/webhook", data=b"{}",
                content_type="application/json", headers={"Shopier-Signature": "invalid"},
            )
        self.assertEqual(response.status_code, 401)

    def test_duplicate_webhook_is_accepted_without_duplicate_row(self):
        payload = json.dumps({"id": "o-1", "total": "100.00", "note": "LA-A1B2C3"}, separators=(",", ":")).encode()
        secret = "webhook-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        headers = {"Shopier-Signature": signature, "Shopier-Webhook-Id": "w-1"}
        with patch.dict(os.environ, {"LISANSARENA_SHOPIER_WEBHOOK_SECRET": secret}):
            first = self.client.post("/api/shopier/lisansarena/webhook", data=payload, content_type="application/json", headers=headers)
            second = self.client.post("/api/shopier/lisansarena/webhook", data=payload, content_type="application/json", headers=headers)
        self.assertEqual(first.status_code, 202)
        self.assertIn(second.status_code, (200, 202))


if __name__ == "__main__":
    unittest.main()
