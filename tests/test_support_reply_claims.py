import unittest
from unittest.mock import patch

import firestore_helper
import support_flow


class SupportReplyClaimTests(unittest.IsolatedAsyncioTestCase):
    async def test_customer_reply_claim_fails_closed_without_remote_store(self):
        with patch.object(firestore_helper, "claim_remote_document", return_value=None):
            self.assertTrue(await support_flow.claim_support_event("KeyVadi", 42, 9999, "product_card"))
            self.assertFalse(await support_flow.claim_support_event("KeyVadi", 42, 9999, "product_card"))

    async def test_customer_reply_claim_is_one_time_per_event(self):
        calls = []

        def claim(doc_id, fields):
            calls.append((doc_id, fields))
            return len(calls) == 1

        with patch.object(firestore_helper, "claim_remote_document", side_effect=claim):
            self.assertTrue(await support_flow.claim_support_event("Froxy AI", 42, 1001, "product_card"))
            self.assertFalse(await support_flow.claim_support_event("Froxy AI", 42, 1001, "product_card"))
        self.assertIn("support_reply_froxy_ai_42_1001_product_card", calls[0][0])


if __name__ == "__main__":
    unittest.main()
