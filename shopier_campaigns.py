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
from urllib.parse import quote

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
    def _url(self, brand: str, product_id: str) -> str:
        configured = _endpoint(brand)
        if configured:
            return configured.replace("{id}", quote(str(product_id), safe=""))
        return f"https://api.shopier.com/v1/products/{quote(str(product_id), safe='')}"

    def _request(self, brand: str, product_id: str, *, method: str, payload: dict | None = None) -> dict:
        token = _token(brand)
        if not token:
            raise PriceWriteUnavailable(f"Shopier access token missing for {brand}")
        request = urllib.request.Request(
            self._url(brand, product_id),
            data=(json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None),
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if payload is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", errors="replace")
                body = json.loads(raw) if raw else {}
            return {"ok": True, "status": response.status, "body": body}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            status = getattr(exc, "code", None)
            suffix = f" status={status}" if status else ""
            raise PriceWriteUnavailable(
                f"Shopier product {method} failed for {brand}{suffix}"
            ) from exc

    def update(self, brand: str, product_id: str, new_price: str) -> dict:
        if not _writes_enabled():
            raise PriceWriteUnavailable("SHOPIER_PRICE_WRITES_ENABLED is disabled")
        method = os.environ.get(
            f"SHOPIER_{_brand_key(brand).upper()}_PRODUCT_UPDATE_METHOD", "PUT"
        ).upper()
        if method not in {"PUT", "PATCH"}:
            raise PriceWriteUnavailable(f"Unsupported Shopier update method: {method}")
        return self._request(
            brand,
            product_id,
            method=method,
            payload={"priceData": {"price": str(new_price)}},
        )

    def read(self, brand: str, product_id: str) -> dict:
        if not _writes_enabled():
            raise PriceWriteUnavailable("SHOPIER_PRICE_WRITES_ENABLED is disabled")
        return self._request(brand, product_id, method="GET")

    def verify(self, brand: str, product_id: str, expected_price: str) -> dict:
        result = self.read(brand, product_id)
        body = result.get("body") if isinstance(result, dict) else {}
        price_data = body.get("priceData") if isinstance(body, dict) else {}
        observed = (
            price_data.get("price")
            or price_data.get("discountedPrice")
            or body.get("price")
            if isinstance(body, dict)
            else None
        )
        if observed is None or price_number(observed) != price_number(expected_price):
            raise PriceWriteUnavailable(
                f"Shopier price verification mismatch for {brand}/{product_id}"
            )
        return {"verified": True, "price": str(observed)}


def campaign_status() -> dict:
    state = _load_state()
    # Do not present stale dry-run records as live discounts while the write
    # feature is disabled. They remain persisted for safe migration/cleanup
    # when an explicitly verified write endpoint is enabled.
    if not _writes_enabled():
        state = dict(state)
        state["campaigns"] = {}
        state["state"] = "disabled"
    return state


def _write_verified(
    writer,
    brand: str,
    product_id: str,
    price: str,
    rollback_price: str | None = None,
) -> dict:
    result = writer.update(brand, product_id, price)
    verifier = getattr(writer, "verify", None)
    if callable(verifier):
        try:
            verifier(brand, product_id, price)
        except Exception:
            # A write without a read-back confirmation is not a valid active
            # campaign. Best-effort rollback prevents a stuck low price.
            if rollback_price is not None:
                try:
                    writer.update(brand, product_id, rollback_price)
                except Exception:
                    pass
            raise
    return result


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
                _write_verified(writer, brand, current["product_id"], current["original_price"])
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
        try:
            _write_verified(
                writer,
                brand,
                str(product["id"]),
                new_price,
                rollback_price=original,
            )
        except Exception:
            # Do not persist an active campaign unless Shopier confirms the
            # exact price on a subsequent read.
            raise
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
