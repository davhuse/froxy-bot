import unittest

from customer_intent import (
    INTENT_AFTER_SALES,
    INTENT_DELIVERY_PROBLEM,
    INTENT_PAYMENT_QUESTION,
    INTENT_SALES_LEAD,
    classify_customer_message,
)


class CustomerIntentTests(unittest.TestCase):
    def test_product_name_is_sales_lead(self):
        self.assertEqual(classify_customer_message("youtube"), INTENT_SALES_LEAD)
        self.assertEqual(classify_customer_message("Chat GBT plas fiyatı"), INTENT_SALES_LEAD)

    def test_delivery_problem_wins_over_product_match(self):
        self.assertEqual(
            classify_customer_message("youtube kodu çalışmıyor", product_matched=True),
            INTENT_DELIVERY_PROBLEM,
        )

    def test_payment_and_after_sales_are_separate(self):
        self.assertEqual(classify_customer_message("bakiye yansımadı"), INTENT_DELIVERY_PROBLEM)
        self.assertEqual(classify_customer_message("IBAN var mı"), INTENT_PAYMENT_QUESTION)
        self.assertEqual(
            classify_customer_message("tamam geldi sağol", has_sales_context=True),
            INTENT_AFTER_SALES,
        )


if __name__ == "__main__":
    unittest.main()
