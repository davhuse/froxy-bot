import os
import tempfile
import unittest
from unittest.mock import patch

import firestore_helper


class FirestoreFallbackTests(unittest.TestCase):
    def test_claim_uses_local_atomic_store_when_firestore_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"RUNTIME_CLAIM_DB": os.path.join(directory, "claims.db")}
        ), patch.object(firestore_helper, "_commit", return_value=None):
            self.assertTrue(firestore_helper.claim_document("product-1", {"brand": "keyvadi"}))
            self.assertFalse(firestore_helper.claim_document("product-1", {"brand": "keyvadi"}))
            self.assertEqual(firestore_helper.get_document("product-1")["brand"], "keyvadi")

    def test_local_claim_can_be_released_after_a_send_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"RUNTIME_CLAIM_DB": os.path.join(directory, "claims.db")}
        ), patch.object(firestore_helper, "_commit", return_value=None):
            self.assertTrue(firestore_helper.claim_document("product-2", {"brand": "froxy"}))
            self.assertTrue(firestore_helper.delete_document("product-2"))
            self.assertTrue(firestore_helper.claim_document("product-2", {"brand": "froxy"}))


if __name__ == "__main__":
    unittest.main()
