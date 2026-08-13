"""Shopier order ingestion shared by webhooks and periodic reconciliation."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import firestore_helper
from sales_metrics import record_event


def _order_fields(order: dict) -> dict:
    shipping = order.get("shippingInfo") if isinstance(order.get("shippingInfo"), dict) else {}
    totals = order.get("totals") if isinstance(order.get("totals"), dict) else {}
    line_items = order.get("lineItems") if isinstance(order.get("lineItems"), list) else []
    titles = [str(item.get("title") or "").strip() for item in line_items if isinstance(item, dict)]
    return {
        "order_id": str(order.get("id") or order.get("platform_order_id") or "").strip(),
        "email": str(shipping.get("email") or order.get("email") or "").strip().lower(),
        "phone": str(shipping.get("phone") or order.get("phone") or "").strip(),
        "product_name": ", ".join(title for title in titles if title) or str(order.get("product_name") or ""),
        "amount": str(totals.get("total") or order.get("total_amount") or "0"),
        "payment_status": str(order.get("paymentStatus") or "paid").lower(),
    }


def ingest_shopier_order(order: dict, account: str, source: str) -> bool:
    """Persist one paid order once. Returns True only for a newly ingested order."""
    fields = _order_fields(order)
    order_id = fields["order_id"]
    if not order_id or fields["payment_status"] != "paid":
        return False
    claim_id = "shopier_order_" + re.sub(r"[^a-zA-Z0-9_-]+", "_", order_id)
    claimed = firestore_helper.claim_document(claim_id, {
        "order_id": order_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    })
    if claimed is False:
        return False

    order_record = {
        "order_id": order_id,
        "product_name": fields["product_name"],
        "amount": fields["amount"],
        "claimed": False,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    email = fields["email"]
    if email:
        doc_id = "order_email_" + email.replace("@", "_").replace(".", "_")
        document = firestore_helper.get_document(doc_id) or {"orders": []}
        if not any(str(item.get("order_id")) == order_id for item in document.get("orders", [])):
            document.setdefault("orders", []).append(order_record)
            firestore_helper.set_document(doc_id, document)
    phone = fields["phone"].replace("+", "").replace(" ", "").strip()
    if phone:
        doc_id = "order_phone_" + phone
        document = firestore_helper.get_document(doc_id) or {"orders": []}
        if not any(str(item.get("order_id")) == order_id for item in document.get("orders", [])):
            document.setdefault("orders", []).append(order_record)
            firestore_helper.set_document(doc_id, document)

    try:
        amount = float(fields["amount"].replace(",", "."))
    except (TypeError, ValueError):
        amount = 0.0
    record_event(
        "shopier_order", account or "Shopier", amount=amount,
        product=fields["product_name"], status="paid", source=source,
    )
    return True


def reconcile_shopier_orders(brand: str) -> int:
    """Import recent paid orders when the brand's PAT is configured."""
    brand = str(brand).lower()
    token_key = "SHOPIER_KEYVADI_ACCESS_TOKEN" if brand == "keyvadi" else "SHOPIER_FROXY_ACCESS_TOKEN"
    token = os.environ.get(token_key, "").strip()
    if not token:
        return 0
    date_start = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S%z")
    query = urllib.parse.urlencode({"limit": 100, "dateStart": date_start})
    request = urllib.request.Request(
        f"https://api.shopier.com/v1/orders?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    orders = payload if isinstance(payload, list) else payload.get("data") or payload.get("orders") or []
    account = "KeyVadi" if brand == "keyvadi" else "Froxy AI"
    return sum(1 for order in orders if isinstance(order, dict) and ingest_shopier_order(order, account, "api_reconciliation"))


def reconcile_configured_orders() -> dict[str, int]:
    results = {}
    for brand in ("keyvadi", "froxy"):
        try:
            results[brand] = reconcile_shopier_orders(brand)
        except Exception:
            results[brand] = 0
    return results
