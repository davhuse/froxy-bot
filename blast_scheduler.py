"""Durable, single-owner scheduling for the three advertising accounts.

The Telegram clients still keep independent connections and DM handlers, but
only the account selected here may run a group-ad blast.  Every group and its
template are checkpointed before Telegram is called so a deploy can resume the
same cycle without treating a partial blast as complete.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import uuid


ACCOUNT_ORDER = ("KeyVadiOnline", "FroxyOnline", "LisansArenaOnline")
TERMINAL_TARGET_STATES = {
    "accepted", "failed", "skipped", "skipped_uncertain",
}


def is_recent_message_from_account(message, account_id, now=None, window_seconds=3600):
    """Return whether Telegram already contains this account's recent message.

    This guards against duplicate ads when a deploy loses the local blast
    checkpoint before the remote state store is available.
    """
    if not message or getattr(message, "empty", False):
        return False
    if getattr(message, "sender_id", None) != int(account_id or 0):
        return False
    message_date = getattr(message, "date", None)
    if message_date is None:
        return False
    if getattr(message_date, "tzinfo", None) is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    current = datetime.now(timezone.utc) if now is None else now
    if getattr(current, "tzinfo", None) is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current - message_date).total_seconds()
    return 0 <= age <= max(1, int(window_seconds))


def _now_iso(now: float | None = None) -> str:
    return datetime.fromtimestamp(now or time.time(), timezone.utc).isoformat()


def _timestamp(value, default=0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return float(default)


class BlastCoordinator:
    """Persist and serialize account-level blasts.

    ``remote`` may be disabled in tests/local development.  In production the
    state is mirrored to one Firestore document, while the JSON file remains a
    quick local recovery copy.
    """

    version = 3

    def __init__(
        self,
        path="blast_checkpoint_v3.json",
        *,
        remote=None,
        owner_id=None,
        now_fn=time.time,
    ):
        self.path = Path(path)
        self.owner_id = owner_id or f"{os.getpid()}-{uuid.uuid4().hex[:10]}"
        self.now_fn = now_fn
        self._lock = threading.RLock()
        self.remote = self._remote_available() if remote is None else bool(remote)
        self.state = self._load_best_state()

    @staticmethod
    def _remote_available() -> bool:
        return bool(
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            or os.environ.get("FIREBASE_API_KEY", "").strip()
        )

    def _empty_state(self):
        now = float(self.now_fn())
        return {
            "version": self.version,
            "updated_at": _now_iso(now),
            "active_account": None,
            "accounts": {
                account: {
                    "enabled": True,
                    "status": "waiting",
                    "due_at": now,
                    "cycle_number": 0,
                    "run_id": None,
                    "started_at": None,
                    "completed_at": None,
                    "cursor": 0,
                    "targets": [],
                    "pause_reason": None,
                }
                for account in ACCOUNT_ORDER
            },
        }

    @staticmethod
    def _valid_state(value):
        return (
            isinstance(value, dict)
            and int(value.get("version", 0) or 0) == 3
            and isinstance(value.get("accounts"), dict)
        )

    def _load_local(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if self._valid_state(value) else None
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None

    def _load_remote(self):
        if not self.remote:
            return None
        try:
            from firestore_helper import get_document

            document = get_document("blast_checkpoint_v3") or {}
            payload = document.get("payload")
            value = json.loads(payload) if isinstance(payload, str) else None
            return value if self._valid_state(value) else None
        except Exception:
            return None

    def _load_best_state(self):
        local = self._load_local()
        remote = self._load_remote()
        choices = [item for item in (local, remote) if item]
        if not choices:
            return self._empty_state()
        state = max(choices, key=lambda item: _timestamp(item.get("updated_at")))
        result = self._empty_state()
        result.update(deepcopy(state))
        result["version"] = self.version
        result.setdefault("active_account", None)
        result.setdefault("accounts", {})
        for account in ACCOUNT_ORDER:
            result["accounts"].setdefault(account, self._empty_state()["accounts"][account])
        return result

    def _persist(self):
        self.state["updated_at"] = _now_iso(float(self.now_fn()))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.path)
        if self.remote:
            try:
                from firestore_helper import set_document

                set_document("blast_checkpoint_v3", {
                    "payload": json.dumps(self.state, ensure_ascii=False),
                    "updated_at": self.state["updated_at"],
                    "active_account": self.state.get("active_account") or "",
                })
            except Exception:
                # Local durability must not be lost because cloud sync is
                # temporarily unavailable; the next transition retries it.
                pass

    def initialize_accounts(self, remaining_waits=None, enabled_accounts=None):
        """Seed due times without overwriting an in-progress V3 cycle."""
        with self._lock:
            waits = remaining_waits or {}
            enabled = set(enabled_accounts or ACCOUNT_ORDER)
            now = float(self.now_fn())
            changed = False
            for account in ACCOUNT_ORDER:
                record = self.state["accounts"][account]
                should_enable = account in enabled
                if record.get("enabled") != should_enable:
                    record["enabled"] = should_enable
                    changed = True
                if not should_enable:
                    record["status"] = "offline"
                    if self.state.get("active_account") == account:
                        self.state["active_account"] = None
                    continue
                if record.get("run_id") and record.get("targets"):
                    if record.get("status") in {"offline", "waiting", "completed"}:
                        record["status"] = "queued"
                        changed = True
                    continue
                desired_due = now + max(0, int(waits.get(account, 0) or 0))
                if not record.get("initialized_v3"):
                    record["due_at"] = desired_due
                    record["initialized_v3"] = True
                    record["status"] = "queued" if desired_due <= now else "waiting"
                    changed = True
            # The web process reads the local checkpoint for its status API.
            # When a fresh deploy restores an already-initialized state from
            # Firestore, no account field necessarily changes; materialize the
            # remote snapshot locally anyway so the panel and worker report the
            # same queue immediately after startup.
            if changed or not self.path.exists():
                self._persist()
            return self.snapshot()

    def _ready_accounts(self, now):
        ready = []
        for order, account in enumerate(ACCOUNT_ORDER):
            record = self.state["accounts"][account]
            if not record.get("enabled", True):
                continue
            due_at = float(record.get("due_at", 0) or 0)
            if due_at <= now:
                ready.append((due_at, order, account))
        return [item[2] for item in sorted(ready)]

    def try_acquire_turn(self, account, now=None):
        with self._lock:
            now = float(self.now_fn() if now is None else now)
            active = self.state.get("active_account")
            if active:
                return active == account
            ready = self._ready_accounts(now)
            if not ready or ready[0] != account:
                return False
            self.state["active_account"] = account
            record = self.state["accounts"][account]
            record["status"] = "preparing"
            record["pause_reason"] = None
            self._persist()
            return True

    def begin_cycle(self, account, targets, templates):
        with self._lock:
            if self.state.get("active_account") != account:
                raise RuntimeError(f"{account} does not own the blast turn")
            record = self.state["accounts"][account]
            existing = record.get("targets") or []
            if record.get("run_id") and any(
                item.get("state") not in TERMINAL_TARGET_STATES for item in existing
            ):
                record["status"] = "sending"
                self._persist()
                return deepcopy(record)

            ordered_targets = sorted({str(item).strip().lower().lstrip("@") for item in targets if item})
            available = [str(item) for item in templates if item]
            cycle_number = int(record.get("cycle_number", 0) or 0) + 1
            offset = (cycle_number - 1) % max(1, len(available))
            target_records = []
            for index, group in enumerate(ordered_targets):
                template = available[(offset + index) % len(available)] if available else ""
                target_records.append({
                    "index": index,
                    "group": group,
                    "template": template,
                    "state": "pending",
                    "attempt_owner": None,
                    "claimed_at": None,
                    "finished_at": None,
                    "message_id": None,
                    "reason": None,
                })
            record.update({
                "status": "sending",
                "cycle_number": cycle_number,
                "run_id": uuid.uuid4().hex,
                "started_at": _now_iso(float(self.now_fn())),
                "completed_at": None,
                "cursor": 0,
                "targets": target_records,
                "pause_reason": None,
            })
            self._persist()
            return deepcopy(record)

    def next_target(self, account):
        with self._lock:
            if self.state.get("active_account") != account:
                return None
            record = self.state["accounts"][account]
            targets = record.get("targets") or []
            changed = False
            for index, target in enumerate(targets):
                state = target.get("state", "pending")
                if state == "claimed" and target.get("attempt_owner") != self.owner_id:
                    # A previous process may have reached Telegram after its
                    # final checkpoint.  Skipping is safer than a duplicate ad.
                    target["state"] = "skipped_uncertain"
                    target["reason"] = "claimed_by_previous_process"
                    target["finished_at"] = _now_iso(float(self.now_fn()))
                    changed = True
                    continue
                if state == "pending" or (
                    state == "claimed" and target.get("attempt_owner") == self.owner_id
                ):
                    record["cursor"] = index
                    if changed:
                        self._persist()
                    return deepcopy(target)
            record["cursor"] = len(targets)
            if changed:
                self._persist()
            return None

    def claim_target(self, account, index):
        with self._lock:
            if self.state.get("active_account") != account:
                return None
            targets = self.state["accounts"][account].get("targets") or []
            if not 0 <= int(index) < len(targets):
                return None
            target = targets[int(index)]
            if target.get("state") != "pending":
                return None
            target.update({
                "state": "claimed",
                "attempt_owner": self.owner_id,
                "claimed_at": _now_iso(float(self.now_fn())),
            })
            self.state["accounts"][account]["cursor"] = int(index)
            self._persist()
            return deepcopy(target)

    def finish_target(self, account, index, status, *, message_id=None, reason=None):
        if status not in TERMINAL_TARGET_STATES:
            raise ValueError(f"Invalid target status: {status}")
        with self._lock:
            targets = self.state["accounts"][account].get("targets") or []
            target = targets[int(index)]
            target.update({
                "state": status,
                "finished_at": _now_iso(float(self.now_fn())),
                "message_id": message_id,
                "reason": reason,
            })
            self.state["accounts"][account]["cursor"] = min(int(index) + 1, len(targets))
            self._persist()
            return deepcopy(target)

    def defer_current(self, account, index, wait_seconds, reason):
        with self._lock:
            record = self.state["accounts"][account]
            targets = record.get("targets") or []
            if 0 <= int(index) < len(targets):
                target = targets[int(index)]
                if target.get("state") == "claimed" and target.get("attempt_owner") == self.owner_id:
                    target.update({
                        "state": "pending",
                        "attempt_owner": None,
                        "claimed_at": None,
                        "reason": reason,
                    })
            record["status"] = "paused"
            record["pause_reason"] = reason
            record["due_at"] = float(self.now_fn()) + max(1, int(wait_seconds or 1))
            self.state["active_account"] = None
            self._persist()

    def pause_account(self, account, wait_seconds, reason):
        """Release an account turn while preserving its current cycle."""
        with self._lock:
            record = self.state["accounts"][account]
            record["status"] = "paused"
            record["pause_reason"] = reason
            record["due_at"] = float(self.now_fn()) + max(1, int(wait_seconds or 1))
            if self.state.get("active_account") == account:
                self.state["active_account"] = None
            self._persist()

    def complete_cycle(self, account, wait_seconds=3600):
        with self._lock:
            record = self.state["accounts"][account]
            incomplete = [
                target for target in record.get("targets", [])
                if target.get("state") not in TERMINAL_TARGET_STATES
            ]
            if incomplete:
                raise RuntimeError("Cannot complete a blast with pending targets")
            record.update({
                "status": "waiting",
                "completed_at": _now_iso(float(self.now_fn())),
                "due_at": float(self.now_fn()) + max(1, int(wait_seconds)),
                "last_run_id": record.get("run_id"),
                "last_targets": deepcopy(record.get("targets") or []),
                "run_id": None,
                "targets": [],
                "cursor": 0,
                "pause_reason": None,
            })
            if self.state.get("active_account") == account:
                self.state["active_account"] = None
            self._persist()
            return deepcopy(record)

    def release_empty_cycle(self, account, wait_seconds=3600):
        """Finish a scan that produced no sendable targets."""
        with self._lock:
            record = self.state["accounts"][account]
            record.update({
                "status": "waiting",
                "completed_at": _now_iso(float(self.now_fn())),
                "due_at": float(self.now_fn()) + max(1, int(wait_seconds)),
                "run_id": None,
                "targets": [],
                "cursor": 0,
            })
            if self.state.get("active_account") == account:
                self.state["active_account"] = None
            self._persist()

    def disable_account(self, account, reason="offline"):
        with self._lock:
            record = self.state["accounts"].setdefault(account, {})
            record["enabled"] = False
            record["status"] = "offline"
            record["pause_reason"] = reason
            if self.state.get("active_account") == account:
                self.state["active_account"] = None
            self._persist()

    def remaining_wait(self, account, now=None):
        with self._lock:
            now = float(self.now_fn() if now is None else now)
            due_at = float(self.state["accounts"].get(account, {}).get("due_at", now) or now)
            return max(0, int(due_at - now))

    def snapshot(self):
        with self._lock:
            snapshot = deepcopy(self.state)
            for account, record in snapshot.get("accounts", {}).items():
                targets = record.get("targets") or []
                record["total_targets"] = len(targets)
                record["accepted_targets"] = sum(
                    1 for item in targets if item.get("state") == "accepted"
                )
                record["failed_targets"] = sum(
                    1 for item in targets if item.get("state") == "failed"
                )
                record["skipped_targets"] = sum(
                    1 for item in targets
                    if item.get("state") in {"skipped", "skipped_uncertain"}
                )
                record["pending_targets"] = sum(
                    1 for item in targets
                    if item.get("state") not in TERMINAL_TARGET_STATES
                )
                record["current_group"] = (
                    targets[record.get("cursor", 0)].get("group")
                    if targets and 0 <= int(record.get("cursor", 0) or 0) < len(targets)
                    else None
                )
                record["remaining_seconds"] = self.remaining_wait(account)
                # Full per-target data stays in the protected group-status API.
            return snapshot


def load_blast_snapshot(path="blast_checkpoint_v3.json"):
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
