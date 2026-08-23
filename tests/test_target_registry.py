import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import otomatik_katil as publisher
from target_registry import TargetRegistry, generate_discovery_queries, score_candidate
from telethon.tl.types import Channel


class TargetRegistryTests(unittest.TestCase):
    def test_configured_queries_are_used_deduplicated_and_bounded(self):
        queries = generate_discovery_queries(
            ["Kupon Kod Satış", "kupon kod satis", "Hediye Çeki Alım Satım"],
            limit=4,
        )
        self.assertEqual(queries[0], "Kupon Kod Satış")
        self.assertIn("Hediye Çeki Alım Satım", queries)
        self.assertLessEqual(len(queries), 4)
        self.assertEqual(len(queries), len({item.casefold() for item in queries}))

    def test_candidate_score_rejects_unrelated_and_accepts_target_like_group(self):
        good = score_candidate(
            username="hediyecekikuponsatisi",
            title="Hediye Çeki Kupon Alım Satım Grubu",
            members=1800,
            days_inactive=0,
            unique_senders=7,
            existing_targets=["kuponsat", "kupongrupta"],
        )
        bad = score_candidate(
            username="coinairdrop",
            title="Kripto Airdrop Referans",
            members=20000,
            days_inactive=0,
            unique_senders=20,
            existing_targets=["kuponsat"],
        )
        self.assertTrue(good["eligible"])
        self.assertGreaterEqual(good["score"], 45)
        self.assertFalse(bad["eligible"])

    def test_candidate_is_not_renotified_and_sources_are_merged(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {"FIREBASE_API_KEY": ""}
        ):
            registry = TargetRegistry(Path(directory) / "registry.json")
            first, is_new = registry.register_candidate({
                "username": "@KuponYeniPazar",
                "title": "Kupon Yeni Pazar",
                "score": 70,
                "sources": ["telegram_search"],
            })
            second, is_new_again = registry.register_candidate({
                "username": "kuponyenipazar",
                "sources": ["historical_report"],
            })
            self.assertTrue(is_new)
            self.assertFalse(is_new_again)
            self.assertEqual(first["status"], "pending")
            self.assertEqual(
                set(second["sources"]), {"telegram_search", "historical_report"}
            )

    def test_batch_approval_becomes_shared_target_and_rejection_stays_closed(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {"FIREBASE_API_KEY": ""}
        ):
            registry = TargetRegistry(Path(directory) / "registry.json")
            for name in ("kuponadaybir", "kuponadayiki"):
                registry.register_candidate({"username": name, "score": 70})
            batch_id, rows = registry.create_batch(
                ["kuponadaybir", "kuponadayiki"], "KeyVadiOnline"
            )
            self.assertEqual(len(rows), 2)
            registry.apply_batch_decision(batch_id, [1], "approved", 123)
            registry.apply_batch_decision(batch_id, [2], "rejected", 123)
            self.assertEqual(registry.approved_groups(), {"kuponadaybir"})
            _, repeated = registry.register_candidate({"username": "kuponadayiki"})
            self.assertFalse(repeated)

    def test_dynamic_approved_groups_are_in_main_publisher_targets(self):
        fake_registry = mock.Mock()
        fake_registry.approved_groups.return_value = {"dinamikkuponpazari"}
        with mock.patch.object(publisher, "TARGET_REGISTRY", fake_registry), mock.patch.object(
            publisher, "get_list", return_value=set()
        ):
            targets = publisher.get_all_protected_groups()
        self.assertIn("dinamikkuponpazari", targets)

    def test_timed_write_restriction_is_temporary_and_explainable(self):
        until = datetime.now(timezone.utc) + timedelta(hours=2)
        participant = SimpleNamespace(
            banned_rights=SimpleNamespace(send_messages=True, until_date=until)
        )

        class FakeClient:
            async def __call__(self, _request):
                return SimpleNamespace(participant=participant)

        entity = SimpleNamespace(default_banned_rights=None)
        detail = asyncio.run(publisher.inspect_write_forbidden(FakeClient(), entity))
        self.assertEqual(detail["scope"], "account")
        self.assertEqual(detail["reason"], "AccountWriteRestricted")
        self.assertGreater(detail["retry_after"], 60 * 60)
        self.assertIsNotNone(detail["until"])


class SmmSharedTargetsTests(unittest.TestCase):
    def test_smm_target_list_includes_shared_approvals(self):
        repo = Path(__file__).resolve().parents[1] / "smm-bot-repo"
        sys.path.insert(0, str(repo))
        try:
            import smm_reklam

            with mock.patch.object(
                smm_reklam, "shared_approved_groups", return_value={"ortakdinamikgrup"}
            ):
                targets = smm_reklam.groups_from_env()
            self.assertIn("ortakdinamikgrup", targets)
        finally:
            sys.path.remove(str(repo))


class DiscoverySafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_registers_and_notifies_but_never_joins(self):
        now = datetime.now(timezone.utc)
        chat = Channel(
            id=987654321,
            title="Yeni Kupon Kod Satış Pazarı",
            photo=None,
            date=now,
            megagroup=True,
            broadcast=False,
            username="yenikuponkodsatis",
            participants_count=1400,
        )
        messages = [
            SimpleNamespace(date=now, sender_id=index, raw_text="kupon arıyorum")
            for index in range(1, 6)
        ]

        class FakeClient:
            def __init__(self):
                self.requests = []
                self.sent = []

            async def __call__(self, request):
                self.requests.append(type(request).__name__)
                return SimpleNamespace(chats=[chat])

            async def get_messages(self, _chat, limit=5):
                return messages[:limit]

            async def send_message(self, target, message):
                self.sent.append((target, message))

        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {"FIREBASE_API_KEY": "", "DISCOVERY_QUERY_LIMIT": "20"}
        ):
            registry = TargetRegistry(Path(directory) / "registry.json")
            client = FakeClient()
            with mock.patch.object(publisher, "TARGET_REGISTRY", registry), mock.patch.object(
                publisher, "generate_discovery_queries", return_value=["kupon kod satış"]
            ), mock.patch.object(
                publisher, "seed_discovery_candidates", return_value=[]
            ), mock.patch.object(
                publisher, "get_list", return_value=set()
            ), mock.patch.object(
                publisher, "save_to_list"
            ), mock.patch.object(
                publisher, "update_stats"
            ), mock.patch.object(
                publisher.asyncio, "sleep", new=mock.AsyncMock()
            ):
                found = await publisher.auto_scrape_groups(client, "KeyVadiOnline", set())

            self.assertEqual(found, 1)
            self.assertEqual(client.requests, ["SearchRequest"])
            self.assertTrue(client.sent)
            self.assertEqual(registry.approved_groups(), set())
            data = registry.load(prefer_remote=False)
            self.assertEqual(
                data["candidates"]["yenikuponkodsatis"]["status"], "pending"
            )


if __name__ == "__main__":
    unittest.main()
