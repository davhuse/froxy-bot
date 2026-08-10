"""Distributed ownership for the single Render Telegram runtime."""

from __future__ import annotations

import asyncio
import os
import socket
import uuid

import firestore_helper


class RuntimeLease:
    def __init__(self, document_id="telegram_runtime_main", ttl_seconds=120):
        self.document_id = document_id
        self.ttl_seconds = int(ttl_seconds)
        identity = (
            os.environ.get("RENDER_INSTANCE_ID")
            or os.environ.get("RENDER_SERVICE_ID")
            or socket.gethostname()
        )
        self.owner_id = f"{identity}:{os.getpid()}:{uuid.uuid4().hex}"
        self.acquired = False

    @property
    def disabled(self):
        """Allow the explicitly selected production owner to bypass a stale lease."""
        return os.environ.get("DISABLE_RUNTIME_LEASE", "").strip().lower() in {
            "1", "true", "yes", "on"
        }

    async def acquire(self):
        if self.disabled:
            self.acquired = True
            return True
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            firestore_helper.acquire_lease,
            self.document_id,
            self.owner_id,
            self.ttl_seconds,
        )
        self.acquired = result is True
        return self.acquired

    async def heartbeat(self, stop_event, interval_seconds=30):
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except asyncio.TimeoutError:
                pass
            if not await self.acquire():
                print("[RuntimeLease] Lease renewal failed; Telegram runtime is stopping.", flush=True)
                stop_event.set()
                return

    async def release(self):
        if self.disabled:
            self.acquired = False
            return True
        if not self.acquired:
            return True
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            firestore_helper.release_lease,
            self.document_id,
            self.owner_id,
        )
        if result is True:
            self.acquired = False
        return result
