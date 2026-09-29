"""Idempotently publish Jarvis subscription listings with their cover images.

Dry run is the default. Publishing requires SHOPIER_JARVIS_ACCESS_TOKEN and
either a public image base URL or the existing Uguu image uploader.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jarvis_subscriptions import load_subscriptions  # noqa: E402
from upload_campaign_covers import upload as upload_to_uguu  # noqa: E402


API = "https://api.shopier.com/v1"
CACHE = ROOT / "jarvis_shopier_products.json"


def request_json(token: str, method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "JarvisCraft-catalog-sync/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Shopier {method} {path} HTTP {exc.code}: {detail}") from exc
    return json.loads(body) if body else {}


def list_all(token: str) -> list[dict]:
    rows = []
    for page in range(1, 101):
        result = request_json(token, "GET", f"/products?limit=50&page={page}")
        batch = result if isinstance(result, list) else result.get("data") or result.get("products") or []
        if not isinstance(batch, list):
            raise RuntimeError("Shopier returned an invalid product list")
        rows.extend(batch)
        if len(batch) < 50:
            break
    return rows


def save_cache(rows: list[dict]) -> None:
    temporary = CACHE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, CACHE)


def public_image_url(item: dict, base_url: str) -> str:
    if base_url:
        return base_url.rstrip("/") + item["image"]
    local_path = ROOT / item["image"].lstrip("/")
    if not local_path.is_file():
        raise FileNotFoundError(local_path)
    return upload_to_uguu(local_path)


def payload_for(item: dict, image_url: str) -> dict:
    return {
        "title": item["title"],
        "type": "digital",
        "description": item["description"],
        "priceData": {
            "currency": "TRY",
            "price": item["price"],
            "discount": False,
            "discountedPrice": item["price"],
            "shippingPrice": "0.00",
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays",
        "media": [{"type": "image", "url": image_url, "placement": 1}],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Write listings to JarvisStore")
    parser.add_argument("--image-base-url", default="", help="Public base serving /static/jarvis_subscriptions")
    parser.add_argument("--only", nargs="*", help="Publish only the specified subscription keys")
    args = parser.parse_args()
    products = load_subscriptions()
    if args.only:
        wanted = set(args.only)
        products = [item for item in products if item["key"] in wanted]
        if len(products) != len(wanted):
            raise SystemExit("An unknown subscription key was passed to --only")
    for item in products:
        print(f"{item['key']}: {item['title']} | {item['price_display']} | {item['warranty'] or 'garanti belirtilmedi'}")
    if not args.publish:
        print(f"Dry run: {len(products)} listings; nothing was sent to Shopier.")
        return

    token = os.environ.get("SHOPIER_JARVIS_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("SHOPIER_JARVIS_ACCESS_TOKEN is required for --publish")
    try:
        existing = list_all(token)
    except RuntimeError as exc:
        if "HTTP 403" not in str(exc):
            raise
        print("Shopier product reads returned 403; resuming from the local verified ID cache.")
        existing = []
    by_title = {str(row.get("title") or row.get("name") or "").strip().casefold(): row for row in existing}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
    by_key = {str(row.get("key")): row for row in cache if isinstance(row, dict)}

    for item in products:
        match = by_key.get(item["key"]) or by_title.get(item["title"].casefold())
        product_id = str((match or {}).get("id") or "").strip()
        if match and all(match.get(field) == item[value] for field, value in (
            ("title", "title"), ("price", "price_display"), ("description", "description"),
            ("image", "image"), ("delivery", "delivery"), ("warranty", "warranty")
        )) and match.get("url"):
            print(f"Already published {item['key']}: {match['url']}")
            continue
        image_url = public_image_url(item, args.image_base_url)
        payload = payload_for(item, image_url)
        method = "PUT" if product_id else "POST"
        path = f"/products/{product_id}" if product_id else "/products"
        result = request_json(token, method, path, payload)
        actual_id = str(result.get("id") or product_id or "")
        if not actual_id:
            raise RuntimeError(f"Shopier did not return an ID for {item['key']}")
        try:
            verified = request_json(token, "GET", f"/products/{actual_id}")
        except RuntimeError as exc:
            if "HTTP 403" not in str(exc):
                raise
            verified = result
            print(f"Shopier product read returned 403; checking the write response for {item['key']}.")
        title = str(verified.get("title") or verified.get("name") or "")
        price_data = verified.get("priceData") or {}
        actual_price = str(price_data.get("price") or "").replace(",", ".")
        actual_desc = str(verified.get("description") or "")
        if title != item["title"] or Decimal(actual_price) != Decimal(item["price"]) or actual_desc != item["description"]:
            raise RuntimeError(f"Verification failed for {item['key']} ({actual_id})")
        if not verified.get("media"):
            raise RuntimeError(f"Cover image missing for {item['key']} ({actual_id})")
        url = str(verified.get("url") or verified.get("link") or f"https://www.shopier.com/{actual_id}")
        by_key[item["key"]] = {
            "key": item["key"],
            "id": actual_id,
            "title": item["title"],
            "price": item["price_display"],
            "url": url,
            "description": item["description"],
            "image": item["image"],
            "delivery": item["delivery"],
            "warranty": item["warranty"],
        }
        cache = [row for row in cache if row.get("key") != item["key"]]
        cache.append(by_key[item["key"]])
        save_cache(cache)
        print(f"Verified API product {method} {item['key']}: {url}")


if __name__ == "__main__":
    main()
