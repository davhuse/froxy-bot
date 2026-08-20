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


if __name__ == "__main__":
    unittest.main()
