"""Small, privacy-preserving sales funnel event journal.

The Telegram workers and the Flask dashboard run in separate processes.  A
line-oriented journal keeps writes append-only and makes the seven-day test
observable without storing message contents or customer PII.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_WRITE_LOCK = threading.Lock()
_DEFAULT_FILE = "sales_metrics.jsonl"


def _path() -> Path:
    configured = os.environ.get("SALES_METRICS_FILE", "").strip()
    return Path(configured or _DEFAULT_FILE)


def record_event(kind: str, account: str, **fields: Any) -> None:
    """Append one sanitized funnel event.

    Values are deliberately limited to scalar metadata.  Raw Telegram text,
    usernames, e-mail addresses and phone numbers must never be written here.
    """
    event = {
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
    except Exception:
        # Metrics must never stop a Telegram handler or a webhook.
        return


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


def summarize(days: int = 7) -> dict[str, Any]:
    events = read_events(days)
    by_kind: dict[str, int] = {}
    by_account: dict[str, dict[str, int | float]] = {}
    revenue = 0.0
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
    return {
        "days": int(days),
        "event_count": len(events),
        "by_kind": by_kind,
        "by_account": by_account,
        "revenue": round(revenue, 2),
    }
