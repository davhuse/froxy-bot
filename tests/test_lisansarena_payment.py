import unittest
from unittest import mock
from pathlib import Path

from lisansarena_payment import (
    IBAN_DISPLAY,
    IBAN_RECIPIENT,
    PaymentSessionStore,
    build_payment_message,
)


class LisansArenaPaymentTests(unittest.TestCase):
    def test_message_contains_product_iban_recipient_and_order_code(self):
        text = build_payment_message(
            {"title": "Windows 11 Pro", "price": "70 TL"},
            "LA-A1B2C3",
        )
        self.assertIn("Windows 11 Pro", text)
        self.assertIn("70 TL", text)
        self.assertIn(IBAN_DISPLAY, text)
        self.assertIn(IBAN_RECIPIENT, text)
        self.assertIn("LA-A1B2C3", text)
        self.assertNotIn("Shopier", text)
        self.assertIn("manuel", text)

    def test_same_customer_and_product_reuses_short_code(self):
        store = PaymentSessionStore()
        with mock.patch("lisansarena_payment.secrets.token_hex", return_value="a1b2c3"):
            first = store.get_or_create(42, "product-1", now=100)
            second = store.get_or_create(42, "product-1", now=200)
        self.assertEqual("LA-A1B2C3", first["code"])
        self.assertEqual(first["code"], second["code"])

    def test_different_product_gets_different_order_code(self):
        store = PaymentSessionStore()
        with mock.patch(
            "lisansarena_payment.secrets.token_hex",
            side_effect=["a1b2c3", "d4e5f6"],
        ):
            first = store.get_or_create(42, "product-1", now=100)
            second = store.get_or_create(42, "product-2", now=100)
        self.assertNotEqual(first["code"], second["code"])

    def test_bot_has_no_public_shopier_checkout_or_auto_delivery(self):
        source = Path("lisansarena_bot.py").read_text(encoding="utf-8")
        self.assertNotIn("https://www.shopier.com", source)
        self.assertNotIn("Button.url", source)
        self.assertNotIn("Ödemeniz Başarıyla Doğrulandı", source)

    def test_mini_app_uses_inline_webview_markup(self):
        source = Path("lisansarena_bot.py").read_text(encoding="utf-8")
        self.assertIn("ReplyInlineMarkup", source)
        self.assertIn("KeyboardButtonWebView", source)
        self.assertNotIn("ReplyKeyboardMarkup", source)
        self.assertIn("setChatMenuButton", source)
        self.assertIn("ButtonTypeInvalidError", source)

    def test_all_customer_commands_are_registered_and_have_handlers(self):
        source = Path("lisansarena_bot.py").read_text(encoding="utf-8")
        commands = (
            "start", "magaza", "urunler", "bakiye", "siparisler",
            "hesaplar", "gecmis", "kullanim", "talep", "destek",
            "iade", "referans", "cekilis", "ayarlar", "dil", "yardim",
        )
        for command in commands:
            self.assertIn(f'(\"{command}\",', source)
        self.assertIn("setMyCommands", source)
        self.assertIn("setMyDescription", source)
        self.assertIn("setMyProfilePhoto", source)
        self.assertIn('attach://profile_photo', source)
        self.assertIn('lisansarena_logo_v2.jpg', source)


if __name__ == "__main__":
    unittest.main()
