import unittest
from unittest.mock import patch

import supplier_opportunities as suppliers


class SupplierOpportunityTests(unittest.TestCase):
    def test_catalog_urls_and_capital_limit(self):
        catalog = suppliers.load_opportunities()
        self.assertEqual(len(catalog["opportunities"]), 8)
        self.assertTrue(all(suppliers.validate_opportunity(row) for row in catalog["opportunities"]))
        with self.assertRaises(ValueError):
            suppliers.create_procurement_request("itemsatis-discord-14boost-30d", "customer", 3)

    def test_manual_approval_requires_fresh_stock_and_price(self):
        rows = []
        with patch.object(suppliers, "_read_queue", side_effect=lambda: rows), patch.object(
            suppliers, "_write_queue", side_effect=lambda value: rows.__setitem__(slice(None), value)
        ):
            created = suppliers.create_procurement_request(
                "itemsatis-capcut-shared-30d", "customer", 1
            )
            with self.assertRaises(ValueError):
                suppliers.update_procurement_request(created["id"], action="approve")
            verified = suppliers.update_procurement_request(
                created["id"], action="verify", observed_unit_cost_cents=1288,
                stock_available=True,
            )
            self.assertEqual(verified["status"], "verified_waiting_admin")
            approved = suppliers.update_procurement_request(created["id"], action="approve")
            self.assertEqual(approved["status"], "manual_purchase_approved")


if __name__ == "__main__":
    unittest.main()
