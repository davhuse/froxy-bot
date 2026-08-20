import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MINIAPP = ROOT / "miniapp"
if str(MINIAPP) not in sys.path:
    sys.path.insert(0, str(MINIAPP))

import server


class KeyVadiMiniAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = server.USER_DATA_PATH
        server.USER_DATA_PATH = Path(self.temp_dir.name) / "users.json"
        server.save_users({})
        self.client = server.app.test_client()

    def tearDown(self):
        server.USER_DATA_PATH = self.old_path
        self.temp_dir.cleanup()

    def test_user_api_requires_telegram_auth(self):
        response = self.client.get("/api/user/123")
        self.assertEqual(response.status_code, 401)

    def test_simulated_payment_is_disabled(self):
        response = self.client.post("/api/balance/simulate-payment", json={"user_id": 123, "amount": 10})
        self.assertEqual(response.status_code, 404)

    def test_purchase_idempotency_prevents_double_charge(self):
        with patch.dict(os.environ, {"KEYVADI_ALLOW_DEV_AUTH": "1", "APP_ENV": "test"}):
            self.client.post("/api/user/123", json={"user_id": 123})
            users = server.load_users()
            users["123"]["balance"] = 100.0
            server.save_users(users)
            product_id = server.load_products()[0]["id"]
            first = self.client.post("/api/user/purchase", json={
                "user_id": 123, "product_id": product_id, "idempotency_key": "same-order"
            })
            second = self.client.post("/api/user/purchase", json={
                "user_id": 123, "product_id": product_id, "idempotency_key": "same-order"
            })
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json["success"])
        self.assertTrue(second.json["duplicate"])
        self.assertEqual(len(server.load_users()["123"]["orders"]), 1)


if __name__ == "__main__":
    unittest.main()
