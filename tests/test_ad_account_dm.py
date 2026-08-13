import unittest
from unittest.mock import AsyncMock, patch

import otomatik_katil as publisher


class AdAccountDmTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        publisher.USER_DM_PRODUCT_REPLY_TIME.clear()

    def test_froxy_and_keyvadi_ad_accounts_own_direct_messages(self):
        self.assertTrue(publisher.ad_worker_dm_replies_enabled("FroxyOnline"))
        self.assertTrue(publisher.ad_worker_dm_replies_enabled("KeyVadiOnline"))
        self.assertFalse(publisher.ad_worker_dm_replies_enabled("LisansArenaOnline"))

    async def test_same_product_is_sent_once_per_fifteen_minutes(self):
        product = {"id": "42", "title": "ChatGPT Plus", "url": "https://example.com/42"}
        with patch.object(publisher, "async_get_document", new=AsyncMock(return_value=None)):
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
        self.assertEqual(after_fifteen_minutes, [product])

    async def test_different_product_can_reply_without_waiting(self):
        first_product = {"id": "1", "title": "ChatGPT Plus"}
        second_product = {"id": "2", "title": "Gemini Pro"}
        with patch.object(publisher, "async_get_document", new=AsyncMock(return_value=None)):
            first, _ = await publisher.reserve_product_dm_replies(
                "FroxyOnline", 123, [first_product], now=1000
            )
            second, _ = await publisher.reserve_product_dm_replies(
                "FroxyOnline", 123, [second_product], now=1001
            )

        self.assertEqual(first, [first_product])
        self.assertEqual(second, [second_product])


if __name__ == "__main__":
    unittest.main()
