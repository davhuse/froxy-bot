import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import support_flow


class SupportFlowTicketTests(unittest.TestCase):
    def test_save_ticket_record_is_visible_to_panel_file(self):
        with tempfile.TemporaryDirectory() as directory:
            tickets_file = Path(directory) / "tickets.json"
            with patch.object(support_flow, "TICKETS_FILE", str(tickets_file)), patch.object(
                support_flow, "TICKETS_LOCK_FILE", str(Path(directory) / "tickets.json.lock")
            ):
                support_flow.save_ticket_record(
                    "Froxy AI", 12345, "Ada", "Lovelace", "@ada", "ChatGPT almak istiyorum"
                )

            tickets = json.loads(tickets_file.read_text(encoding="utf-8"))
            self.assertEqual(tickets[0]["bot_type"], "Froxy AI")
            self.assertEqual(tickets[0]["user_id"], 12345)
            self.assertEqual(tickets[0]["message"], "ChatGPT almak istiyorum")

    def test_save_ticket_record_keeps_newest_200(self):
        with tempfile.TemporaryDirectory() as directory:
            tickets_file = Path(directory) / "tickets.json"
            with patch.object(support_flow, "TICKETS_FILE", str(tickets_file)), patch.object(
                support_flow, "TICKETS_LOCK_FILE", str(Path(directory) / "tickets.json.lock")
            ):
                for user_id in range(205):
                    support_flow.save_ticket_record(
                        "KeyVadi", user_id, "", "", "Yok", f"mesaj {user_id}"
                    )

            tickets = json.loads(tickets_file.read_text(encoding="utf-8"))
            self.assertEqual(len(tickets), 200)
            self.assertEqual(tickets[0]["user_id"], 204)
            self.assertEqual(tickets[-1]["user_id"], 5)

    def test_dm_logs_api_includes_tickets_fallback(self):
        os.environ["PANEL_ADMIN_TOKEN"] = "test-support-panel-token"
        from app import app
        with tempfile.TemporaryDirectory() as directory:
            tickets_file = Path(directory) / "tickets.json"
            tickets_data = [
                {
                    "bot_type": "LisansArena",
                    "user_id": 999111,
                    "username": "@testuser",
                    "message": "Adobe lisans var mı?",
                    "timestamp": "2026-08-22 01:20:00"
                }
            ]
            tickets_file.write_text(json.dumps(tickets_data), encoding="utf-8")
            client = app.test_client()
            with patch("os.path.exists", side_effect=lambda p: str(p) == "tickets.json" or str(p) == str(tickets_file)), \
                 patch("builtins.open", patch_open(tickets_file, tickets_data)):
                response = client.get(
                    "/api/dm-logs",
                    headers={"X-Admin-Token": "test-support-panel-token"},
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertIn("logs", data)


def patch_open(tickets_file, tickets_data):
    import io
    orig_open = open
    def custom_open(file, *args, **kwargs):
        if str(file) == "tickets.json":
            return io.StringIO(json.dumps(tickets_data))
        return orig_open(file, *args, **kwargs)
    return custom_open


if __name__ == "__main__":
    unittest.main()
