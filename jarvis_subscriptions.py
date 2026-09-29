"""Single source for JarvisCraft's digital subscription offers.

Shopier IDs are stored only after a listing has been verified. An unpublished
offer remains visible for enquiries but never points to a different product.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "jarvis_subscriptions.json"
SHOPIER_CACHE = ROOT / "jarvis_shopier_products.json"


def load_subscriptions() -> list[dict]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    try:
        published = json.loads(SHOPIER_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        published = []
    by_key = {str(row.get("key")): row for row in published if isinstance(row, dict)}
    result = []
    for item in source:
        row = dict(item)
        row["price_display"] = f"{Decimal(row['price']):.2f}".replace(".", ",") + " TL"
        row["image"] = f"/static/jarvis_subscriptions/{row['key']}-ai.png"
        listing = by_key.get(row["key"], {})
        url = str(listing.get("url") or "")
        row["shopier_id"] = str(listing.get("id") or "") if url else ""
        row["shopier_url"] = url if url.startswith("https://www.shopier.com/") else ""
        result.append(row)
    return result
