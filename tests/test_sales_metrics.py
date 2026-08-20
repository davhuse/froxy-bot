import json
import os
import tempfile
import unittest
from unittest.mock import patch

import sales_metrics


class SalesMetricsTests(unittest.TestCase):
    def test_account_names_and_unique_conversations_are_merged(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"SALES_METRICS_FILE": os.path.join(directory, "events.jsonl"), "METRICS_HASH_SECRET": "test"},
        ), patch.object(sales_metrics, "_queue_durable_event"), patch.object(
            sales_metrics, "_read_durable_events", return_value=[]
        ):
            sales_metrics.record_dm_event("KeyVadiOnline", 42, "Netflix", message_id=1)
            sales_metrics.record_dm_event("KeyVadi", 42, "fiyatı nedir", message_id=2)
            sales_metrics.record_dm_event("Froxy AI", 99, "kod çalışmıyor", message_id=3)
            summary = sales_metrics.summarize(1)
        self.assertIn("keyvadi", summary["by_account"])
        self.assertNotIn("KeyVadiOnline", summary["by_account"])
        self.assertEqual(summary["funnel"]["raw_dm_received"], 3)
        self.assertEqual(summary["funnel"]["unique_conversations"], 2)
        self.assertEqual(summary["funnel"]["qualified_leads"], 1)
        self.assertEqual(summary["dm_classes"]["delivery_problem"], 1)

    def test_summary_excludes_events_before_release_baseline(self):
        events = [
            {"event_id": "old", "ts": "2026-08-20T15:59:59+00:00", "kind": "ad_sent", "account": "keyvadi"},
            {"event_id": "new", "ts": "2026-08-20T16:00:01+00:00", "kind": "ad_sent", "account": "keyvadi"},
        ]
        with patch.dict(os.environ, {"SALES_METRICS_BASELINE_AT": "2026-08-20T16:00:00+00:00"}), patch.object(
            sales_metrics, "_read_durable_events", return_value=events
        ), patch.object(sales_metrics, "read_events", return_value=[]):
            summary = sales_metrics.summarize(7)
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["funnel"]["ad_sent"], 1)
        self.assertEqual(summary["baseline_at"], "2026-08-20T16:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
