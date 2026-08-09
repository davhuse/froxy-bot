import importlib
import os
import unittest


class PanelSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["BOT_RUNTIME_ENABLED"] = "false"
        os.environ["PANEL_ADMIN_TOKEN"] = "test-panel-token"
        os.environ.pop("SHOPIER_CALLBACK_SECRET", None)
        cls.module = importlib.import_module("app")
        cls.client = cls.module.app.test_client()

    def test_health_and_status_are_public(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/status").status_code, 200)

    def test_privileged_api_rejects_missing_token(self):
        response = self.client.get("/api/group-status")
        self.assertEqual(response.status_code, 401)

    def test_privileged_api_accepts_header_token(self):
        response = self.client.get(
            "/api/group-status", headers={"X-Admin-Token": "test-panel-token"}
        )
        self.assertEqual(response.status_code, 200)

    def test_shopier_callback_fails_closed_without_secret(self):
        response = self.client.post("/api/shopier/callback")
        self.assertEqual(response.status_code, 503)

    def test_config_api_never_returns_or_accepts_secrets(self):
        headers = {"X-Admin-Token": "test-panel-token"}
        response = self.client.get("/api/config", headers=headers)
        self.assertEqual(response.status_code, 200)
        for key in response.get_json():
            self.assertFalse(any(marker in key.lower() for marker in ("token", "session", "secret", "key", "hash")))
        rejected = self.client.post(
            "/api/config",
            headers={**headers, "Content-Type": "application/json"},
            json={"ad_string_session": "must-not-be-stored"},
        )
        self.assertEqual(rejected.status_code, 400)

    def test_status_does_not_report_stale_authorization_without_process(self):
        data = self.client.get("/api/status").get_json()
        if data["ad_processes"] == 0:
            self.assertEqual(data["status"], "stopped")
            for account in data["ad_accounts"].values():
                self.assertFalse(account["process_running"])
                self.assertFalse(account["telegram_connected"])
                self.assertFalse(account["telegram_authorized"])


if __name__ == "__main__":
    unittest.main()
