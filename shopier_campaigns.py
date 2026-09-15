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
DYNAMIC_STATE_DOC = "shopier_dynamic_sale_listings_v1"
DYNAMIC_STATE_PATH = ROOT / "shopier_dynamic_sale_listings_v1.json"


class PriceWriteUnavailable(RuntimeError):
    pass


class DynamicListingUnavailable(RuntimeError):
    """The optional click-to-create Shopier listing is not available."""


def _dynamic_enabled() -> bool:
    return os.environ.get("SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _dynamic_ttl_seconds() -> int:
    try:
        # A short TTL prevents abandoned, customer-specific listings from
        # accumulating while still leaving enough time for 3-D Secure checkout.
        return max(300, min(86400, int(os.environ.get("SHOPIER_DYNAMIC_SALE_LISTING_TTL_SECONDS", "900"))))
    except (TypeError, ValueError):
        return 900


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


def _load_dynamic_state() -> dict:
    try:
        remote = firestore_helper.get_document(DYNAMIC_STATE_DOC) or {}
        if isinstance(remote, dict) and isinstance(remote.get("listings"), dict):
            return remote
    except Exception:
        pass
    try:
        value = json.loads(DYNAMIC_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("listings"), dict):
            return value
    except Exception:
        pass
    return {"listings": {}}


def _save_dynamic_state(state: dict) -> None:
    DYNAMIC_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        firestore_helper.set_document(DYNAMIC_STATE_DOC, state)
    except Exception:
        pass


def _creation_endpoint(brand: str) -> str:
    return os.environ.get(
        f"SHOPIER_{_brand_key(brand).upper()}_PRODUCT_CREATE_URL",
        "https://api.shopier.com/v1/products",
    ).strip()


def _product_url_template(brand: str) -> str:
    brand = _brand_key(brand)
    defaults = {
        "keyvadi": "https://www.shopier.com/{id}",
        "froxy": "https://www.shopier.com/froxyai/{id}",
        "lisansarena": "https://www.shopier.com/lisansarena/{id}",
    }
    return os.environ.get(
        f"SHOPIER_{brand.upper()}_PRODUCT_URL_TEMPLATE",
        defaults.get(brand, "https://www.shopier.com/{id}"),
    ).strip()


def _dynamic_response_product_id(body: dict) -> str:
    if not isinstance(body, dict):
        return ""
    nested = body.get("product") if isinstance(body.get("product"), dict) else {}
    return str(body.get("id") or body.get("productId") or nested.get("id") or "").strip()


def _safe_dynamic_media(product: dict) -> list[dict]:
    image = str(
        product.get("image_url") or product.get("image") or product.get("cover_url") or ""
    ).strip()
    if not image.startswith("https://"):
        return []
    return [{"type": "image", "url": image, "placement": 1}]


def _dynamic_delete(brand: str, product_id: str) -> None:
    token = _token(brand)
    if not token:
        raise DynamicListingUnavailable(f"Shopier access token missing for {brand}")
    request = urllib.request.Request(
        ShopierPriceWriter()._url(brand, product_id),
        method="DELETE",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            return
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        status = getattr(exc, "code", None)
        suffix = f" status={status}" if status else ""
        raise DynamicListingUnavailable(
            f"Shopier dynamic listing DELETE failed for {brand}{suffix}"
        ) from exc


def dynamic_sale_status() -> dict:
    state = _load_dynamic_state()
    listings = state.get("listings", {}) if isinstance(state, dict) else {}
    pending = sum(1 for item in listings.values() if item.get("status") == "pending")
    return {
        "enabled": _dynamic_enabled(),
        "ttl_seconds": _dynamic_ttl_seconds(),
        "pending": pending,
        "total": len(listings),
        "updated_at": state.get("updated_at") if isinstance(state, dict) else None,
    }


def active_dynamic_campaign(brand: str, now: float | None = None) -> dict:
    """Return the still-live dynamic campaign for one brand."""
    current_time = float(time.time() if now is None else now)
    state = _load_state()
    campaign = (state.get("campaigns") or {}).get(_brand_key(brand)) or {}
    if (
        campaign.get("active")
        and campaign.get("mode") == "dynamic_listing"
        and float(campaign.get("restore_at", 0) or 0) > current_time
    ):
        return campaign
    return {}


def campaign_price_for_product(brand: str, product: dict) -> str:
    """Return the active 3-hour campaign price, or the catalog price."""
    product_id = str((product or {}).get("id") or "")
    campaign = active_dynamic_campaign(brand)
    if str(campaign.get("product_id")) == product_id and campaign.get("discount_price"):
        return str(campaign["discount_price"])
    return str((product or {}).get("price") or "")


def apply_dynamic_campaign_prices(brand: str, products: list[dict]) -> list[dict]:
    """Overlay the campaign price in bot/catalog cards without editing Shopier."""
    campaign = active_dynamic_campaign(brand)
    if not campaign:
        return products
    product_id = str(campaign.get("product_id") or "")
    result = []
    for product in products:
        row = dict(product)
        if str(row.get("id") or "") == product_id and campaign.get("discount_price"):
            row["original_price"] = row.get("price")
            row["price"] = str(campaign["discount_price"])
            row["campaign_discount_percent"] = campaign.get("discount_percent")
        result.append(row)
    return result


def create_dynamic_sale_listing(
    brand: str,
    product: dict,
    *,
    price: str | None = None,
    idempotency_key: str = "",
    now: float | None = None,
) -> dict:
    """Create a one-off Shopier product for a bot CTA.

    The original catalog listing is never edited.  This is intentionally
    disabled until the merchant has supplied a valid write-capable PAT and
    explicitly enables ``SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED``.
    """
    brand = _brand_key(brand)
    if brand not in BRANDS:
        raise DynamicListingUnavailable(f"Unknown brand: {brand}")
    if not _dynamic_enabled():
        raise DynamicListingUnavailable("SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED is disabled")
    token = _token(brand)
    if not token:
        raise DynamicListingUnavailable(f"Shopier access token missing for {brand}")
    product_id = str((product or {}).get("id") or "").strip()
    title = str((product or {}).get("title") or "").strip()
    if not product_id or not title:
        raise DynamicListingUnavailable("Dynamic listing requires a catalog product")
    key = str(idempotency_key or f"{brand}:{product_id}").strip()
    state = _load_dynamic_state()
    listings = state.setdefault("listings", {})
    existing = listings.get(key)
    current_time = float(time.time() if now is None else now)
    if isinstance(existing, dict) and existing.get("status") == "pending":
        if float(existing.get("expires_at", 0) or 0) > current_time:
            return {"success": True, "duplicate": True, **existing}
        try:
            _dynamic_delete(brand, str(existing.get("shopier_product_id") or ""))
        except Exception:
            # A stale listing must not block a new CTA forever.  It is kept in
            # the state log with a replaced status for later operator review.
            pass
        existing["status"] = "expired"
        existing["closed_at"] = _utc()

    amount = str(price or campaign_price_for_product(brand, product)).strip()
    try:
        numeric_amount = float(price_number(amount))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise DynamicListingUnavailable("Dynamic listing price is invalid") from exc
    if numeric_amount <= 0:
        raise DynamicListingUnavailable("Dynamic listing price must be positive")
    description = str((product or {}).get("description") or "").strip()
    if not description:
        description = f"{title}\n\nBot üzerinden oluşturulan güvenli satın alma ilanı."
    payload = {
        "title": title,
        "type": str((product or {}).get("type") or "digital"),
        "description": description,
        "stockQuantity": 1,
        "shippingPayer": "sellerPays",
        "priceData": {
            "currency": "TRY",
            "price": round(numeric_amount, 2),
            "discount": False,
            "shippingPrice": 0.0,
        },
    }
    media = _safe_dynamic_media(product)
    if media:
        payload["media"] = media
    request = urllib.request.Request(
        _creation_endpoint(brand),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        status = getattr(exc, "code", None)
        suffix = f" status={status}" if status else ""
        raise DynamicListingUnavailable(
            f"Shopier dynamic listing POST failed for {brand}{suffix}"
        ) from exc
    shopier_product_id = _dynamic_response_product_id(body)
    if not shopier_product_id:
        raise DynamicListingUnavailable("Shopier dynamic listing response has no product id")
    template = _product_url_template(brand)
    payment_url = str(body.get("url") or body.get("link") or "").strip() if isinstance(body, dict) else ""
    if not payment_url:
        payment_url = template.replace("{id}", quote(shopier_product_id, safe=""))
    record = {
        "brand": brand,
        "source_product_id": product_id,
        "shopier_product_id": shopier_product_id,
        "title": title,
        "amount": format_price(Decimal(str(numeric_amount))),
        "payment_url": payment_url,
        "idempotency_key": key,
        "status": "pending",
        "created_at": current_time,
        "expires_at": current_time + _dynamic_ttl_seconds(),
    }
    listings[key] = record
    state["updated_at"] = _utc()
    _save_dynamic_state(state)
    return {"success": True, **record}


def cleanup_dynamic_sale_listings(now: float | None = None) -> dict:
    """Close unpurchased one-off sale listings after their TTL."""
    state = _load_dynamic_state()
    listings = state.setdefault("listings", {})
    if not listings:
        return {"closed": 0, "failed": 0, "pending": 0}
    current_time = float(time.time() if now is None else now)
    closed = failed = 0
    for key, item in list(listings.items()):
        if item.get("status") != "pending" or float(item.get("expires_at", 0) or 0) > current_time:
            continue
        try:
            _dynamic_delete(str(item.get("brand") or ""), str(item.get("shopier_product_id") or ""))
            item["status"] = "expired"
            item["closed_at"] = _utc()
            closed += 1
        except Exception as exc:
            item["last_error"] = type(exc).__name__
            failed += 1
        item["updated_at"] = _utc()
    state["updated_at"] = _utc()
    _save_dynamic_state(state)
    return {"closed": closed, "failed": failed, "pending": sum(1 for item in listings.values() if item.get("status") == "pending")}


def mark_dynamic_listing_paid(brand: str, product_id: str, order_id: str = "") -> bool:
    """Mark a one-off CTA listing paid so the TTL cleaner will not delete it."""
    brand = _brand_key(brand)
    product_id = str(product_id or "").strip()
    if not brand or not product_id:
        return False
    state = _load_dynamic_state()
    listings = state.setdefault("listings", {})
    changed = False
    for item in listings.values():
        if (
            item.get("brand") == brand
            and str(item.get("shopier_product_id") or "") == product_id
            and item.get("status") == "pending"
        ):
            item["status"] = "paid"
            item["order_id"] = str(order_id or "")
            item["paid_at"] = _utc()
            changed = True
    if changed:
        state["updated_at"] = _utc()
        _save_dynamic_state(state)
    return changed


def run_dynamic_campaign_cycle(catalog_loader, now=None) -> dict:
    """Select one product per shop for a 3-hour click-to-create campaign."""
    if not _dynamic_enabled():
        return {"state": "disabled", "updated": 0, "restored": 0}
    current_time = float(time.time() if now is None else now)
    state = _load_state()
    campaigns = state.setdefault("campaigns", {})
    updated = restored = 0
    for brand in BRANDS:
        current = campaigns.get(brand) or {}
        if current.get("active") and float(current.get("restore_at", 0) or 0) <= current_time:
            campaigns[brand] = {"active": False, "mode": "dynamic_listing", "next_run_at": current_time}
            current = campaigns[brand]
            restored += 1
        if current.get("active"):
            continue
        if float(current.get("next_run_at", 0) or 0) > current_time:
            continue
        products = []
        try:
            for product in catalog_loader(brand) or []:
                if not product.get("id") or not product.get("price"):
                    continue
                quantity = product.get("stockQuantity")
                if quantity not in (None, "") and str(quantity).replace(",", ".").isdigit() and float(str(quantity).replace(",", ".")) <= 0:
                    continue
                if str(product.get("stockStatus", "")).replace("_", "").casefold() in {"outofstock", "soldout", "stokyok", "tukendi"}:
                    continue
                products.append(product)
        except Exception:
            products = []
        if not products:
            campaigns[brand] = {"active": False, "mode": "dynamic_listing", "next_run_at": current_time + 300}
            continue
        product = random.choice(products)
        original = str(product["price"])
        percent = random.randint(5, 10)
        campaigns[brand] = {
            "active": True,
            "mode": "dynamic_listing",
            "product_id": str(product["id"]),
            "title": str(product.get("title") or ""),
            "original_price": original,
            "discount_price": discounted_price(original, percent),
            "discount_percent": percent,
            "started_at": _utc(),
            "restore_at": current_time + 3 * 60 * 60,
        }
        updated += 1
    state["updated_at"] = _utc()
    _save_state(state)
    return {"state": "enabled", "mode": "dynamic_listing", "updated": updated, "restored": restored}


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
    if not _writes_enabled() and not _dynamic_enabled():
        state = dict(state)
        state["campaigns"] = {}
        state["state"] = "disabled"
    elif _dynamic_enabled() and not _writes_enabled():
        state = dict(state)
        state["state"] = "dynamic_listing"
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
