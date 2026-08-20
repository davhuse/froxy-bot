"""Safe ItemSatis opportunity catalog and manual procurement queue.

This module never buys from ItemSatis.  It creates an auditable admin task and
requires a fresh price/stock confirmation before approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import firestore_helper
from sales_metrics import record_event


CATALOG_PATH = Path(__file__).with_name("supplier_opportunities.json")
QUEUE_DOC = "supplier_procurement_queue_v1"
ALLOWED_HOSTS = {"itemsatis.com", "www.itemsatis.com"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_opportunities() -> dict:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    rows = payload.get("opportunities") or []
    payload["opportunities"] = [row for row in rows if validate_opportunity(row)]
    return payload


def validate_opportunity(row: dict) -> bool:
    if not isinstance(row, dict) or not row.get("id") or not row.get("title"):
        return False
    parsed = urlparse(str(row.get("source_url") or ""))
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def opportunity_by_id(opportunity_id: str) -> dict | None:
    return next(
        (row for row in load_opportunities()["opportunities"] if row["id"] == opportunity_id),
        None,
    )


def _read_queue() -> list[dict]:
    fields = firestore_helper.get_document(QUEUE_DOC) or {}
    try:
        value = json.loads(str(fields.get("items_json") or "[]"))
        return [row for row in value if isinstance(row, dict)]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _write_queue(rows: list[dict]) -> None:
    if not firestore_helper.set_document(
        QUEUE_DOC,
        {"items_json": json.dumps(rows[-500:], ensure_ascii=False, separators=(",", ":"))},
    ):
        raise RuntimeError("Tedarik kuyruğu kalıcı depoya yazılamadı")


def list_procurement_requests() -> list[dict]:
    return sorted(_read_queue(), key=lambda row: row.get("created_at", ""), reverse=True)


def create_procurement_request(opportunity_id: str, customer_reference: str,
                               quantity: int = 1) -> dict:
    opportunity = opportunity_by_id(opportunity_id)
    if not opportunity:
        raise ValueError("Geçersiz tedarik fırsatı")
    quantity = int(quantity)
    if quantity < 1 or quantity > 50:
        raise ValueError("Adet 1-50 arasında olmalı")
    committed = int(opportunity["effective_unit_cost_cents"]) * quantity
    capital_limit = int(load_opportunities().get("working_capital_limit_cents", 30000))
    if committed > capital_limit:
        raise ValueError("İşlem 300 TL döner sermaye sınırını aşıyor")
    customer_hash = hashlib.sha256(str(customer_reference).encode("utf-8")).hexdigest()[:20]
    request_id = "PR-" + secrets.token_hex(4).upper()
    row = {
        "id": request_id,
        "opportunity_id": opportunity_id,
        "title": opportunity["title"],
        "quantity": quantity,
        "expected_cost_cents": committed,
        "customer_key": customer_hash,
        "status": "awaiting_price_stock_check",
        "source_url": opportunity["source_url"],
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = _read_queue()
    rows.append(row)
    _write_queue(rows)
    return row


def update_procurement_request(request_id: str, *, action: str,
                               observed_unit_cost_cents: int | None = None,
                               stock_available: bool | None = None,
                               admin_id: str = "panel") -> dict:
    rows = _read_queue()
    row = next((item for item in rows if item.get("id") == request_id), None)
    if not row:
        raise ValueError("Tedarik kaydı bulunamadı")
    opportunity = opportunity_by_id(str(row.get("opportunity_id")))
    if not opportunity:
        raise ValueError("Tedarik fırsatı artık katalogda yok")
    if observed_unit_cost_cents is not None:
        row["observed_unit_cost_cents"] = int(observed_unit_cost_cents)
    if stock_available is not None:
        row["stock_available"] = bool(stock_available)
    if action == "approve":
        observed = int(row.get("observed_unit_cost_cents") or 0)
        max_cost = round(int(opportunity["effective_unit_cost_cents"]) * 1.10)
        if row.get("stock_available") is not True or observed <= 0:
            raise ValueError("Onaydan önce canlı fiyat ve stok doğrulanmalı")
        if observed > max_cost:
            raise ValueError("Canlı maliyet %10 fiyat artışı sınırını aşıyor")
        row["status"] = "manual_purchase_approved"
    elif action in {"reject", "fulfilled", "refund_required"}:
        row["status"] = action
    elif action == "verify":
        row["status"] = "verified_waiting_admin"
    else:
        raise ValueError("Geçersiz işlem")
    row["admin_id"] = str(admin_id)[:80]
    row["updated_at"] = _now()
    _write_queue(rows)
    if action == "fulfilled":
        unit_cost = int(row.get("observed_unit_cost_cents") or opportunity["effective_unit_cost_cents"])
        record_event(
            "procurement_fulfilled", "supplier",
            product=opportunity["title"],
            amount=round((unit_cost * int(row.get("quantity") or 1)) / 100, 2),
            request_id=request_id,
            source="itemsatis_manual",
        )
    elif action == "refund_required":
        record_event(
            "refund_required", "supplier",
            product=opportunity["title"], request_id=request_id,
            source="itemsatis_manual",
        )
    return row
