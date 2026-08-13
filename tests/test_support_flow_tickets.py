import json
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


if __name__ == "__main__":
    unittest.main()
