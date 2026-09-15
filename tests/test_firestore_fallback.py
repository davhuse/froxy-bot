import os
import tempfile
import unittest
from unittest.mock import patch

import firestore_helper


class FirestoreFallbackTests(unittest.TestCase):
    def test_missing_remote_credentials_never_call_live_firestore(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {
                "FIREBASE_SERVICE_ACCOUNT_JSON": "",
                "RUNTIME_CLAIM_DB": os.path.join(directory, "claims.db"),
            }
        ), patch.object(firestore_helper, "API_KEY", ""), patch.object(
            firestore_helper, "_request", side_effect=AssertionError("live Firestore request")
        ):
            self.assertFalse(firestore_helper.remote_credentials_configured())
            self.assertEqual(
                firestore_helper.health_check()["status"], "missing_credentials"
            )
            self.assertTrue(firestore_helper.set_document("local-test", {"ok": True}))
            self.assertEqual(firestore_helper.get_document("local-test"), {"ok": True})
            self.assertIsNone(firestore_helper.claim_remote_document("remote-test"))

    def test_nested_orders_are_encoded_as_real_firestore_maps_and_arrays(self):
        source = {"users": {"42": {"balance": 10.5, "orders": [{"id": "KV-1"}]}}}
        encoded = firestore_helper._fields_to_firestore(source)
        decoded = {
            key: firestore_helper._value_from_firestore(value)
            for key, value in encoded.items()
        }
        self.assertEqual(decoded, source)

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

    def test_local_runtime_lease_renews_when_firestore_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"RUNTIME_CLAIM_DB": os.path.join(directory, "claims.db")}
        ), patch.object(firestore_helper, "get_document_with_meta", return_value=(None, None)), patch.object(
            firestore_helper, "_commit", return_value=None
        ):
            self.assertTrue(firestore_helper.acquire_lease("runtime", "owner-a", ttl_seconds=120))
            self.assertTrue(firestore_helper.acquire_lease("runtime", "owner-a", ttl_seconds=120))
            self.assertFalse(firestore_helper.acquire_lease("runtime", "owner-b", ttl_seconds=120))


if __name__ == "__main__":
    unittest.main()
