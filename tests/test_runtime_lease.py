import asyncio
import unittest
from unittest.mock import patch

from runtime_lease import RuntimeLease


class RuntimeLeaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_owner_cannot_acquire_active_lease(self):
        owners = {}

        def acquire(document_id, owner_id, _ttl):
            current = owners.get(document_id)
            if current not in (None, owner_id):
                return False
            owners[document_id] = owner_id
            return True

        first = RuntimeLease("test-runtime")
        second = RuntimeLease("test-runtime")
        with patch("runtime_lease.firestore_helper.acquire_lease", side_effect=acquire):
            self.assertTrue(await first.acquire())
            self.assertFalse(await second.acquire())

    async def test_heartbeat_stops_runtime_when_renewal_is_lost(self):
        lease = RuntimeLease("test-runtime")
        stop_event = asyncio.Event()
        with patch.object(lease, "acquire", return_value=False):
            await lease.heartbeat(stop_event, interval_seconds=0.001)
        self.assertTrue(stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
