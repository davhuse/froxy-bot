"""Controlled product catalog for the seven-day sales experiment."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


TEST_FILE = Path(__file__).with_name("sales_test_catalog.json")


def sales_test_mode() -> bool:
    value = os.environ.get("SALES_TEST_MODE", "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    try:
        with open(Path(__file__).with_name("bot_config.json"), "r", encoding="utf-8") as handle:
            configured = json.load(handle).get("sales_test_mode")
            if configured is not None:
                return bool(configured)
    except Exception:
        pass
    # Full catalog is the production default. A reduced catalog is now an
    # explicit maintenance-only opt-in.
    return False


def load_test_catalog() -> list[dict[str, Any]]:
    try:
        with TEST_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return [item for item in data if isinstance(item, dict) and item.get("id") and item.get("url")]
    except Exception:
        return []


def filter_keyvadi_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the full local cache, but expose only the test set to customers."""
    if not sales_test_mode():
        return products
    allowed = {str(item["id"]): item for item in load_test_catalog()}
    if not allowed:
        return products
    by_id = {str(item.get("id")): item for item in products if item.get("id")}
    # Prefer the live catalog's title/price while preserving the tested IDs.
    return [by_id.get(product_id, item) for product_id, item in allowed.items()]
