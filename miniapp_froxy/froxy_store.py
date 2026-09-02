"""Durable state and billing primitives for the Froxy Telegram Mini App.

Production writes are deliberately fail-closed when Firestore is unavailable.
The in-memory backend exists only for local development and automated tests.
"""

from __future__ import annotations

import copy
import hashlib
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

try:
    import firestore_helper
except ImportError:  # pragma: no cover - package-style local execution
    from .. import firestore_helper


ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_ORDERS = 80
MAX_CHATS = 24
MAX_MESSAGES_PER_CHAT = 40
MAX_PROCESSED_KEYS = 160
MAX_RESERVATIONS = 80


class StoreUnavailable(RuntimeError):
    """Raised when durable production state cannot be reached."""


class InsufficientBalance(ValueError):
    """Raised when a wallet or AI-credit debit cannot be completed."""


class QuotaExceeded(ValueError):
    """Raised when the daily free allowance is exhausted."""


def _safe_id(value: Any) -> str:
    raw = str(value or "").strip()
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return digest


def _utc_ts() -> int:
    return int(time.time())


def _quota_day(now: float | None = None) -> str:
    stamp = datetime.fromtimestamp(now or time.time(), tz=ISTANBUL)
    return stamp.strftime("%Y-%m-%d")


def _quota_reset_at(now: float | None = None) -> str:
    stamp = datetime.fromtimestamp(now or time.time(), tz=ISTANBUL)
    return (stamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()


def _trim_map(data: dict[str, Any], limit: int) -> dict[str, Any]:
    if len(data) <= limit:
        return data
    ordered = sorted(
        data.items(),
        key=lambda row: int((row[1] or {}).get("created_at", 0) or 0),
        reverse=True,
    )
    return dict(ordered[:limit])


class FroxyStore:
    """Small CAS-based store over the repository's Firestore REST helper."""

    _memory_docs: dict[str, dict[str, Any]] = {}
    _memory_lock = threading.RLock()

    def __init__(self, backend: str | None = None):
        selected = (backend or os.environ.get("FROXY_STORE_BACKEND", "")).strip().lower()
        if not selected:
            selected = "firestore" if os.environ.get("RENDER", "").lower() == "true" else "memory"
        if selected not in {"firestore", "memory"}:
            raise ValueError("FROXY_STORE_BACKEND must be 'firestore' or 'memory'")
        self.backend = selected

    @classmethod
    def reset_memory(cls) -> None:
        with cls._memory_lock:
            cls._memory_docs = {}

    def _read(self, doc_id: str) -> tuple[dict[str, Any] | None, Any]:
        if self.backend == "memory":
            with self._memory_lock:
                current = self._memory_docs.get(doc_id)
                version = int((current or {}).get("_memory_version", 0) or 0)
                return copy.deepcopy(current), version
        if not firestore_helper.remote_credentials_configured():
            raise StoreUnavailable("Firestore production credentials are missing")
        fields, update_time = firestore_helper.get_document_with_meta(doc_id, quiet=True)
        if fields is None and update_time is None:
            return None, None
        return fields, update_time

    def _claim(self, doc_id: str, fields: dict[str, Any]) -> bool:
        if self.backend == "memory":
            with self._memory_lock:
                if doc_id in self._memory_docs:
                    return False
                row = copy.deepcopy(fields)
                row["_memory_version"] = 1
                self._memory_docs[doc_id] = row
                return True
        result = firestore_helper.claim_remote_document(doc_id, fields, quiet=True)
        if result is None:
            raise StoreUnavailable("Firestore is unavailable")
        return bool(result)

    def _cas(self, doc_id: str, fields: dict[str, Any], version: Any) -> bool:
        if self.backend == "memory":
            with self._memory_lock:
                current = self._memory_docs.get(doc_id)
                current_version = int((current or {}).get("_memory_version", 0) or 0)
                if current is None or current_version != int(version or 0):
                    return False
                row = copy.deepcopy(fields)
                row["_memory_version"] = current_version + 1
                self._memory_docs[doc_id] = row
                return True
        result = firestore_helper.compare_and_set_document(doc_id, fields, version, quiet=True)
        if result is None:
            raise StoreUnavailable("Firestore is unavailable")
        return bool(result)

    def _mutate_doc(
        self,
        doc_id: str,
        default_factory: Callable[[], dict[str, Any]],
        mutator: Callable[[dict[str, Any]], Any],
        retries: int = 12,
    ) -> tuple[dict[str, Any], Any]:
        last_error: Exception | None = None
        for _ in range(retries):
            current, version = self._read(doc_id)
            if current is None:
                current = default_factory()
                try:
                    result = mutator(current)
                except Exception:
                    raise
                if self._claim(doc_id, current):
                    return copy.deepcopy(current), result
                continue
            current.pop("_memory_version", None)
            try:
                result = mutator(current)
            except Exception:
                raise
            if self._cas(doc_id, current, version):
                return copy.deepcopy(current), result
        if last_error:
            raise last_error
        raise StoreUnavailable("Concurrent Firestore update could not be committed")

    @staticmethod
    def _user_doc_id(user_id: int | str) -> str:
        return f"froxy_user_v1_{_safe_id(user_id)}"

    @staticmethod
    def _default_user(user_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any]:
        p = profile or {}
        now = _utc_ts()
        return {
            "id": int(user_id),
            "username": str(p.get("username") or ""),
            "first_name": str(p.get("first_name") or "Müşteri"),
            "last_name": str(p.get("last_name") or ""),
            "wallet_kurus": 0,
            "ai_credits": 0,
            "quota_day": _quota_day(),
            "free_text_used": 0,
            "free_image_used": 0,
            "orders": [],
            "chats": [],
            "image_job_ids": [],
            "topup_ids": [],
            "processed_keys": {},
            "reservations": {},
            "ledger_tail": [],
            "created_at": now,
            "updated_at": now,
        }

    def get_or_create_user(self, profile: dict[str, Any]) -> dict[str, Any]:
        user_id = int(profile["id"])

        def mutate(user: dict[str, Any]) -> None:
            user["id"] = user_id
            for key in ("username", "first_name", "last_name"):
                if profile.get(key) is not None:
                    user[key] = str(profile.get(key) or "")
            self._reset_quota_if_needed(user)
            user["updated_at"] = _utc_ts()

        user, _ = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id, profile),
            mutate,
        )
        return self.public_user(user)

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        user, _ = self._read(self._user_doc_id(user_id))
        if user is None:
            return None
        user.pop("_memory_version", None)
        return self.public_user(user)

    @staticmethod
    def _reset_quota_if_needed(user: dict[str, Any], now: float | None = None) -> None:
        day = _quota_day(now)
        if user.get("quota_day") != day:
            user["quota_day"] = day
            user["free_text_used"] = 0
            user["free_image_used"] = 0

    @staticmethod
    def public_user(user: dict[str, Any]) -> dict[str, Any]:
        safe = copy.deepcopy(user)
        safe.pop("_memory_version", None)
        safe.pop("processed_keys", None)
        safe.pop("reservations", None)
        safe["wallet_balance"] = round(int(safe.get("wallet_kurus", 0)) / 100, 2)
        safe["free_text_remaining"] = max(0, 3 - int(safe.get("free_text_used", 0)))
        safe["free_image_remaining"] = max(0, 1 - int(safe.get("free_image_used", 0)))
        safe["quota_reset_at"] = _quota_reset_at()
        safe["orders"] = list(reversed(safe.get("orders", [])))
        return safe

    def consume_free_quota(self, user_id: int, kind: str, request_id: str) -> dict[str, int]:
        if kind not in {"text", "image"}:
            raise ValueError("Unknown free quota kind")
        key = f"quota:{kind}:{request_id}"

        def mutate(user: dict[str, Any]) -> dict[str, int]:
            self._reset_quota_if_needed(user)
            processed = user.setdefault("processed_keys", {})
            if key in processed:
                return {
                    "text": max(0, 3 - int(user.get("free_text_used", 0))),
                    "image": max(0, 1 - int(user.get("free_image_used", 0))),
                }
            field, limit = ("free_text_used", 3) if kind == "text" else ("free_image_used", 1)
            used = int(user.get(field, 0))
            if used >= limit:
                raise QuotaExceeded("Günlük ücretsiz hakkınız tükendi")
            user[field] = used + 1
            processed[key] = {"created_at": _utc_ts(), "type": "quota"}
            user["processed_keys"] = _trim_map(processed, MAX_PROCESSED_KEYS)
            user["updated_at"] = _utc_ts()
            return {
                "text": max(0, 3 - int(user.get("free_text_used", 0))),
                "image": max(0, 1 - int(user.get("free_image_used", 0))),
            }

        _, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        return result

    def restore_free_quota(self, user_id: int, kind: str, request_id: str) -> None:
        if kind not in {"text", "image"}:
            return
        key = f"quota:{kind}:{request_id}"

        def mutate(user: dict[str, Any]) -> None:
            processed = user.setdefault("processed_keys", {})
            event = processed.get(key)
            if not event or event.get("refunded"):
                return
            field = "free_text_used" if kind == "text" else "free_image_used"
            user[field] = max(0, int(user.get(field, 0)) - 1)
            event["refunded"] = True
            event["refunded_at"] = _utc_ts()
            processed[key] = event
            user["updated_at"] = _utc_ts()

        self._mutate_doc(self._user_doc_id(user_id), lambda: self._default_user(user_id), mutate)

    def reserve_credits(self, user_id: int, request_id: str, amount: int, purpose: str) -> dict[str, Any]:
        reserve = max(1, int(amount))
        key = str(request_id)[:120]

        def mutate(user: dict[str, Any]) -> dict[str, Any]:
            reservations = user.setdefault("reservations", {})
            if key in reservations:
                return {"duplicate": True, **reservations[key], "ai_credits": int(user.get("ai_credits", 0))}
            balance = int(user.get("ai_credits", 0))
            if balance < reserve:
                raise InsufficientBalance("Yetersiz AI kredisi")
            user["ai_credits"] = balance - reserve
            reservations[key] = {
                "amount": reserve,
                "purpose": str(purpose)[:80],
                "state": "reserved",
                "created_at": _utc_ts(),
            }
            user["reservations"] = _trim_map(reservations, MAX_RESERVATIONS)
            user["updated_at"] = _utc_ts()
            return {"duplicate": False, "amount": reserve, "ai_credits": user["ai_credits"]}

        _, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        return result

    def settle_credits(self, user_id: int, request_id: str, actual_amount: int, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        key = str(request_id)[:120]
        actual = max(0, int(actual_amount))

        def mutate(user: dict[str, Any]) -> dict[str, Any]:
            reservations = user.setdefault("reservations", {})
            row = reservations.get(key)
            if not row:
                return {"missing": True, "ai_credits": int(user.get("ai_credits", 0))}
            if row.get("state") == "settled":
                return {"duplicate": True, "charged": int(row.get("charged", 0)), "ai_credits": int(user.get("ai_credits", 0))}
            reserved = int(row.get("amount", 0))
            charged = min(reserved, actual)
            refund = max(0, reserved - charged)
            user["ai_credits"] = int(user.get("ai_credits", 0)) + refund
            row.update({"state": "settled", "charged": charged, "refund": refund, "settled_at": _utc_ts()})
            if metadata:
                row["metadata"] = copy.deepcopy(metadata)
            reservations[key] = row
            ledger = user.setdefault("ledger_tail", [])
            ledger.append({
                "id": key,
                "type": "ai_usage",
                "amount": -charged,
                "purpose": row.get("purpose"),
                "created_at": _utc_ts(),
            })
            user["ledger_tail"] = ledger[-40:]
            user["updated_at"] = _utc_ts()
            return {"charged": charged, "refund": refund, "ai_credits": user["ai_credits"]}

        updated, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        if not result.get("missing") and not result.get("duplicate"):
            self._write_immutable_ledger(user_id, key, updated.get("ledger_tail", [])[-1])
        return result

    def refund_credits(self, user_id: int, request_id: str, reason: str = "provider_error") -> dict[str, Any]:
        return self.settle_credits(user_id, request_id, 0, {"refund_reason": reason})

    def credit_balance(
        self,
        user_id: int,
        *,
        wallet_kurus: int = 0,
        ai_credits: int = 0,
        idempotency_key: str,
        title: str,
    ) -> dict[str, Any]:
        idem = str(idempotency_key)[:160]
        if not idem:
            raise ValueError("idempotency_key is required")
        wallet_delta = max(0, int(wallet_kurus))
        credit_delta = max(0, int(ai_credits))

        def mutate(user: dict[str, Any]) -> dict[str, Any]:
            processed = user.setdefault("processed_keys", {})
            if idem in processed:
                return {"duplicate": True, **processed[idem], "wallet_kurus": int(user.get("wallet_kurus", 0)), "ai_credits": int(user.get("ai_credits", 0))}
            user["wallet_kurus"] = int(user.get("wallet_kurus", 0)) + wallet_delta
            user["ai_credits"] = int(user.get("ai_credits", 0)) + credit_delta
            event = {
                "type": "credit",
                "wallet_kurus": wallet_delta,
                "ai_credits": credit_delta,
                "title": str(title)[:160],
                "created_at": _utc_ts(),
            }
            processed[idem] = event
            user["processed_keys"] = _trim_map(processed, MAX_PROCESSED_KEYS)
            user.setdefault("ledger_tail", []).append({"id": idem, **event})
            user["ledger_tail"] = user["ledger_tail"][-40:]
            user["updated_at"] = _utc_ts()
            return {"duplicate": False, **event, "wallet_kurus": user["wallet_kurus"], "ai_credits": user["ai_credits"]}

        updated, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        if not result.get("duplicate"):
            self._write_immutable_ledger(user_id, idem, updated.get("ledger_tail", [])[-1])
        return result

    def reserve_wallet_purchase(
        self,
        user_id: int,
        idempotency_key: str,
        total_kurus: int,
        orders: list[dict[str, Any]],
    ) -> dict[str, Any]:
        idem = f"purchase:{str(idempotency_key)[:140]}"
        total = max(0, int(total_kurus))

        def mutate(user: dict[str, Any]) -> dict[str, Any]:
            processed = user.setdefault("processed_keys", {})
            if idem in processed:
                order_ids = set(processed[idem].get("order_ids", []))
                existing = [o for o in user.get("orders", []) if o.get("order_id") in order_ids]
                return {"duplicate": True, "orders": existing, "wallet_kurus": int(user.get("wallet_kurus", 0))}
            balance = int(user.get("wallet_kurus", 0))
            if balance < total:
                raise InsufficientBalance("Yetersiz mağaza bakiyesi")
            user["wallet_kurus"] = balance - total
            pending = copy.deepcopy(orders)
            for row in pending:
                row["status"] = "processing"
                row["created_at"] = int(row.get("created_at") or _utc_ts())
            user.setdefault("orders", []).extend(pending)
            user["orders"] = user["orders"][-MAX_ORDERS:]
            processed[idem] = {"type": "purchase", "order_ids": [o["order_id"] for o in pending], "created_at": _utc_ts()}
            user["processed_keys"] = _trim_map(processed, MAX_PROCESSED_KEYS)
            user.setdefault("ledger_tail", []).append({"id": idem, "type": "wallet_purchase", "amount_kurus": -total, "created_at": _utc_ts()})
            user["ledger_tail"] = user["ledger_tail"][-40:]
            user["updated_at"] = _utc_ts()
            return {"duplicate": False, "orders": pending, "wallet_kurus": user["wallet_kurus"]}

        updated, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        if not result.get("duplicate"):
            self._write_immutable_ledger(user_id, idem, updated.get("ledger_tail", [])[-1])
        return result

    def finalize_orders(self, user_id: int, finalized_orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        replacements = {str(row["order_id"]): copy.deepcopy(row) for row in finalized_orders}

        def mutate(user: dict[str, Any]) -> list[dict[str, Any]]:
            result = []
            rows = []
            for order in user.get("orders", []):
                replacement = replacements.get(str(order.get("order_id")))
                if replacement:
                    rows.append(replacement)
                    result.append(replacement)
                else:
                    rows.append(order)
            user["orders"] = rows[-MAX_ORDERS:]
            user["updated_at"] = _utc_ts()
            return result

        _, result = self._mutate_doc(
            self._user_doc_id(user_id),
            lambda: self._default_user(user_id),
            mutate,
        )
        for order in result:
            self._write_order_doc(user_id, order)
        return result

    def append_chat(
        self,
        user_id: int,
        chat_id: str,
        model_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        cid = str(chat_id or uuid.uuid4().hex)[:80]

        def mutate(user: dict[str, Any]) -> None:
            chats = list(user.get("chats", []))
            target = next((row for row in chats if row.get("chat_id") == cid), None)
            if target is None:
                target = {"chat_id": cid, "title": user_message[:80], "messages": [], "created_at": _utc_ts()}
                chats.append(target)
            target["model_id"] = str(model_id)[:180]
            target.setdefault("messages", []).extend([
                {"role": "user", "content": user_message[:12000], "created_at": _utc_ts()},
                {"role": "assistant", "content": assistant_message[:24000], "created_at": _utc_ts()},
            ])
            target["messages"] = target["messages"][-MAX_MESSAGES_PER_CHAT:]
            target["updated_at"] = _utc_ts()
            user["chats"] = chats[-MAX_CHATS:]
            user["updated_at"] = _utc_ts()

        self._mutate_doc(self._user_doc_id(user_id), lambda: self._default_user(user_id), mutate)

    def create_image_job(self, user_id: int, job: dict[str, Any]) -> dict[str, Any]:
        job_id = str(job.get("job_id") or uuid.uuid4().hex)
        row = {**copy.deepcopy(job), "job_id": job_id, "user_id": int(user_id), "status": "queued", "created_at": _utc_ts(), "updated_at": _utc_ts()}
        doc_id = f"froxy_job_v1_{_safe_id(job_id)}"
        if not self._claim(doc_id, row):
            existing, _ = self._read(doc_id)
            row = existing or row

        def mutate(user: dict[str, Any]) -> None:
            ids = list(user.get("image_job_ids", []))
            if job_id not in ids:
                ids.append(job_id)
            user["image_job_ids"] = ids[-40:]
            user["updated_at"] = _utc_ts()

        self._mutate_doc(self._user_doc_id(user_id), lambda: self._default_user(user_id), mutate)
        return row

    def get_image_job(self, user_id: int, job_id: str) -> dict[str, Any] | None:
        row, _ = self._read(f"froxy_job_v1_{_safe_id(job_id)}")
        if row and int(row.get("user_id", 0)) == int(user_id):
            row.pop("_memory_version", None)
            return row
        return None

    def update_image_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        doc_id = f"froxy_job_v1_{_safe_id(job_id)}"

        def mutate(row: dict[str, Any]) -> None:
            row.update(copy.deepcopy(updates))
            row["updated_at"] = _utc_ts()

        row, _ = self._mutate_doc(doc_id, lambda: {"job_id": job_id, "created_at": _utc_ts()}, mutate)
        return row

    def save_topup(self, topup: dict[str, Any]) -> dict[str, Any]:
        pid = str(topup["product_id"])
        doc_id = f"froxy_topup_v1_{_safe_id(pid)}"
        row = copy.deepcopy(topup)
        row.setdefault("created_at", _utc_ts())
        row.setdefault("status", "pending")
        if not self._claim(doc_id, row):
            existing, _ = self._read(doc_id)
            return existing or row

        user_id = int(row.get("user_id", 0) or 0)
        if user_id:
            def mutate_user(user: dict[str, Any]) -> None:
                ids = list(user.get("topup_ids", []))
                if pid not in ids:
                    ids.append(pid)
                user["topup_ids"] = ids[-40:]
                user["updated_at"] = _utc_ts()

            self._mutate_doc(self._user_doc_id(user_id), lambda: self._default_user(user_id), mutate_user)

        def mutate_index(index: dict[str, Any]) -> None:
            ids = list(index.get("product_ids", []))
            if pid not in ids:
                ids.append(pid)
            index["product_ids"] = ids[-240:]
            index["updated_at"] = _utc_ts()

        self._mutate_doc("froxy_topup_index_v1", lambda: {"product_ids": []}, mutate_index)
        return row

    def get_topup(self, product_id: str) -> dict[str, Any] | None:
        row, _ = self._read(f"froxy_topup_v1_{_safe_id(product_id)}")
        if row:
            row.pop("_memory_version", None)
        return row

    def get_pending_topup_by_idempotency(self, user_id: int, idempotency_key: str) -> dict[str, Any] | None:
        """Look up a pending checkout from Firestore, never local JSON."""
        user, _ = self._read(self._user_doc_id(user_id))
        if not user:
            return None
        for product_id in reversed(list(user.get("topup_ids", []))[-40:]):
            row = self.get_topup(str(product_id))
            if (
                row
                and row.get("status") == "pending"
                and str(row.get("idempotency_key") or "") == str(idempotency_key)
            ):
                return row
        return None

    def update_topup(self, product_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        doc_id = f"froxy_topup_v1_{_safe_id(product_id)}"

        def mutate(row: dict[str, Any]) -> None:
            row.update(copy.deepcopy(updates))
            row["updated_at"] = _utc_ts()

        row, _ = self._mutate_doc(doc_id, lambda: {"product_id": str(product_id), "created_at": _utc_ts()}, mutate)
        return row

    def list_active_topups(self) -> list[dict[str, Any]]:
        index, _ = self._read("froxy_topup_index_v1")
        if not index:
            return []
        rows = []
        for product_id in list(index.get("product_ids", []))[-240:]:
            row = self.get_topup(str(product_id))
            if row and row.get("status") == "pending":
                rows.append(row)
        return rows

    def _write_immutable_ledger(self, user_id: int, event_id: str, event: dict[str, Any]) -> None:
        doc_id = f"froxy_ledger_v1_{_safe_id(f'{user_id}:{event_id}')}"
        payload = {"user_id": int(user_id), "event_id": str(event_id), **copy.deepcopy(event)}
        try:
            self._claim(doc_id, payload)
        except StoreUnavailable:
            # The authoritative user CAS already succeeded. The embedded ledger
            # tail keeps reconciliation possible until Firestore is healthy.
            pass

    def _write_order_doc(self, user_id: int, order: dict[str, Any]) -> None:
        doc_id = f"froxy_order_v1_{_safe_id(order.get('order_id'))}"
        payload = {"user_id": int(user_id), **copy.deepcopy(order)}
        try:
            current, version = self._read(doc_id)
            if current is None:
                self._claim(doc_id, payload)
            else:
                current.pop("_memory_version", None)
                current.update(payload)
                self._cas(doc_id, current, version)
        except StoreUnavailable:
            pass
