# -*- coding: utf-8 -*-
"""Unit tests for automatic license stock allocation and category matching."""

import unittest
from unittest.mock import patch
import license_delivery


class TestLicenseDelivery(unittest.TestCase):
    def test_resolve_category(self):
        self.assertEqual("canva", license_delivery.resolve_category("Canva Pro 1 Yıllık"))
        self.assertEqual("adobe", license_delivery.resolve_category("Adobe Creative Cloud Tüm Uygulamalar"))
        self.assertEqual("windows", license_delivery.resolve_category("Windows 11 Pro Orijinal Lisans"))
        self.assertEqual("office", license_delivery.resolve_category("Microsoft 365 Pro Plus Hesap"))
        self.assertEqual("netflix", license_delivery.resolve_category("Netflix 4K Ultra HD Özel Profil"))
        self.assertEqual("steam", license_delivery.resolve_category("Steam VIP Random Key (100-1000 TL)"))
        self.assertEqual("minecraft", license_delivery.resolve_category("Minecraft Founder Pelerin Kodu"))
        self.assertEqual("capcut", license_delivery.resolve_category("CapCut Pro 1 Yıllık Lisans"))
        self.assertEqual("roblox", license_delivery.resolve_category("Roblox 2010 Offsale Hesap"))
        self.assertIsNone(license_delivery.resolve_category("Bilinmeyen Rastgele Hizmet"))

    def test_allocate_license_success(self):
        fake_stock = {"canva": ["CANVA-TEST-KEY-12345"]}
        with patch.object(license_delivery, "load_licenses_stock", return_value=fake_stock), \
             patch.object(license_delivery, "save_licenses_stock") as mock_save:
            res = license_delivery.allocate_license("Canva Pro 1 Yıllık")
            self.assertTrue(res["allocated"])
            self.assertEqual("CANVA-TEST-KEY-12345", res["license_key"])
            self.assertEqual("delivered", res["status"])
            mock_save.assert_called_once()

    def test_allocate_license_empty_stock(self):
        fake_stock = {"canva": []}
        with patch.object(license_delivery, "load_licenses_stock", return_value=fake_stock), \
             patch.object(license_delivery, "save_licenses_stock") as mock_save:
            res = license_delivery.allocate_license("Canva Pro 1 Yıllık")
            self.assertFalse(res["allocated"])
            self.assertIsNone(res["license_key"])
            self.assertEqual("pending_delivery", res["status"])
            mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
