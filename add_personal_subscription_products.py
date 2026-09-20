"""Create the new personal Duolingo and Adobe Express products on both stores.

The Shopier tokens are intentionally read from the environment.  The command
is safe to re-run: it reuses a matching local or remote listing instead of
creating another one with the same title.
"""

from __future__ import annotations

import json
from pathlib import Path

from campaign_catalog import CAMPAIGNS
from sync_campaign_shopier import (
    API,
    CATALOGS,
    MEDIA_MAP,
    MINIAPPS,
    ROOT,
    _entry,
    _payload,
    _request,
    _shopier_url,
    _write_catalogs,
)
from upload_campaign_covers import upload


PRODUCT_KEYS = (
    "duolingo_super_12_personal",
    "adobe_express_12_personal",
)


def _remote_products(brand: str) -> list[dict]:
    """Read the first Shopier page for idempotency checks."""
    body = _request(brand, "GET", f"{API}?limit=50&page=1")
    if isinstance(body, list):
        return [row for row in body if isinstance(row, dict)]
    if isinstance(body, dict):
        rows = body.get("products") or body.get("data") or []
        return [row for row in rows if isinstance(row, dict)]
    return []


def _find_local(brand: str, title: str) -> tuple[str, str] | None:
    path = CATALOGS[brand]
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for row in rows:
        if str(row.get("title") or "").strip().casefold() != title.casefold():
            continue
        product_id = str(row.get("id") or "").strip()
        if product_id:
            return product_id, str(row.get("url") or f"https://www.shopier.com/{product_id}")
    return None


def _find_remote(rows: list[dict], title: str) -> tuple[str, str] | None:
    for row in rows:
        if str(row.get("title") or "").strip().casefold() != title.casefold():
            continue
        product_id = str(row.get("id") or "").strip()
        if product_id:
            return product_id, _shopier_url(row, product_id)
    return None


def main() -> int:
    media = {}
    if MEDIA_MAP.exists():
        try:
            media = json.loads(MEDIA_MAP.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            media = {}

    # Upload only the two new covers; existing campaign media is untouched.
    for key in PRODUCT_KEYS:
        if not str(media.get(key) or "").startswith("https://"):
            image_path = ROOT / "miniapp" / "assets" / CAMPAIGNS[key]["image"]
            media[key] = upload(image_path)
            print(f"Kapak yüklendi: {key}")
    MEDIA_MAP.write_text(json.dumps(media, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    results: dict[tuple[str, str], tuple[str, str]] = {}
    for brand in ("keyvadi", "lisansarena"):
        try:
            remote = _remote_products(brand)
        except RuntimeError as exc:
            remote = []
            print(f"[{brand}] mevcut ilan taraması yapılamadı; yeni ilan oluşturulacak: {exc}")
        for key in PRODUCT_KEYS:
            title = CAMPAIGNS[key]["title"]
            existing = _find_local(brand, title) or _find_remote(remote, title)
            if existing:
                results[(brand, key)] = existing
                print(f"[{brand}] mevcut ilan korundu: {key} -> {existing[0]}")
                continue
            body = _request(brand, "POST", API, _payload(key, brand))
            product_id = str(body.get("id") or "").strip()
            if not product_id:
                raise RuntimeError(f"[{brand}] {key} oluşturuldu ancak ID dönmedi")
            url = _shopier_url(body, product_id)
            results[(brand, key)] = (product_id, url)
            print(f"[{brand}] ilan oluşturuldu: {key} -> {product_id}")

    _write_catalogs(results)
    result_rows = []
    for (brand, key), (product_id, url) in sorted(results.items()):
        result_rows.append({"brand": brand, "campaign": key, "id": product_id, "url": url})
    (ROOT / "personal_products_shopier_results.json").write_text(
        json.dumps(result_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Kişisel abonelik ürünleri senkronlandı: {len(result_rows)} mağaza ilanı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
