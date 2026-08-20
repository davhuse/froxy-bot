"""Small, privacy-preserving sales funnel event journal.

The Telegram workers and the Flask dashboard run in separate processes.  A
line-oriented journal keeps writes append-only and makes the seven-day test
observable without storing message contents or customer PII.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import os
import threading
import queue
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from customer_intent import classify_customer_message

_WRITE_LOCK = threading.Lock()
_DEFAULT_FILE = "sales_metrics.jsonl"
_BASELINE_FILE = Path(__file__).with_name("sales_metrics_baseline.json")
_DURABLE_DOC_ID = "sales_metrics_journal_v1"
_DURABLE_QUEUE: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=500)
_DURABLE_STARTED = False
_DURABLE_START_LOCK = threading.Lock()


_ACCOUNT_ALIASES = {
    "keyvadi": "keyvadi", "keyvadi online": "keyvadi", "keyvadionline": "keyvadi",
    "keyvadi satis": "keyvadi", "keyvadi bot": "keyvadi",
    "froxy": "froxy", "froxy ai": "froxy", "froxyonline": "froxy",
    "froxy online": "froxy", "froxy destek": "froxy",
    "lisansarena": "lisansarena", "lisans arena": "lisansarena",
    "lisansarenaonline": "lisansarena", "lisans arena online": "lisansarena",
}


def canonical_account(account: str) -> str:
    raw = str(account or "unknown").strip()
    key = " ".join(raw.casefold().replace("_", " ").replace("-", " ").split())
    return _ACCOUNT_ALIASES.get(key, key.replace(" ", "") or "unknown")


def _private_key(*parts: Any) -> str:
    secret = os.environ.get("METRICS_HASH_SECRET", "").strip()
    if not secret:
        secret = os.environ.get("SECRET_KEY", "sales-metrics-local-fallback")
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()[:32]


def _path() -> Path:
    configured = os.environ.get("SALES_METRICS_FILE", "").strip()
    return Path(configured or _DEFAULT_FILE)


def _baseline_at() -> datetime | None:
    configured = os.environ.get("SALES_METRICS_BASELINE_AT", "").strip()
    if not configured and _BASELINE_FILE.exists():
        try:
            configured = str(json.loads(_BASELINE_FILE.read_text(encoding="utf-8")).get("start_at") or "").strip()
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            configured = ""
    if not configured:
        return None
    try:
        value = datetime.fromisoformat(configured.replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def record_event(kind: str, account: str, **fields: Any) -> None:
    """Append one sanitized funnel event.

    Values are deliberately limited to scalar metadata.  Raw Telegram text,
    usernames, e-mail addresses and phone numbers must never be written here.
    """
    event = {
        "event_id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": str(kind),
        "account": canonical_account(account),
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


def record_dm_event(account: str, user_id: Any, message: str, *,
                    message_id: Any = None, source: str = "telegram_private",
                    product_matched: bool = False,
                    has_sales_context: bool = False) -> str:
    """Record one DM without storing customer identity or message contents."""
    brand = canonical_account(account)
    intent = classify_customer_message(
        message, product_matched=product_matched, has_sales_context=has_sales_context
    )
    fields: dict[str, Any] = {
        "source": source,
        "dm_class": intent,
        "conversation_key": _private_key("conversation", brand, user_id),
    }
    if message_id is not None:
        fields["message_key"] = _private_key("message", brand, user_id, message_id)
    record_event("dm_received", brand, **fields)
    return intent


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
    try:
        event_day = datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00")).strftime("%Y%m%d")
    except (TypeError, ValueError):
        event_day = datetime.now(timezone.utc).strftime("%Y%m%d")
    document_id = f"sales_metrics_{event_day}"
    for _ in range(2):
        fields, update_time = firestore_helper.get_document_with_meta(document_id, quiet=True)
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
        # Daily shards keep a full high-volume day while remaining below
        # Firestore's 1 MiB document limit for these small scalar events.
        existing = existing[-2500:]
        payload = {"events_json": json.dumps(existing, ensure_ascii=False, separators=(",", ":"))}
        if fields is None:
            if firestore_helper.claim_document(document_id, payload, quiet=True) is True:
                return
        elif firestore_helper.compare_and_set_document(document_id, payload, update_time, quiet=True) is True:
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
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        rows: list[dict[str, Any]] = []
        # Read legacy rolling data once, then one bounded document per UTC day.
        document_ids = [_DURABLE_DOC_ID]
        for offset in range(max(1, int(days)) + 1):
            day = (datetime.now(timezone.utc) - timedelta(days=offset)).strftime("%Y%m%d")
            document_ids.append(f"sales_metrics_{day}")
        for document_id in document_ids:
            fields = firestore_helper.get_document(document_id) or {}
            try:
                raw = json.loads(str(fields.get("events_json", "[]")))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            rows.extend(
                item for item in raw
                if isinstance(item, dict) and _event_is_newer_than(item, cutoff)
            )
        return rows
    except Exception:
        return []


def summarize(days: int = 7) -> dict[str, Any]:
    events_by_id = {}
    for event in _read_durable_events(days) + read_events(days):
        events_by_id[str(event.get("event_id") or json.dumps(event, sort_keys=True))] = event
    baseline_at = _baseline_at()
    events = [
        event for event in events_by_id.values()
        if baseline_at is None or _event_is_newer_than(event, baseline_at)
    ]
    by_kind: dict[str, int] = {}
    by_account: dict[str, dict[str, int | float]] = {}
    revenue = 0.0
    procurement_cost = 0.0
    refunds = 0.0
    bundles: dict[str, dict[str, int | float]] = {}
    by_product: dict[str, dict[str, int | float]] = {}
    by_arm: dict[str, dict[str, int | float]] = {}
    unique_conversations: set[str] = set()
    qualified_conversations: set[str] = set()
    account_conversations: dict[str, set[str]] = {}
    account_qualified: dict[str, set[str]] = {}
    dm_classes: dict[str, int] = {}
    for event in events:
        kind = str(event.get("kind", "unknown"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
        account = canonical_account(str(event.get("account", "unknown")))
        bucket = by_account.setdefault(account, {"events": 0, "orders": 0, "revenue": 0.0})
        bucket["events"] = int(bucket["events"]) + 1
        bucket[kind] = int(bucket.get(kind, 0)) + 1
        if kind == "dm_received":
            conversation_key = str(event.get("conversation_key") or "").strip()
            if not conversation_key:
                # Historical events lacked a safe conversation identifier;
                # count them as separate unknown conversations rather than
                # silently pretending they belong to one customer.
                conversation_key = f"legacy:{event.get('event_id', id(event))}"
            unique_conversations.add(conversation_key)
            account_conversations.setdefault(account, set()).add(conversation_key)
            dm_class = str(event.get("dm_class") or "unknown")
            dm_classes[dm_class] = dm_classes.get(dm_class, 0) + 1
            if dm_class == "sales_lead":
                qualified_conversations.add(conversation_key)
                account_qualified.setdefault(account, set()).add(conversation_key)
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
        elif kind in {"procurement_fulfilled", "shopier_refund", "refund"}:
            try:
                amount = float(event.get("amount", 0) or 0)
            except (TypeError, ValueError):
                amount = 0.0
            if kind == "procurement_fulfilled":
                procurement_cost += amount
            else:
                refunds += amount
        product = str(event.get("product") or "").strip()
        if product:
            product_bucket = by_product.setdefault(product, {})
            product_bucket[kind] = product_bucket.get(kind, 0) + 1
            try:
                event_amount = float(event.get("amount", 0) or 0)
            except (TypeError, ValueError):
                event_amount = 0.0
            if kind == "shopier_order":
                product_bucket["revenue"] = round(float(product_bucket.get("revenue", 0)) + event_amount, 2)
            elif kind == "procurement_fulfilled":
                product_bucket["cost"] = round(float(product_bucket.get("cost", 0)) + event_amount, 2)
            elif kind in {"shopier_refund", "refund"}:
                product_bucket["refunds"] = round(float(product_bucket.get("refunds", 0)) + event_amount, 2)
        arm = str(event.get("arm") or "").strip()
        if arm:
            arm_bucket = by_arm.setdefault(arm, {})
            arm_bucket[kind] = arm_bucket.get(kind, 0) + 1
    ads = by_kind.get("ad_sent", 0)
    dms = by_kind.get("dm_received", 0)
    orders = by_kind.get("shopier_order", 0)
    matched = by_kind.get("product_matched", 0)
    ctas = by_kind.get("purchase_cta_sent", 0)
    clicks = by_kind.get("purchase_click", 0)
    handoffs = by_kind.get("human_handoff", 0)
    opens = by_kind.get("ad_cta_open", 0)
    for account, bucket in by_account.items():
        bucket["unique_conversations"] = len(account_conversations.get(account, set()))
        bucket["qualified_leads"] = len(account_qualified.get(account, set()))

    def add_rates(bucket):
        bucket["ad_to_open_pct"] = round(
            (bucket.get("ad_cta_open", 0) / bucket.get("ad_sent", 0)) * 100, 2
        ) if bucket.get("ad_sent", 0) else 0.0
        lead_denominator = bucket.get("qualified_leads", bucket.get("dm_received", 0))
        bucket["dm_to_match_pct"] = round(
            (bucket.get("product_matched", 0) / lead_denominator) * 100, 2
        ) if lead_denominator else 0.0
        bucket["match_to_click_pct"] = round(
            (bucket.get("purchase_click", 0) / bucket.get("product_matched", 0)) * 100, 2
        ) if bucket.get("product_matched", 0) else 0.0
        bucket["click_to_order_pct"] = round(
            (bucket.get("shopier_order", 0) / bucket.get("purchase_click", 0)) * 100, 2
        ) if bucket.get("purchase_click", 0) else 0.0
        bucket["handoff_pct"] = round(
            (bucket.get("human_handoff", 0) / bucket.get("dm_received", 0)) * 100, 2
        ) if bucket.get("dm_received", 0) else 0.0
    for dimension in (by_account, by_product, by_arm):
        for dimension_bucket in dimension.values():
            add_rates(dimension_bucket)
            dimension_bucket["net_profit"] = round(
                float(dimension_bucket.get("revenue", 0))
                - float(dimension_bucket.get("cost", 0))
                - float(dimension_bucket.get("refunds", 0)), 2
            )
            dimension_bucket["net_profit_per_1000_visible_ads"] = round(
                dimension_bucket["net_profit"] * 1000 / int(dimension_bucket.get("ad_sent", 0)), 2
            ) if dimension_bucket.get("ad_sent", 0) else 0.0
    return {
        "days": int(days),
        "baseline_at": baseline_at.isoformat() if baseline_at else None,
        "event_count": len(events),
        "by_kind": by_kind,
        "by_account": by_account,
        "revenue": round(revenue, 2),
        "procurement_cost": round(procurement_cost, 2),
        "refunds": round(refunds, 2),
        "net_profit": round(revenue - procurement_cost - refunds, 2),
        "by_bundle": bundles,
        "by_product": by_product,
        "by_arm": by_arm,
        "dm_classes": dm_classes,
        "funnel": {
            "ad_sent": ads, "ad_cta_open": opens, "dm_received": dms,
            "raw_dm_received": dms,
            "unique_conversations": len(unique_conversations),
            "qualified_leads": len(qualified_conversations),
            "product_matched": matched, "purchase_cta_sent": ctas,
            "purchase_click": clicks, "human_handoff": handoffs, "orders": orders,
            "ad_to_dm_pct": round((dms / ads) * 100, 2) if ads else 0.0,
            "ad_to_open_pct": round((opens / ads) * 100, 2) if ads else 0.0,
            "dm_to_match_pct": round(
                (matched / len(qualified_conversations)) * 100, 2
            ) if qualified_conversations else 0.0,
            "match_to_click_pct": round((clicks / matched) * 100, 2) if matched else 0.0,
            "click_to_order_pct": round((orders / clicks) * 100, 2) if clicks else 0.0,
            "dm_to_order_pct": round((orders / dms) * 100, 2) if dms else 0.0,
            "handoff_pct": round((handoffs / dms) * 100, 2) if dms else 0.0,
        },
    }
