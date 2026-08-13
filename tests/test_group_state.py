import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from telethon.errors import ChannelPrivateError, UsernameInvalidError

import otomatik_katil as publisher


class GroupStateTests(unittest.TestCase):
    def _entity(self, *, username="kuponceksatis", title="Kupon Çek Satış", members=300,
                broadcast=False, entity_id=12345):
        return SimpleNamespace(
            id=entity_id,
            username=username,
            title=title,
            participants_count=members,
            broadcast=broadcast,
            default_banned_rights=SimpleNamespace(send_messages=False),
        )

    def test_numeric_telegram_target_is_not_treated_as_username(self):
        self.assertEqual(publisher.telegram_target_reference("@-3608209943"), -3608209943)
        self.assertEqual(publisher.telegram_target_reference("@ceksat"), "ceksat")

    def test_join_errors_are_classified_without_global_blacklist(self):
        self.assertEqual(
            publisher.classify_join_error(ChannelPrivateError(request=None)),
            "access_review",
        )
        self.assertEqual(
            publisher.classify_join_error(UsernameInvalidError(request=None)),
            "unresolvable",
        )

    def test_pending_join_requests_are_account_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "pending.json")
            with patch.object(publisher, "PENDING_INVITES_FILE", target):
                publisher.save_pending_invites("FroxyOnline", {"group-a"})
                publisher.save_pending_invites("LisansArenaOnline", {"group-b"})
                self.assertEqual(publisher.load_pending_invites("FroxyOnline"), {"group-a"})
                self.assertEqual(publisher.load_pending_invites("LisansArenaOnline"), {"group-b"})
                with open(target, encoding="utf-8") as handle:
                    persisted = json.load(handle)
                self.assertEqual(set(persisted), {"FroxyOnline", "LisansArenaOnline"})
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

    def test_live_joined_sales_group_becomes_target_without_static_list(self):
        with tempfile.TemporaryDirectory() as directory:
            blocks = str(Path(directory) / "blocks.json")
            with patch.object(publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks):
                entity = self._entity(username="yenikuponpazari", entity_id=991)
                joined = {"yenikuponpazari": entity, "-100991": entity}
                self.assertEqual(
                    publisher.live_joined_sales_targets(joined, "KeyVadiOnline"),
                    {"yenikuponpazari"},
                )

    def test_live_target_requires_150_members_and_rejects_reference_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            blocks = str(Path(directory) / "blocks.json")
            with patch.object(publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks):
                small = self._entity(username="kuponmini", members=149, entity_id=992)
                referral = self._entity(
                    username="kuponreferans", title="Kupon referans kasma", entity_id=993
                )
                self.assertFalse(publisher.joined_sales_target_status(
                    "kuponmini", small, "FroxyOnline"
                )[0])
                self.assertFalse(publisher.joined_sales_target_status(
                    "kuponreferans", referral, "FroxyOnline"
                )[0])

    def test_reopenable_groups_are_removed_from_global_blacklist(self):
        cleaned = publisher.remove_reopenable_sales_blacklist({
            "kuponceking", "hesapsatisgenel", "illegalalimsatimerkezi"
        })
        self.assertEqual(cleaned, {"illegalalimsatimerkezi"})

    def test_cooldown_is_written_only_after_ten_minute_visibility_passes(self):
        class VisibleClient:
            async def get_messages(self, entity, ids):
                return SimpleNamespace(empty=False)

        with patch.object(publisher, "set_cooldown") as set_cooldown, \
                patch.object(publisher, "record_event"), \
                patch.object(publisher, "record_delivery_state"), \
                patch.object(publisher, "update_stats"), \
                patch.object(publisher, "clear_group_failure"), \
                patch.object(publisher, "update_ad_account_status"):
            asyncio.run(publisher.verify_ad_after_window(
                VisibleClient(), self._entity(), 42, "FroxyOnline",
                "kuponceksatis", seconds=0, experiment_arm="policy_smoke"
            ))
            set_cooldown.assert_called_once()

    def test_deleted_ten_minute_smoke_never_creates_cooldown(self):
        class DeletedClient:
            async def get_messages(self, entity, ids):
                return SimpleNamespace(empty=True)

        with patch.object(publisher, "set_cooldown") as set_cooldown, \
                patch.object(publisher, "record_event"), \
                patch.object(publisher, "record_moderation_hold"), \
                patch.object(publisher, "record_group_failure"):
            asyncio.run(publisher.verify_ad_after_window(
                DeletedClient(), self._entity(), 43, "KeyVadiOnline",
                "indirim363", seconds=0, experiment_arm="policy_smoke"
            ))
            set_cooldown.assert_not_called()


if __name__ == "__main__":
    unittest.main()
