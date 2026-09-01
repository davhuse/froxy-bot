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
import time
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
    ("duolingo", ["duolingo", "super duolingo"]),
    ("gemini", ["gemini"]),
    ("claude", ["claude"]),
    ("instagram", ["instagram", "takipci"]),
    ("gmail", ["gmail", "google hesap"]),
]

PRODUCT_GUIDES = {
    "youtube": {
        "redeem_url": "https://youtube.com/redeem",
        "guide": "https://youtube.com/redeem linkinden kodunuzu kullanabilirsiniz. Yeni hesap ve yeni kartla aldığınızdan emin olun.",
        "needs_email": False
    },
    "duolingo": {
        "redeem_url": None,
        "guide": "Bu ürün hesap tanımlamalıdır. Lütfen destek ekibimize sipariş numaranızla birlikte Duolingo'ya kayıtlı E-posta (Mail) adresinizi iletiniz.",
        "needs_email": True
    },
    "gemini": {
        "redeem_url": None,
        "guide": "Bu ürün davet/lisans tanımlamalıdır. Lütfen destek ekibimize sipariş numaranızla birlikte Google (Gmail) E-posta adresinizi iletiniz.",
        "needs_email": True
    },
    "canva": {
        "redeem_url": None,
        "guide": "Gerekli durumlarda destek ekibimize Canva E-posta adresinizi iletebilirsiniz.",
        "needs_email": True
    }
}


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


def allocate_license(product_title_or_id: str, brand: str = "keyvadi") -> dict[str, Any]:
    """
    Attempt to automatically allocate a license key from stock for the given product.
    Supports brand-specific pools (e.g. keyvadi_youtube, lisansarena_youtube),
    redeem URLs, and email delivery routing.
    """
    cat = resolve_category(product_title_or_id)
    b = str(brand or "").lower().strip()
    if "froxy" in b:
        brand_slug = "froxy"
        support_handle = "@FroxyDestekBOT"
    elif "lisans" in b:
        brand_slug = "lisansarena"
        support_handle = "@LisansArenaOnline"
    else:
        brand_slug = "keyvadi"
        support_handle = "@KeyVadiDestek"
    
    guide_info = PRODUCT_GUIDES.get(cat, {}) if cat else {}
    redeem_url = guide_info.get("redeem_url")
    activation_guide = guide_info.get("guide")
    needs_email = guide_info.get("needs_email", False)

    if not cat:
        return {
            "allocated": False,
            "category": None,
            "license_key": None,
            "status": "pending_delivery",
            "delivery_note": f"Manuel teslimat / Temsilci ({support_handle}) iletecektir",
            "support_handle": support_handle,
            "redeem_url": None,
            "activation_guide": None,
            "needs_email": False,
        }

    license_key = None
    pool_key = None
    try:
        import firestore_helper
        if firestore_helper.remote_credentials_configured():
            # A CAS loop makes one stock key consumable by only one Render process.
            for _attempt in range(5):
                stocks, update_time = firestore_helper.get_document_with_meta(
                    "license_stock_v1", quiet=True
                )
                if stocks is None:
                    seeded = load_licenses_stock()
                    claimed = firestore_helper.claim_remote_document(
                        "license_stock_v1", seeded, quiet=True
                    )
                    if claimed is not True:
                        time.sleep(0.05)
                    continue
                brand_cat = f"{brand_slug}_{cat}"
                pool_key = brand_cat if stocks.get(brand_cat) else cat
                keys = list(stocks.get(pool_key, []) or [])
                if not keys:
                    break
                candidate = str(keys.pop(0)).strip()
                updated = dict(stocks)
                updated[pool_key] = keys
                if firestore_helper.compare_and_set_document(
                    "license_stock_v1", updated, update_time, quiet=True
                ) is True:
                    license_key = candidate
                    save_licenses_stock(updated)
                    break
        else:
            with STOCK_LOCK:
                stocks = load_licenses_stock()
                brand_cat = f"{brand_slug}_{cat}"
                pool_key = brand_cat if stocks.get(brand_cat) else cat
                keys = stocks.get(pool_key, [])
                if keys:
                    license_key = str(keys.pop(0)).strip()
                    stocks[pool_key] = keys
                    save_licenses_stock(stocks)
    except Exception:
        # In production, never fall back to ephemeral stock after a durable-store
        # failure; that could deliver the same key twice after a redeploy.
        license_key = None

    if license_key:
        delivery_note = "⚡ 7/24 Anında Otomatik Teslim Edildi"
        if activation_guide:
            delivery_note += f"\n📌 {activation_guide}"
        return {
            "allocated": True,
            "category": cat,
            "pool_key": pool_key,
            "license_key": license_key,
            "status": "delivered",
            "delivery_note": delivery_note,
            "support_handle": support_handle,
            "redeem_url": redeem_url,
            "activation_guide": activation_guide,
            "needs_email": needs_email,
        }

    if needs_email:
        delivery_note = f"Lütfen {support_handle} hesabına sipariş kodunuzla birlikte E-posta (Mail) adresinizi iletiniz; üyeliğiniz hemen tanımlanacaktır."
    else:
        delivery_note = f"Stok hazırlanıyor / Temsilci ({support_handle}) iletecektir"

    return {
        "allocated": False,
        "category": cat,
        "license_key": None,
        "status": "pending_delivery",
        "delivery_note": delivery_note,
        "support_handle": support_handle,
        "redeem_url": redeem_url,
        "activation_guide": activation_guide,
        "needs_email": needs_email,
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
