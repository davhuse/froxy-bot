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
        self.assertEqual(self.client.get("/api/ad-smoke/status").status_code, 401)

    def test_privileged_api_accepts_header_token(self):
        response = self.client.get(
            "/api/group-status", headers={"X-Admin-Token": "test-panel-token"}
        )
        self.assertEqual(response.status_code, 200)
        smoke = self.client.get(
            "/api/ad-smoke/status", headers={"X-Admin-Token": "test-panel-token"}
        )
        self.assertEqual(smoke.status_code, 200)
        self.assertIn("normal_ads_paused", smoke.get_json())

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

    def test_process_matcher_never_treats_a_shell_command_as_the_bot(self):
        self.assertFalse(self.module.command_runs_python_script(
            "powershell.exe",
            ["powershell.exe", "python -m py_compile otomatik_katil.py"],
            "otomatik_katil.py",
        ))
        self.assertTrue(self.module.command_runs_python_script(
            "python.exe",
            ["python.exe", "-u", "otomatik_katil.py"],
            "otomatik_katil.py",
        ))

    def test_panel_sends_admin_header_and_exposes_controlled_smoke_ui(self):
        script_response = self.client.get("/static/script.js")
        html_response = self.client.get("/")
        script = script_response.get_data(as_text=True)
        html = html_response.get_data(as_text=True)
        script_response.close()
        html_response.close()
        self.assertIn("X-Admin-Token", script)
        self.assertIn("adminFetch('/api/group-status')", script)
        self.assertIn("adminFetch('/api/ad-smoke/start'", script)
        self.assertIn('id="panelAdminToken"', html)
        self.assertIn('id="controlledSmokeGroup"', html)


if __name__ == "__main__":
    unittest.main()
