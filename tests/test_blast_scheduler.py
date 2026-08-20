import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blast_scheduler import BlastCoordinator, is_recent_message_from_account


class Clock:
    def __init__(self, value=1_000_000):
        self.value = float(value)

    def __call__(self):
        return self.value


class BlastCoordinatorTests(unittest.TestCase):
    def test_recent_message_guard_matches_only_same_account_inside_window(self):
        from datetime import datetime, timedelta, timezone
        from types import SimpleNamespace

        now = datetime.now(timezone.utc)
        recent = SimpleNamespace(sender_id=42, date=now - timedelta(minutes=5), empty=False)
        old = SimpleNamespace(sender_id=42, date=now - timedelta(hours=2), empty=False)
        other = SimpleNamespace(sender_id=99, date=now - timedelta(minutes=5), empty=False)
        self.assertTrue(is_recent_message_from_account(recent, 42, now=now))
        self.assertFalse(is_recent_message_from_account(old, 42, now=now))
        self.assertFalse(is_recent_message_from_account(other, 42, now=now))

    def make_coordinator(self, directory, clock, owner="worker-a"):
        return BlastCoordinator(
            Path(directory) / "checkpoint.json",
            remote=False,
            owner_id=owner,
            now_fn=clock,
        )

    def test_ready_tie_uses_required_account_order(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            scheduler = self.make_coordinator(directory, clock)
            scheduler.initialize_accounts({name: 0 for name in (
                "KeyVadiOnline", "FroxyOnline", "LisansArenaOnline"
            )})
            self.assertFalse(scheduler.try_acquire_turn("FroxyOnline"))
            self.assertTrue(scheduler.try_acquire_turn("KeyVadiOnline"))
            self.assertFalse(scheduler.try_acquire_turn("LisansArenaOnline"))

    def test_remote_checkpoint_is_materialized_for_status_api(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            checkpoint = Path(directory) / "checkpoint.json"
            seed = self.make_coordinator(directory, clock)
            seed.initialize_accounts({"KeyVadiOnline": 600})
            remote_state = seed.snapshot()
            checkpoint.unlink()

            with patch.object(BlastCoordinator, "_load_remote", return_value=remote_state):
                restored = BlastCoordinator(
                    checkpoint,
                    remote=True,
                    owner_id="after-deploy",
                    now_fn=clock,
                )
            restored.initialize_accounts({"KeyVadiOnline": 600})

            self.assertTrue(checkpoint.exists())
            self.assertEqual(
                restored.snapshot()["accounts"]["KeyVadiOnline"]["due_at"],
                remote_state["accounts"]["KeyVadiOnline"]["due_at"],
            )

    def test_deploy_resumes_same_targets_and_never_repeats_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            first = self.make_coordinator(directory, clock, owner="before-deploy")
            first.initialize_accounts({"KeyVadiOnline": 0})
            self.assertTrue(first.try_acquire_turn("KeyVadiOnline"))
            cycle = first.begin_cycle(
                "KeyVadiOnline", ["group-b", "group-a"], ["one.txt", "two.txt"]
            )
            self.assertEqual([item["group"] for item in cycle["targets"]], ["group-a", "group-b"])
            item = first.next_target("KeyVadiOnline")
            first.claim_target("KeyVadiOnline", item["index"])
            first.finish_target("KeyVadiOnline", item["index"], "accepted", message_id=99)

            after = self.make_coordinator(directory, clock, owner="after-deploy")
            after.initialize_accounts({"KeyVadiOnline": 0})
            self.assertTrue(after.try_acquire_turn("KeyVadiOnline"))
            resumed = after.begin_cycle(
                "KeyVadiOnline", ["different-new-list"], ["changed.txt"]
            )
            self.assertEqual(resumed["run_id"], cycle["run_id"])
            self.assertEqual(after.next_target("KeyVadiOnline")["group"], "group-b")

    def test_previous_process_claim_is_skipped_uncertain(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            first = self.make_coordinator(directory, clock, owner="old")
            first.initialize_accounts({"KeyVadiOnline": 0})
            first.try_acquire_turn("KeyVadiOnline")
            first.begin_cycle("KeyVadiOnline", ["a", "b"], ["one"])
            first.claim_target("KeyVadiOnline", 0)

            second = self.make_coordinator(directory, clock, owner="new")
            second.initialize_accounts({"KeyVadiOnline": 0})
            self.assertTrue(second.try_acquire_turn("KeyVadiOnline"))
            self.assertEqual(second.next_target("KeyVadiOnline")["group"], "b")
            state = second.snapshot()["accounts"]["KeyVadiOnline"]
            self.assertEqual(state["targets"][0]["state"], "skipped_uncertain")

    def test_deferred_target_releases_turn_for_another_due_account(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            scheduler = self.make_coordinator(directory, clock)
            scheduler.initialize_accounts({"KeyVadiOnline": 0, "FroxyOnline": 0})
            scheduler.try_acquire_turn("KeyVadiOnline")
            scheduler.begin_cycle("KeyVadiOnline", ["a"], ["one"])
            scheduler.claim_target("KeyVadiOnline", 0)
            scheduler.defer_current("KeyVadiOnline", 0, 120, "FloodWait")
            self.assertTrue(scheduler.try_acquire_turn("FroxyOnline"))
            state = scheduler.snapshot()["accounts"]["KeyVadiOnline"]
            self.assertEqual(state["targets"][0]["state"], "pending")

    def test_completed_cycle_waits_one_hour(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = Clock()
            scheduler = self.make_coordinator(directory, clock)
            scheduler.initialize_accounts({"KeyVadiOnline": 0})
            scheduler.try_acquire_turn("KeyVadiOnline")
            scheduler.begin_cycle("KeyVadiOnline", ["a"], ["one"])
            scheduler.claim_target("KeyVadiOnline", 0)
            scheduler.finish_target("KeyVadiOnline", 0, "accepted")
            scheduler.complete_cycle("KeyVadiOnline", 3600)
            self.assertEqual(scheduler.remaining_wait("KeyVadiOnline"), 3600)
            self.assertFalse(scheduler.try_acquire_turn("KeyVadiOnline"))


if __name__ == "__main__":
    unittest.main()
