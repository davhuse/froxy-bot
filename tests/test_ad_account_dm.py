import unittest
from unittest.mock import AsyncMock, patch

import otomatik_katil as publisher


class AdAccountDmTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        publisher.USER_DM_PRODUCT_REPLY_TIME.clear()

    def test_froxy_and_keyvadi_ad_accounts_own_direct_messages(self):
        self.assertTrue(publisher.ad_worker_dm_replies_enabled("FroxyOnline"))
        self.assertTrue(publisher.ad_worker_dm_replies_enabled("KeyVadiOnline"))
        self.assertTrue(publisher.ad_worker_dm_replies_enabled("LisansArenaOnline"))

    async def test_same_product_is_sent_once_per_private_chat(self):
        product = {"id": "42", "title": "ChatGPT Plus", "url": "https://example.com/42"}
        with patch.object(publisher, "async_claim_document", new=AsyncMock(return_value=True)):
            first, _first_keys = await publisher.reserve_product_dm_replies(
                "KeyVadiOnline", 123, [product], now=1000
            )
            repeated, _repeated_keys = await publisher.reserve_product_dm_replies(
                "KeyVadiOnline", 123, [product], now=1001
            )
            after_fifteen_minutes, _later_keys = await publisher.reserve_product_dm_replies(
                "KeyVadiOnline", 123, [product], now=1901
            )

        self.assertEqual(first, [product])
        self.assertEqual(repeated, [])
        self.assertEqual(after_fifteen_minutes, [])

    async def test_different_product_can_reply_without_waiting(self):
        first_product = {"id": "1", "title": "ChatGPT Plus"}
        second_product = {"id": "2", "title": "Gemini Pro"}
        with patch.object(publisher, "async_claim_document", new=AsyncMock(return_value=True)):
            first, _ = await publisher.reserve_product_dm_replies(
                "FroxyOnline", 123, [first_product], now=1000
            )
            second, _ = await publisher.reserve_product_dm_replies(
                "FroxyOnline", 123, [second_product], now=1001
            )

        self.assertEqual(first, [first_product])
        self.assertEqual(second, [second_product])

    async def test_followup_reply_has_one_durable_conversation_claim(self):
        with patch.object(publisher, "async_claim_document", new=AsyncMock(return_value=True)) as claim:
            first = await publisher.claim_customer_auto_reply("FroxyOnline", 123, 123, "generic")
            self.assertTrue(first)
            claim.return_value = False
            second = await publisher.claim_customer_auto_reply("FroxyOnline", 123, 123, "generic")
        self.assertIsNone(second)

    async def test_dm_event_fails_closed_without_durable_claim(self):
        publisher.PROCESSED_DM_MSG_IDS.clear()
        with patch.object(
            publisher, "async_claim_document", new=AsyncMock(return_value=None)
        ):
            claim = await publisher.claim_dm_reply_event("FroxyOnline", 123, 99)
        self.assertIsNone(claim)
        self.assertNotIn(("FroxyOnline", 123, 99), publisher.PROCESSED_DM_MSG_IDS)

    def test_null_context_product_is_safe(self):
        self.assertEqual(publisher.context_product_title({"products": [None]}), "")
        self.assertEqual(
            publisher.context_product_title({"products": [None, {"title": "Office"}]}),
            "Office",
        )

    def test_froxy_product_reply_uses_direct_shopier_listing(self):
        reply = publisher.froxy_product_reply({
            "id": "49489691",
            "title": "ChatGPT Plus 30 Gün - Kişisel",
            "price": "499,99 TL",
            "url": "https://www.shopier.com/froxyai/49489691",
        })
        self.assertIn("499,90 TL", reply)
        self.assertIn("https://www.shopier.com/froxyai/49489691", reply)
        self.assertNotIn("/go/", reply)


if __name__ == "__main__":
    unittest.main()
