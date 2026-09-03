import asyncio
from datetime import datetime, timezone
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telethon.errors import (
    ChannelPrivateError,
    UserBannedInChannelError,
    UsernameInvalidError,
)

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
        self.assertEqual(publisher.telegram_target_reference("@-3608209943"), -1003608209943)
        self.assertEqual(publisher.telegram_target_reference("@ceksat"), "ceksat")

    def test_legacy_numeric_target_resolves_existing_supergroup_dialog(self):
        entity = self._entity(username=None, entity_id=3608209943)
        joined = {"-1003608209943": entity}
        self.assertIs(
            publisher.joined_entity_for_target(joined, "-3608209943"), entity
        )

    def test_join_errors_are_classified_without_global_blacklist(self):
        self.assertEqual(
            publisher.classify_join_error(ChannelPrivateError(request=None)),
            "access_review",
        )
        self.assertEqual(
            publisher.classify_join_error(UsernameInvalidError(request=None)),
            "unresolvable",
        )
        expired = type("InviteHashExpiredError", (Exception,), {})()
        self.assertEqual(publisher.classify_join_error(expired), "invalid_invite")
        self.assertEqual(
            publisher.classify_join_error(UserBannedInChannelError(request=None)),
            "account_blocked",
        )

    def test_keyvadi_specific_group_approvals_do_not_enable_other_accounts(self):
        self.assertEqual(
            publisher.ACCOUNT_APPROVED_TARGET_OVERRIDES["KeyVadiOnline"],
            {"kuponceking"},
        )
        self.assertIn("kuponinternet", {item.lower() for item in publisher.gruplar})
        self.assertIn("kuponsatimalim", {item.lower() for item in publisher.gruplar})
        self.assertIn(("KeyVadiOnline", "ceksat"), publisher.SEEDED_ACCOUNT_GROUP_BLOCKS)

    def test_replacement_lisansarena_account_is_locked_to_slot_three(self):
        identity = publisher.ACTIVE_ACCOUNT_IDENTITIES["lisansarenadestek"]
        self.assertEqual(identity["stable_name"], "LisansArenaOnline")
        self.assertEqual(identity["user_id"], 8960726264)
        self.assertEqual(identity["slot"], 3)
        self.assertNotIn("lisansarenaonline", publisher.ACTIVE_ACCOUNT_IDENTITIES)

    def test_automatic_group_leaves_are_opt_in(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALLOW_AUTOMATIC_LEAVES", None)
            self.assertFalse(publisher.automatic_leaves_enabled())
            os.environ["ALLOW_AUTOMATIC_LEAVES"] = "1"
            self.assertTrue(publisher.automatic_leaves_enabled())
            os.environ.pop("ALLOW_AUTOMATIC_LEAVES", None)

    def test_send_ban_never_leaves_the_group(self):
        source = inspect.getsource(publisher.main)
        banned_handler = source.split(
            "except UserBannedInChannelError:", 1
        )[1].split("except ChatWriteForbiddenError:", 1)[0]
        self.assertNotIn("LeaveChannelRequest", banned_handler)

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

    def test_confirmed_join_ban_is_immediately_account_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            failures = str(Path(directory) / "failures.json")
            blocks = str(Path(directory) / "blocks.json")
            with patch.object(publisher, "GROUP_FAILURES_FILE", failures), patch.object(
                publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks
            ):
                publisher.record_confirmed_join_block(
                    "samplegroup", "KeyVadiOnline", "UserBannedInChannelError"
                )
                self.assertTrue(publisher.is_account_group_blocked(
                    "samplegroup", "KeyVadiOnline"
                ))
                self.assertFalse(publisher.is_account_group_blocked(
                    "samplegroup", "FroxyOnline"
                ))

    def test_channel_private_reviews_back_off_then_quarantine_one_account(self):
        with tempfile.TemporaryDirectory() as directory:
            failures = str(Path(directory) / "failures.json")
            blocks = str(Path(directory) / "blocks.json")
            with patch.object(publisher, "GROUP_FAILURES_FILE", failures), patch.object(
                publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks
            ):
                first = publisher.record_join_access_review(
                    "privategroup", "KeyVadiOnline", "ChannelPrivateError"
                )
                second = publisher.record_join_access_review(
                    "privategroup", "KeyVadiOnline", "ChannelPrivateError"
                )
                third = publisher.record_join_access_review(
                    "privategroup", "KeyVadiOnline", "ChannelPrivateError"
                )

                self.assertEqual(first["retry_after"], 24 * 60 * 60)
                self.assertEqual(second["retry_after"], 3 * 24 * 60 * 60)
                self.assertEqual(third["status"], "quarantined")
                self.assertFalse(publisher.is_account_group_blocked(
                    "privategroup", "KeyVadiOnline"
                ))
                self.assertFalse(publisher.is_account_group_blocked(
                    "privategroup", "LisansArenaOnline"
                ))
                self.assertTrue(publisher.is_group_retry_blocked(
                    "privategroup", "KeyVadiOnline"
                ))

    def test_audited_join_quarantines_are_account_specific_and_expiring(self):
        with tempfile.TemporaryDirectory() as directory:
            failures = str(Path(directory) / "failures.json")
            with open(failures, "w", encoding="utf-8") as f:
                json.dump({"ceksat": {"FroxyOnline": {"reason": "RepeatedChannelPrivate"}}}, f)
            with patch.object(publisher, "GROUP_FAILURES_FILE", failures):
                changed = publisher.ensure_seeded_account_join_quarantines(
                    datetime(2026, 8, 26, tzinfo=timezone.utc)
                )
                self.assertTrue(changed)
                self.assertFalse(publisher.is_group_retry_blocked("ceksat", "FroxyOnline"))

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
                self.assertEqual(
                    publisher.live_joined_sales_targets(joined, "LisansArenaOnline"),
                    {"yenikuponpazari"},
                )

    def test_candidate_report_is_detailed_and_live_target_replenishes_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            blocks = str(Path(directory) / "blocks.json")
            with patch.object(publisher, "ACCOUNT_GROUP_BLOCKS_FILE", blocks):
                entity = self._entity(username="yenikuponpazari", entity_id=991)
                rows = publisher.live_joined_sales_candidate_report(
                    {"yenikuponpazari": entity}, "FroxyOnline", {"mevcutgrup"}
                )
                self.assertEqual(rows[0]["username"], "yenikuponpazari")
                self.assertTrue(rows[0]["eligible"])
                self.assertFalse(rows[0]["approved"])
                send_targets, _ = publisher.reconcile_send_targets(
                    {"mevcutgrup"}, {rows[0]["username"]}
                )
                self.assertEqual(send_targets, {"mevcutgrup", "yenikuponpazari"})

    def test_live_candidate_expands_send_targets_as_self_healing_reserve(self):
        send_targets, candidates = publisher.reconcile_send_targets(
            {"mevcutgrup"}, {"mevcutgrup", "yenikuponpazari"}
        )
        self.assertEqual(send_targets, {"mevcutgrup", "yenikuponpazari"})
        self.assertEqual(candidates, {"yenikuponpazari"})

    def test_normal_blast_is_deferred_below_floor(self):
        self.assertTrue(publisher.should_defer_blast_for_floor(27, 30))
        self.assertFalse(publisher.should_defer_blast_for_floor(30, 30))
        self.assertFalse(
            publisher.should_defer_blast_for_floor(1, 30, controlled_smoke=True)
        )

    def test_visibility_verification_does_not_move_existing_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "cooldowns.json")
            with patch.object(publisher, "COOLDOWN_FILE", path):
                publisher.set_cooldown("kuponceksatis", "KeyVadiOnline")
                with open(path, encoding="utf-8") as handle:
                    first = json.load(handle)
                publisher.set_cooldown(
                    "kuponceksatis", "KeyVadiOnline", preserve_existing=True
                )
                with open(path, encoding="utf-8") as handle:
                    second = json.load(handle)
                self.assertEqual(first, second)

    def test_in_progress_blast_resumes_without_global_one_hour_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "cooldowns.json")
            empty_cloud = (None, None, None, None, None, None)
            with patch.object(publisher, "COOLDOWN_FILE", path), patch.object(
                publisher, "fs_get_state", return_value=empty_cloud
            ), patch.object(publisher, "fs_set_state"):
                publisher.save_last_blast_time("FroxyOnline")
                self.assertGreater(
                    publisher.get_last_blast_remaining_wait("FroxyOnline"), 3500
                )
                publisher.mark_blast_started("FroxyOnline")
                self.assertEqual(
                    publisher.get_last_blast_remaining_wait("FroxyOnline"), 0
                )

    def test_legacy_per_message_blast_timestamp_is_not_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cooldowns.json"
            path.write_text(json.dumps({
                "__LAST_BLAST_TIME_FroxyOnline": datetime.now(timezone.utc).isoformat()
            }), encoding="utf-8")
            empty_cloud = (None, None, None, None, None, None)
            with patch.object(publisher, "COOLDOWN_FILE", str(path)), patch.object(
                publisher, "fs_get_state", return_value=empty_cloud
            ):
                self.assertEqual(
                    publisher.get_last_blast_remaining_wait("FroxyOnline"), 0
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

    def test_telegram_acceptance_starts_cooldown_before_background_check(self):
        class Sent:
            id = 77
            raw_text = "KeyVadi test"
            media = None

        class Client:
            async def send_message(self, entity, message, **kwargs):
                return Sent()

            async def get_messages(self, entity, ids):
                return Sent()

        def close_background(coro):
            coro.close()
            return SimpleNamespace()

        with patch.object(publisher, "set_cooldown") as set_cooldown, \
                patch.object(publisher, "record_delivery_state"), \
                patch.object(publisher.asyncio, "sleep", new=AsyncMock()), \
                patch.object(
                    publisher.asyncio, "create_task", side_effect=close_background
                ):
            asyncio.run(publisher.send_and_verify_ad(
                Client(), self._entity(), "test", "KeyVadiOnline",
                "kuponceksatis", {},
            ))
            set_cooldown.assert_called_once()

    def test_transport_layer_always_disables_link_preview(self):
        class Sent:
            id = 77
            raw_text = "Froxy panel: @FroxyDestekBOT"
            media = None

        class Client:
            def __init__(self):
                self.kwargs = None

            async def send_message(self, entity, message, **kwargs):
                self.kwargs = kwargs
                return Sent()

            async def get_messages(self, entity, ids):
                return SimpleNamespace(empty=False)

        async def run():
            client = Client()
            def discard_task(coroutine):
                coroutine.close()
                return None
            with patch.object(publisher.asyncio, "sleep", return_value=None), patch.object(
                publisher.asyncio, "create_task", side_effect=discard_task
            ), patch.object(publisher, "set_cooldown"), patch.object(
                publisher, "record_delivery_state"
            ):
                await publisher.send_and_verify_ad(
                    client, self._entity(), Sent.raw_text, "FroxyOnline",
                    "kuponceksatis", {"parse_mode": "md", "link_preview": None},
                )
            return client.kwargs

        kwargs = asyncio.run(run())
        self.assertIs(kwargs["link_preview"], False)

    def test_controlled_release_smoke_awaits_the_full_visibility_check(self):
        class Sent:
            id = 88
            raw_text = "KeyVadi ürün listesi"
            media = None

        class Client:
            async def send_message(self, entity, message, **kwargs):
                return Sent()

            async def get_messages(self, entity, ids):
                return SimpleNamespace(empty=False)

        async def run():
            verifier = AsyncMock(return_value={"success": True, "message_id": 88})
            with patch.object(publisher.asyncio, "sleep", return_value=None), patch.object(
                publisher, "verify_ad_after_window", verifier
            ), patch.object(publisher, "set_cooldown"), patch.object(
                publisher, "record_delivery_state"
            ):
                sent = await publisher.send_and_verify_ad(
                    Client(), self._entity(), Sent.raw_text, "KeyVadiOnline",
                    "indirim363", {
                        "parse_mode": None,
                        "controlled_smoke": True,
                        "verification_seconds": 600,
                    },
                )
            return sent, verifier

        sent, verifier = asyncio.run(run())
        self.assertEqual(sent.id, 88)
        self.assertEqual(verifier.await_count, 1)
        self.assertEqual(verifier.await_args.kwargs["seconds"], 600)
        self.assertTrue(verifier.await_args.kwargs["raise_on_failure"])


if __name__ == "__main__":
    unittest.main()
