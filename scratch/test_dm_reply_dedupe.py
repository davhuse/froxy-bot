import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import otomatik_katil as automation


class DmReplyDedupeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        automation.PROCESSED_DM_MSG_IDS.clear()
        automation.USER_DM_SALES_CONTEXT.clear()

    async def test_concurrent_handlers_only_claim_once_locally(self):
        with patch.object(
            automation, "async_claim_document", AsyncMock(return_value=True)
        ) as remote_claim:
            results = await asyncio.gather(
                automation.claim_dm_reply_event("KeyVadiOnline", 123, 456),
                automation.claim_dm_reply_event("KeyVadiOnline", 123, 456),
            )

        self.assertEqual(sorted(results), [False, True])
        remote_claim.assert_awaited_once()

    async def test_existing_cross_process_claim_is_rejected(self):
        with patch.object(
            automation, "async_claim_document", AsyncMock(return_value=False)
        ):
            claimed = await automation.claim_dm_reply_event(
                "KeyVadiOnline", 987, 654
            )

        self.assertFalse(claimed)

    def test_sales_context_expires_after_fifteen_minutes(self):
        key = ("KeyVadiOnline", 123)
        product = {
            "title": "ChatGPT Plus (1 Aylık Hesap)",
            "price": "299,90 TL",
            "url": "https://example.invalid/product",
        }
        automation.remember_sales_context(key, [product], now=1000)

        self.assertIsNotNone(automation.active_sales_context(key, now=1899))
        self.assertIsNone(automation.active_sales_context(key, now=1901))

    def test_followup_uses_catalog_facts_without_inventing_guarantee(self):
        context = {
            "products": [{
                "title": "ChatGPT Plus (1 Aylık Hesap)",
                "price": "299,90 TL",
                "url": "https://example.invalid/product",
            }]
        }

        price_reply = automation.sales_followup_reply(context, "Fiyatı ne kadar?")
        guarantee_reply = automation.sales_followup_reply(context, "Garantisi var mı?")

        self.assertIn("299,90 TL", price_reply)
        self.assertIn("https://example.invalid/product", price_reply)
        self.assertIn("Yanlış bilgi vermemek", guarantee_reply)
        self.assertNotIn("garantilidir", guarantee_reply.lower())

    def test_keyvadi_reply_contains_verified_trust_routes(self):
        reply = automation.keyvadi_product_reply({
            "title": "Test",
            "url": "https://example.invalid/product",
        })

        self.assertIn("Shopier", reply)
        self.assertIn("satisrefim/9615", reply)


if __name__ == "__main__":
    unittest.main()
