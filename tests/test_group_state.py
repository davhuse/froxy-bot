import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import otomatik_katil as publisher


class GroupStateTests(unittest.TestCase):
    def test_short_flood_wait_resumes_once(self):
        self.assertTrue(publisher.should_resume_after_flood_wait(134, 0))
        self.assertFalse(publisher.should_resume_after_flood_wait(134, 1))
        self.assertFalse(publisher.should_resume_after_flood_wait(3600, 0))

    def test_permanent_block_is_account_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "account_group_blocks.json")
            with patch.object(publisher, "ACCOUNT_GROUP_BLOCKS_FILE", path):
                publisher.record_account_group_block(
                    "ceksatkupon", "FroxyOnline", "UserBannedInChannel"
                )
                self.assertTrue(
                    publisher.is_account_group_blocked("ceksatkupon", "FroxyOnline")
                )
                self.assertFalse(
                    publisher.is_account_group_blocked("ceksatkupon", "KeyVadiOnline")
                )

    def test_slow_mode_is_only_a_temporary_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            failures = str(Path(directory) / "group_failures.json")
            blocks = str(Path(directory) / "account_group_blocks.json")
            with patch.object(publisher, "GROUP_FAILURES_FILE", failures), patch.object(
                publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks
            ):
                publisher.record_group_failure(
                    "slowgroup", "FroxyOnline", "SlowModeWait", 90
                )
                self.assertTrue(
                    publisher.is_group_retry_blocked("slowgroup", "FroxyOnline")
                )
                self.assertFalse(
                    publisher.is_account_group_blocked("slowgroup", "FroxyOnline")
                )


if __name__ == "__main__":
    unittest.main()
