# -*- coding: utf-8 -*-
"""
License Delivery & Stock Pool Manager.
Provides thread-safe allocation of digital license keys and accounts from licenses.json
for KeyVadi, LisansArena, and Froxy Mini Apps and Telegram Bots.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
LICENSES_FILE = BASE_DIR / "licenses.json"
STOCK_LOCK = threading.RLock()

# Default category mappings based on keywords
CATEGORY_KEYWORDS = [
    ("canva", ["canva"]),
    ("adobe", ["adobe", "creative cloud", "photoshop", "illustrator"]),
    ("windows", ["windows", "win 11", "win 10", "win11", "win10"]),
    ("office", ["office", "365", "word", "excel", "powerpoint"]),
    ("netflix", ["netflix"]),
    ("youtube", ["youtube", "premium"]),
    ("spotify", ["spotify"]),
    ("steam", ["steam", "random key"]),
    ("minecraft", ["minecraft", "cape", "pelerin"]),
    ("capcut", ["capcut"]),
    ("exxen", ["exxen"]),
    ("prime", ["prime", "amazon prime"]),
    ("hbo", ["hbo", "max"]),
    ("roblox", ["roblox", "robux"]),
    ("envato", ["envato"]),
    ("freepik", ["freepik"]),
    ("chatgpt", ["chatgpt", "gpt-4", "chat gpt", "openai"]),
    ("gemini", ["gemini"]),
    ("claude", ["claude"]),
    ("instagram", ["instagram", "takipci"]),
    ("gmail", ["gmail", "google hesap"]),
]


def resolve_category(product_text: str) -> str | None:
    if not product_text:
        return None
    normalized = product_text.lower().strip()
    for cat, keywords in CATEGORY_KEYWORDS:
        if any(kw in normalized for kw in keywords):
            return cat
    return None


def load_licenses_stock() -> dict[str, list[str]]:
    with STOCK_LOCK:
        if LICENSES_FILE.exists():
            try:
                with open(LICENSES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
    return {}


def save_licenses_stock(data: dict[str, list[str]]) -> None:
    with STOCK_LOCK:
        fd, tmp_path = tempfile.mkstemp(prefix="licenses_", suffix=".json", dir=str(BASE_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, LICENSES_FILE)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


def allocate_license(product_title_or_id: str) -> dict[str, Any]:
    """
    Attempt to automatically allocate a license key from stock for the given product.
    Returns a dict with allocation details.
    """
    cat = resolve_category(product_title_or_id)
    if not cat:
        return {
            "allocated": False,
            "category": None,
            "license_key": None,
            "status": "pending_delivery",
            "delivery_note": "Manuel teslimat / Hazırlanıyor",
        }

    with STOCK_LOCK:
        stocks = load_licenses_stock()
        keys = stocks.get(cat, [])
        if keys:
            license_key = str(keys.pop(0)).strip()
            stocks[cat] = keys
            save_licenses_stock(stocks)
            return {
                "allocated": True,
                "category": cat,
                "license_key": license_key,
                "status": "delivered",
                "delivery_note": "⚡ 7/24 Anında Otomatik Teslim Edildi",
            }

    return {
        "allocated": False,
        "category": cat,
        "license_key": None,
        "status": "pending_delivery",
        "delivery_note": "Stok hazırlanıyor / Canlı destek iletecektir",
    }


def add_licenses_to_stock(category: str, keys: list[str]) -> int:
    """Add a list of license keys to the stock pool for a category."""
    cat = category.lower().strip()
    clean_keys = [k.strip() for k in keys if k and k.strip()]
    if not clean_keys:
        return 0

    with STOCK_LOCK:
        stocks = load_licenses_stock()
        existing = stocks.setdefault(cat, [])
        existing.extend(clean_keys)
        save_licenses_stock(stocks)
    return len(clean_keys)


def get_stock_summary() -> dict[str, int]:
    stocks = load_licenses_stock()
    return {cat: len(keys) for cat, keys in stocks.items()}
