import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import bot_runtime_status


class BotRuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir_patch = patch.object(
            bot_runtime_status, "BASE_DIR", Path(self.temp_dir.name)
        )
        self.base_dir_patch.start()
        self.addCleanup(self.base_dir_patch.stop)

    def test_status_never_persists_raw_token(self):
        token = "123456789:AA-not-a-real-token"
        payload = bot_runtime_status.write_bot_status(
            "keyvadi", state="ready", telegram_ready=True,
            token=token, bot_username="KeyVadiSatisBot", connected=True,
        )
        raw = bot_runtime_status.status_path("keyvadi").read_text(encoding="utf-8")
        self.assertNotIn(token, raw)
        self.assertEqual(payload["pid"], os.getpid())
        self.assertTrue(payload["telegram_ready"])
        self.assertTrue(payload["last_connected_at"])

    def test_invalid_token_blocks_only_same_fingerprint(self):
        old_token = "old-token"
        bot_runtime_status.write_bot_status(
            "lisansarena", state="invalid_token", telegram_ready=False,
            token=old_token, last_error="AccessTokenExpiredError",
        )
        self.assertTrue(
            bot_runtime_status.restart_blocked_for_token("lisansarena", old_token)
        )
        self.assertFalse(
            bot_runtime_status.restart_blocked_for_token("lisansarena", "new-token")
        )

    def test_expired_token_errors_are_terminal(self):
        self.assertTrue(
            bot_runtime_status.invalid_token_error(RuntimeError("Bot token expired"))
        )
        self.assertFalse(
            bot_runtime_status.invalid_token_error(RuntimeError("temporary network error"))
        )


if __name__ == "__main__":
    unittest.main()
