"""Fail-closed Shopier price campaign scheduler.

Shopier write routes differ by app/merchant configuration. The adapter only
operates when an explicit write endpoint and the global feature flag are set;
otherwise no customer-facing price is changed.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import time
import urllib.error
import urllib.request

import firestore_helper


ROOT = Path(__file__).resolve().parent
BRANDS = ("keyvadi", "froxy", "lisansarena")
STATE_DOC = "shopier_discount_campaigns_v1"
STATE_PATH = ROOT / "shopier_discount_campaigns_v1.json"


class PriceWriteUnavailable(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _brand_key(brand: str) -> str:
    return str(brand or "").strip().lower()


def _token(brand: str) -> str:
    key = {
        "keyvadi": "SHOPIER_KEYVADI_ACCESS_TOKEN",
        "froxy": "SHOPIER_FROXY_ACCESS_TOKEN",
        "lisansarena": "SHOPIER_LISANSARENA_ACCESS_TOKEN",
    }.get(_brand_key(brand), "")
    return os.environ.get(key, "").strip()


def _endpoint(brand: str) -> str:
    return os.environ.get(
        f"SHOPIER_{_brand_key(brand).upper()}_PRODUCT_UPDATE_URL", ""
    ).strip()


def _writes_enabled() -> bool:
    return os.environ.get("SHOPIER_PRICE_WRITES_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def price_number(value) -> Decimal:
    text = str(value or "").replace("₺", "").replace("TL", "").strip()
    text = text.replace(".", "").replace(",", ".") if text.count(",") == 1 else text
    filtered = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
    if not filtered:
        raise ValueError(f"Invalid product price: {value}")
    return Decimal(filtered)


def format_price(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def discounted_price(original, percentage: int) -> str:
    original_value = price_number(original)
    percentage = max(5, min(10, int(percentage)))
    result = original_value * (Decimal(100 - percentage) / Decimal(100))
    floor = original_value * Decimal("0.90")
    return format_price(max(result, floor))


def _load_state() -> dict:
    try:
        remote = firestore_helper.get_document(STATE_DOC) or {}
        if isinstance(remote, dict) and isinstance(remote.get("campaigns"), dict):
            return remote
    except Exception:
        pass
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("campaigns"), dict):
            return value
    except Exception:
        pass
    return {"campaigns": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        firestore_helper.set_document(STATE_DOC, state)
    except Exception:
        pass


class ShopierPriceWriter:
    def update(self, brand: str, product_id: str, new_price: str) -> dict:
        if not _writes_enabled():
            raise PriceWriteUnavailable("SHOPIER_PRICE_WRITES_ENABLED is disabled")
        token = _token(brand)
        endpoint = _endpoint(brand)
        if not token or not endpoint:
            raise PriceWriteUnavailable(f"Shopier write endpoint/token missing for {brand}")
        method = os.environ.get(
            f"SHOPIER_{_brand_key(brand).upper()}_PRODUCT_UPDATE_METHOD", "PATCH"
        ).upper()
        payload = {"id": str(product_id), "price": str(new_price)}
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "body": body[:1000]}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise PriceWriteUnavailable(f"Shopier price update failed: {type(exc).__name__}") from exc


def campaign_status() -> dict:
    return _load_state()


def run_campaign_cycle(catalog_loader, price_writer=None, now=None) -> dict:
    """Apply/restore campaigns when enabled; otherwise report a safe no-op."""
    if not _writes_enabled():
        return {"state": "disabled", "updated": 0, "restored": 0}
    now = float(time.time() if now is None else now)
    writer = price_writer or ShopierPriceWriter()
    state = _load_state()
    campaigns = state.setdefault("campaigns", {})
    updated = restored = 0
    for brand in BRANDS:
        current = campaigns.get(brand) or {}
        if current.get("active") and float(current.get("restore_at", 0) or 0) <= now:
            # Never restore an orphaned/stale record (for example after a
            # failed dry-run) against a newly reused Shopier product id.
            try:
                known_ids = {
                    str(product.get("id"))
                    for product in (catalog_loader(brand) or [])
                    if product.get("id")
                }
            except Exception:
                known_ids = set()
            if str(current.get("product_id")) not in known_ids:
                campaigns[brand] = {"active": False, "next_run_at": now}
                current = campaigns[brand]
            else:
                writer.update(brand, current["product_id"], current["original_price"])
                current = {"active": False, "next_run_at": now}
                campaigns[brand] = current
                restored += 1
        if current.get("active"):
            continue
        next_run = float(current.get("next_run_at", 0) or 0)
        if next_run and next_run > now:
            continue
        products = [p for p in (catalog_loader(brand) or []) if p.get("id") and p.get("price")]
        eligible = []
        for product in products:
            if str(product.get("stockStatus", "")).replace("_", "").lower() in {
                "outofstock", "soldout", "stokyok", "tukendi",
            }:
                continue
            quantity = product.get("stockQuantity")
            if quantity not in (None, ""):
                try:
                    if int(float(str(quantity).replace(",", "."))) <= 0:
                        continue
                except (TypeError, ValueError):
                    # A non-numeric quantity is not enough evidence to hide a
                    # product; Shopier may return values such as "unlimited".
                    pass
            eligible.append(product)
        products = eligible
        if not products:
            campaigns[brand] = {"active": False, "next_run_at": now + 300}
            continue
        product = random.choice(products)
        original = str(product["price"])
        percent = random.randint(5, 10)
        new_price = discounted_price(original, percent)
        writer.update(brand, str(product["id"]), new_price)
        campaigns[brand] = {
            "active": True,
            "product_id": str(product["id"]),
            "title": str(product.get("title") or ""),
            "original_price": original,
            "discount_price": new_price,
            "discount_percent": percent,
            "started_at": _utc(),
            "restore_at": now + 3 * 60 * 60,
        }
        updated += 1
    state["updated_at"] = _utc()
    _save_state(state)
    return {"state": "enabled", "updated": updated, "restored": restored}
