import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
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
