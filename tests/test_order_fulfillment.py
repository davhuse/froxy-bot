# -*- coding: utf-8 -*-
"""Unit tests for order fulfillment module. Strictly zero emojis."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from order_fulfillment import (
    extract_email,
    extract_order_id,
    fulfill_order_request,
    is_auto_delivery_product,
)


class TestOrderFulfillment(unittest.TestCase):
    def test_auto_delivery_categorization(self):
        # Auto delivery products
        self.assertTrue(is_auto_delivery_product("Windows 11 Pro Lisans"))
        self.assertTrue(is_auto_delivery_product("Office 365 ProPlus Hesap"))
        self.assertTrue(is_auto_delivery_product("Steam VIP Random Key"))
        self.assertTrue(is_auto_delivery_product("TikTak 1000 TL Kupon"))
        self.assertTrue(is_auto_delivery_product("Telegram Oto-Reklam & Mesaj Botu Scripti"))
        self.assertTrue(is_auto_delivery_product("JarvisCraft Haftalik VIP Uyelik"))
        self.assertTrue(is_auto_delivery_product("JarvisCraft Aylik Sinirsiz VIP Uyelik"))
        self.assertTrue(is_auto_delivery_product("E-Ticaret & Fiyat Takip Scraper Botu"))

        # Non-auto products (require email / personal invite)
        self.assertFalse(is_auto_delivery_product("Canva Pro (1 Yillik Yetki)"))
        self.assertFalse(is_auto_delivery_product("Canva Pro Ogretmen 1 Yil"))
        self.assertFalse(is_auto_delivery_product("Duolingo Super 12 Ay - Kendi Hesabina Aktivasyon"))
        self.assertFalse(is_auto_delivery_product("Gemini Pro 18 Ay Indirim Baglantisi"))
        self.assertFalse(is_auto_delivery_product("KeyVadi Cuzdan Bakiye Yukleme (70.00 TL)"))

    def test_extract_order_id(self):
        self.assertEqual(extract_order_id("Siparis no 720325449 aldim"), "720325449")
        self.assertEqual(extract_order_id("720325449"), "720325449")
        self.assertEqual(extract_order_id("Siparis numaram: 337297639"), "337297639")
        self.assertIsNone(extract_order_id("Merhaba nasilsiniz"))
        self.assertIsNone(extract_order_id("12345"))

    def test_extract_email(self):
        self.assertEqual(
            extract_email("Mailim emirhan@gmail.com tanimlar misiniz"),
            "emirhan@gmail.com",
        )
        self.assertEqual(extract_email("user.test@domain.com.tr"), "user.test@domain.com.tr")
        self.assertIsNone(extract_email("sadece duz metin"))

    def test_fulfill_auto_delivery_with_stock(self):
        mock_order = {
            "order_id": "999888777",
            "brand": "keyvadi",
            "product_name": "Steam VIP Random Key",
            "amount": "29.90",
            "payment_status": "paid",
            "buyer_name": "Test User",
            "buyer_email": "test@user.com",
            "buyer_phone": "+905550000000",
            "note": "",
        }
        mock_alloc = {
            "allocated": True,
            "license_key": "STEAM-TEST-KEY-12345",
            "activation_guide": "Steam uygulamasinda kod kullan alanina giriniz.",
            "redeem_url": None,
        }
        with patch("order_fulfillment.fetch_shopier_order", return_value=mock_order), \
             patch("order_fulfillment.allocate_license", return_value=mock_alloc):
            res = asyncio.run(fulfill_order_request("999888777", tg_user_id=123456))
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "delivered")
            self.assertIn("SIPARIS ONAYLANDI - OTO TESLIMAT", res["message"])
            self.assertIn("STEAM-TEST-KEY-12345", res["message"])
            self.assertIn("999888777", res["message"])

    def test_fulfill_non_auto_delivery_with_email(self):
        mock_order = {
            "order_id": "720325449",
            "brand": "keyvadi",
            "product_name": "Canva Pro (1 Yillik Yetki)",
            "amount": "49.90",
            "payment_status": "paid",
            "buyer_name": "Emirhan Algan",
            "buyer_email": "emirhangemini44@gmail.com",
            "buyer_phone": "+905330000000",
            "note": "",
        }
        with patch("order_fulfillment.fetch_shopier_order", return_value=mock_order):
            res = asyncio.run(fulfill_order_request("720325449", tg_user_id=123456))
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "email_confirmed")
            self.assertIn("emirhangemini44@gmail.com", res["message"])
            self.assertIn("720325449", res["message"])

    def test_fulfill_non_auto_delivery_needs_email(self):
        mock_order = {
            "order_id": "720325449",
            "brand": "keyvadi",
            "product_name": "Canva Pro (1 Yillik Yetki)",
            "amount": "49.90",
            "payment_status": "paid",
            "buyer_name": "Emirhan Algan",
            "buyer_email": "",
            "buyer_phone": "+905330000000",
            "note": "",
        }
        with patch("order_fulfillment.fetch_shopier_order", return_value=mock_order):
            res = asyncio.run(fulfill_order_request("720325449", tg_user_id=123456))
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "email_needed")
            self.assertIn("kayitli E-Posta adresinizi buraya yaziniz", res["message"])


if __name__ == "__main__":
    unittest.main()
