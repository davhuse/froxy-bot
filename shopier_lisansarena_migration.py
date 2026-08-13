"""Prepare and safely finalize LisansArena's balance-only Shopier catalog.

The destructive finalize command refuses to run until a real, paid 100 TL
balance order is fetched from Shopier and verified.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


API = "https://api.shopier.com/v1"
ROOT = Path(__file__).resolve().parent
LEGACY_FILE = ROOT / "lisansarena_shopier_links.json"
MAPPING_FILE = ROOT / "lisansarena_topup_products.json"
ARCHIVE_DIR = ROOT / "shopier_archives"
AMOUNTS = (100, 200, 500, 1000, 2000, 5000)


def token():
    value = os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN", "").strip()
    if not value:
        raise SystemExit("SHOPIER_LISANSARENA_ACCESS_TOKEN eksik")
    return value


def api(path, method="GET", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        API + path, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "LisansArena-Migration/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Shopier API {exc.code}: {detail}") from exc


def rows(payload):
    if isinstance(payload, list):
        return payload
    return payload.get("data") or payload.get("products") or payload.get("orders") or []


def backup(products):
    ARCHIVE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = ARCHIVE_DIR / f"lisansarena-products-{stamp}.json"
    destination.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def list_products():
    return rows(api("/products?limit=100"))


def prepare():
    current = list_products()
    archive = backup(current)
    by_title = {str(item.get("title") or "").strip(): item for item in current}
    mapping = {}
    for amount in AMOUNTS:
        title = f"LisansArena {amount:,} TL Bakiye".replace(",", ".")
        product = by_title.get(title)
        if product is None:
            price = f"{amount:.2f}"
            product = api("/products", "POST", {
                "title": title,
                "description": (
                    "Yalnız LisansArena Telegram Mini App bakiyesi içindir. "
                    "Mini App'in oluşturduğu 24 saat geçerli LA-XXXXXX kodunu "
                    "sipariş notuna yazın. Hatalı veya eksik kodlar otomatik yüklenmez."
                ),
                "type": "digital",
                "priceData": {
                    "currency": "TRY", "price": price, "discount": False,
                    "discountedPrice": price, "shippingPrice": "0.00",
                },
                "stockQuantity": 99999,
                "shippingPayer": "sellerPays",
            })
        product_id = str(product.get("id") or "")
        if not product_id:
            raise RuntimeError(f"{title} ürün kimliği alınamadı")
        mapping[str(amount)] = product_id
    MAPPING_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(archive), "topup_products": mapping}, ensure_ascii=False))


def paid_100_try_order(order_id, mapping):
    order = api(f"/orders/{urllib.parse.quote(str(order_id), safe='')}")
    status = str(order.get("paymentStatus") or order.get("status") or "").casefold()
    total = str((order.get("totals") or {}).get("total") or order.get("total") or order.get("amount") or "")
    try:
        amount = float(total.replace(",", "."))
    except ValueError:
        amount = -1
    items = order.get("lineItems") or order.get("items") or []
    ids = {str(item.get("productId") or item.get("product_id") or item.get("id") or "") for item in items if isinstance(item, dict)}
    note = str(order.get("note") or order.get("orderNote") or order.get("buyerNote") or "")
    return (
        status == "paid" and abs(amount - 100.0) < 0.001 and
        str(mapping.get("100")) in ids and
        bool(re.search(r"\bLA-[A-F0-9]{6}\b", note.upper()))
    )


def finalize(order_id):
    if not MAPPING_FILE.exists():
        raise SystemExit("Önce prepare çalıştırılmalı")
    mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    if not paid_100_try_order(order_id, mapping):
        raise SystemExit("Silme reddedildi: gerçek, ödenmiş 100 TL LA kodlu test siparişi doğrulanamadı")
    current = list_products()
    archive = backup(current)
    protected = set(mapping.values())
    legacy_ids = {str(item.get("id") or "") for item in json.loads(LEGACY_FILE.read_text(encoding="utf-8"))}
    deleted = []
    for product in current:
        product_id = str(product.get("id") or "")
        if product_id in legacy_ids and product_id not in protected:
            api(f"/products/{urllib.parse.quote(product_id, safe='')}", "DELETE")
            deleted.append(product_id)
    print(json.dumps({"archive": str(archive), "deleted_legacy_ids": deleted, "remaining_balance_ids": sorted(protected)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("prepare")
    finish = sub.add_parser("finalize")
    finish.add_argument("--verified-order", required=True)
    args = parser.parse_args()
    if args.command == "status":
        current = list_products()
        print(json.dumps({"count": len(current), "products": current}, ensure_ascii=False))
    elif args.command == "prepare":
        prepare()
    else:
        finalize(args.verified_order)


if __name__ == "__main__":
    main()
