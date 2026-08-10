"""Small, privacy-preserving sales funnel event journal.

The Telegram workers and the Flask dashboard run in separate processes.  A
line-oriented journal keeps writes append-only and makes the seven-day test
observable without storing message contents or customer PII.
"""

from __future__ import annotations

import json
import os
import threading
import queue
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_WRITE_LOCK = threading.Lock()
_DEFAULT_FILE = "sales_metrics.jsonl"
_DURABLE_DOC_ID = "sales_metrics_journal_v1"
_DURABLE_QUEUE: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=500)
_DURABLE_STARTED = False
_DURABLE_START_LOCK = threading.Lock()


def _path() -> Path:
    configured = os.environ.get("SALES_METRICS_FILE", "").strip()
    return Path(configured or _DEFAULT_FILE)


def record_event(kind: str, account: str, **fields: Any) -> None:
    """Append one sanitized funnel event.

    Values are deliberately limited to scalar metadata.  Raw Telegram text,
    usernames, e-mail addresses and phone numbers must never be written here.
    """
    event = {
        "event_id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": str(kind),
        "account": str(account),
    }
    for key, value in fields.items():
        if value is None or isinstance(value, (dict, list, tuple, set)):
            continue
        if key in {"text", "message", "username", "email", "phone", "user_id", "chat_id"}:
            continue
        event[key] = value if isinstance(value, (str, int, float, bool)) else str(value)

    target = _path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with _WRITE_LOCK:
            with target.open("ab") as handle:
                handle.write(line)
        _queue_durable_event(event)
    except Exception:
        # Metrics must never stop a Telegram handler or a webhook.
        return


def _queue_durable_event(event: dict[str, Any]) -> None:
    """Persist best-effort in Firestore without blocking Telegram handlers."""
    global _DURABLE_STARTED
    with _DURABLE_START_LOCK:
        if not _DURABLE_STARTED:
            threading.Thread(target=_durable_writer, name="sales-metrics", daemon=True).start()
            _DURABLE_STARTED = True
    try:
        _DURABLE_QUEUE.put_nowait(event)
    except queue.Full:
        pass


def _durable_writer() -> None:
    while True:
        event = _DURABLE_QUEUE.get()
        try:
            _append_durable(event)
        except Exception:
            pass
        finally:
            _DURABLE_QUEUE.task_done()


def _append_durable(event: dict[str, Any]) -> None:
    """CAS append a small sanitized rolling journal; never raise to callers."""
    try:
        import firestore_helper
    except Exception:
        return
    for _ in range(2):
        fields, update_time = firestore_helper.get_document_with_meta(_DURABLE_DOC_ID, quiet=True)
        existing: list[dict[str, Any]] = []
        if fields and fields.get("events_json"):
            try:
                parsed = json.loads(str(fields["events_json"]))
                if isinstance(parsed, list):
                    existing = [x for x in parsed if isinstance(x, dict)]
            except (TypeError, ValueError, json.JSONDecodeError):
                existing = []
        if any(item.get("event_id") == event["event_id"] for item in existing):
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        existing = [item for item in existing if _event_is_newer_than(item, cutoff)]
        existing.append(event)
        # Keep document far below Firestore's size limit.
        existing = existing[-1000:]
        payload = {"events_json": json.dumps(existing, ensure_ascii=False, separators=(",", ":"))}
        if fields is None:
            if firestore_helper.claim_document(_DURABLE_DOC_ID, payload, quiet=True) is True:
                return
        elif firestore_helper.compare_and_set_document(_DURABLE_DOC_ID, payload, update_time, quiet=True) is True:
            return


def _event_is_newer_than(event: dict[str, Any], cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00")) >= cutoff
    except (TypeError, ValueError):
        return False


def read_events(days: int = 7) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    target = _path()
    if not target.exists():
        return []
    result: list[dict[str, Any]] = []
    try:
        with target.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                    ts = datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00"))
                    if ts >= cutoff:
                        result.append(event)
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
    except OSError:
        return []
    return result


def _read_durable_events(days: int) -> list[dict[str, Any]]:
    try:
        import firestore_helper
        fields = firestore_helper.get_document(_DURABLE_DOC_ID) or {}
        raw = json.loads(str(fields.get("events_json", "[]")))
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        return [item for item in raw if isinstance(item, dict) and _event_is_newer_than(item, cutoff)]
    except Exception:
        return []


def summarize(days: int = 7) -> dict[str, Any]:
    events_by_id = {}
    for event in _read_durable_events(days) + read_events(days):
        events_by_id[str(event.get("event_id") or json.dumps(event, sort_keys=True))] = event
    events = list(events_by_id.values())
    by_kind: dict[str, int] = {}
    by_account: dict[str, dict[str, int | float]] = {}
    revenue = 0.0
    bundles: dict[str, dict[str, int | float]] = {}
    for event in events:
        kind = str(event.get("kind", "unknown"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
        account = str(event.get("account", "unknown"))
        bucket = by_account.setdefault(account, {"events": 0, "orders": 0, "revenue": 0.0})
        bucket["events"] = int(bucket["events"]) + 1
        if kind == "shopier_order":
            bucket["orders"] = int(bucket["orders"]) + 1
            try:
                amount = float(event.get("amount", 0) or 0)
            except (TypeError, ValueError):
                amount = 0.0
            bucket["revenue"] = round(float(bucket["revenue"]) + amount, 2)
            revenue += amount
            bundle = str(event.get("bundle") or "").strip()
            if bundle:
                item = bundles.setdefault(bundle, {"orders": 0, "revenue": 0.0})
                item["orders"] = int(item["orders"]) + 1
                item["revenue"] = round(float(item["revenue"]) + amount, 2)
    ads = by_kind.get("ad_sent", 0)
    dms = by_kind.get("dm_received", 0)
    orders = by_kind.get("shopier_order", 0)
    return {
        "days": int(days),
        "event_count": len(events),
        "by_kind": by_kind,
        "by_account": by_account,
        "revenue": round(revenue, 2),
        "by_bundle": bundles,
        "funnel": {
            "ad_sent": ads, "dm_received": dms, "orders": orders,
            "ad_to_dm_pct": round((dms / ads) * 100, 2) if ads else 0.0,
            "dm_to_order_pct": round((orders / dms) * 100, 2) if dms else 0.0,
        },
    }
