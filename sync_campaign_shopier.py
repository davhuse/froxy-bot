"""Create/update the campaign catalogue through the Shopier REST API.

Usage (tokens are intentionally supplied through the environment):

    $env:SHOPIER_KEYVADI_ACCESS_TOKEN = "..."
    $env:SHOPIER_LISANSARENA_ACCESS_TOKEN = "..."
    python sync_campaign_shopier.py

The command is idempotent for the known existing listings and records the
returned Shopier IDs in both storefront catalogues.  It never prints tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from campaign_catalog import CAMPAIGNS, api_media_url, price_text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
API = "https://api.shopier.com/v1/products"
MEDIA_MAP = ROOT / "campaign_media_urls.json"
CATALOGS = {
    "keyvadi": ROOT / "keyvadi_shopier_links.json",
    "lisansarena": ROOT / "lisansarena_shopier_links.json",
}
MINIAPPS = {
    "keyvadi": ROOT / "miniapp" / "products_db.json",
    "lisansarena": ROOT / "miniapp_lisansarena" / "products_db.json",
}

# Product IDs already present in the local catalog.  LA had two historical
# records for the 450/350 listing; the script updates the first ID that belongs
# to the account and leaves the foreign/duplicate local record out.
KNOWN_IDS = {
    ("keyvadi", "yemeksepeti_450"): ["50576030"],
    ("keyvadi", "trendyol_market_800"): ["47669486"],
    ("lisansarena", "yemeksepeti_450"): ["50857165", "50821372"],
}


def _token(brand: str) -> str:
    name = "SHOPIER_KEYVADI_ACCESS_TOKEN" if brand == "keyvadi" else "SHOPIER_LISANSARENA_ACCESS_TOKEN"
    return os.environ.get(name, "").strip()


def _request(brand: str, method: str, url: str, payload: dict | None = None) -> dict:
    token = _token(brand)
    if not token:
        raise RuntimeError(f"{brand} Shopier access token is missing")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "tg-bot-reklam-campaign-sync/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8", errors="replace").strip()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Shopier {method} {url.rsplit('/', 1)[-1]} HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Shopier {method} bağlantı hatası: {exc.reason}") from exc


def _payload(key: str, brand: str) -> dict:
    campaign = CAMPAIGNS[key]
    value = float(campaign["prices"][brand])
    price = f"{value:.2f}"
    return {
        "title": campaign["title"],
        "type": "digital",
        "description": campaign["description"],
        "media": [{"type": "image", "url": _media_url(key), "placement": 1}],
        "priceData": {
            "currency": "TRY",
            "price": price,
            "discount": False,
            "discountedPrice": price,
            "shippingPrice": "0.00",
        },
        "stockQuantity": 999,
        "shippingPayer": "sellerPays",
    }


def _media_url(key: str) -> str:
    """Return an API-reachable image URL, preferring the uploaded CDN map."""
    try:
        mapping = json.loads(MEDIA_MAP.read_text(encoding="utf-8"))
        value = str(mapping.get(key) or "").strip()
        if value.startswith("https://"):
            return value
    except (OSError, ValueError):
        pass
    return api_media_url(key)


def _shopier_url(body: dict, product_id: str) -> str:
    return str(body.get("url") or f"https://www.shopier.com/{product_id}").strip()


def _update_existing(brand: str, key: str) -> tuple[str, str] | None:
    for product_id in KNOWN_IDS.get((brand, key), []):
        try:
            body = _request(brand, "PUT", f"{API}/{product_id}", _payload(key, brand))
            actual_id = str(body.get("id") or product_id)
            return actual_id, _shopier_url(body, actual_id)
        except RuntimeError as exc:
            print(f"[{brand}] mevcut {key} {product_id} güncellenemedi: {exc}")
    return None


def _create(brand: str, key: str) -> tuple[str, str]:
    body = _request(brand, "POST", API, _payload(key, brand))
    product_id = str(body.get("id") or "").strip()
    if not product_id:
        raise RuntimeError(f"[{brand}] {key} oluşturuldu ancak Shopier ID dönmedi")
    return product_id, _shopier_url(body, product_id)


def _entry(brand: str, key: str, product_id: str, url: str) -> dict:
    campaign = CAMPAIGNS[key]
    value = float(campaign["prices"][brand])
    category_label = {
        "ai": "YAPAY ZEKA & AI",
        "design": "TASARIM & KREATİF",
        "coupons": "KUPON & İNDİRİM",
    }.get(campaign.get("category"), "DİJİTAL LİSANS")
    if brand == "keyvadi":
        return {
            "id": product_id,
            "title": campaign["title"],
            "price": price_text(value, comma=True),
            "price_num": value,
            "category": campaign["category"],
            "image": "assets/" + campaign["image"],
            "badge": campaign.get("badge", "⚡ Kampanya Kodu"),
            "url": url,
            "description": campaign["description"],
            "showcase": True,
            "is_vitrin": True,
            "category_label": category_label,
            "delivery_type": "instant",
            "delivery_label": "⚡ Anında Kod Teslimi",
            "max_qty": 1,
        }
    return {
        "id": "la_" + key,
        "title": campaign["title"],
        "price": price_text(value),
        "category": campaign["category"],
        "is_vitrin": True,
        "showcase": True,
        "badge": campaign.get("badge", "⚡ Kampanya Kodu"),
        "image": "assets/" + campaign["image"],
        "rating": 4.9,
        "sales_count": 0,
        "delivery": "⚡ Anında Kod Teslimi",
        "warranty": "🛡️ %100 Çalışma Garantili",
        "desc": campaign["description"],
        "shopier_url": url,
        "shopier_product_id": product_id,
        "shopier_owner": "lisansarena",
    }


def _replace_campaign(items: list[dict], brand: str, key: str, entry: dict) -> list[dict]:
    campaign = CAMPAIGNS[key]
    titles = {campaign["title"].casefold()}
    if key == "yemeksepeti_450":
        titles.update({
            "yemeksepeti 450₺'ye 350₺ indirim kodu",
            "yemeksepeti ilk sipariş 450₺'ye 350₺ indirim kodu",
        })
    if key == "trendyol_market_800":
        titles.add("trendyol market kuponu (800₺/300₺ indirim)")
    result = []
    replaced = False
    for item in items:
        title = str(item.get("title") or "").casefold()
        item_id = str(item.get("id") or "")
        is_match = item_id in KNOWN_IDS.get((brand, key), []) or title in titles
        # Do not let the old 700/250 listing be swallowed by the new 750/250 one.
        if key == "trendyol_yemek_750" and "700" in title:
            is_match = False
        if is_match:
            if not replaced:
                result.append(entry)
                replaced = True
            continue
        result.append(item)
    if not replaced:
        result.insert(0, entry)
    return result


def _write_catalogs(results: dict[tuple[str, str], tuple[str, str]]) -> None:
    for brand in ("keyvadi", "lisansarena"):
        catalog_path = CATALOGS[brand]
        miniapp_path = MINIAPPS[brand]
        links = json.loads(catalog_path.read_text(encoding="utf-8"))
        products = json.loads(miniapp_path.read_text(encoding="utf-8"))
        for key, campaign in CAMPAIGNS.items():
            result = results.get((brand, key))
            if not result:
                continue
            product_id, url = result
            entry = _entry(brand, key, product_id, url)
            links = _replace_campaign(links, brand, key, {
                "id": product_id,
                "title": campaign["title"],
                "price": price_text(campaign["prices"][brand], comma=(brand == "keyvadi")),
                "price_num": float(campaign["prices"][brand]),
                "url": url,
            })
            products = _replace_campaign(products, brand, key, entry)
        # Explicitly remove the known foreign LA duplicate for 450/350.
        if brand == "lisansarena":
            links = [item for item in links if str(item.get("id")) != "50576030"]
        catalog_path.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        miniapp_path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="API çağrısı yapmadan payload özetini göster")
    args = parser.parse_args()
    if args.dry_run:
        for brand in ("keyvadi", "lisansarena"):
            for key, campaign in CAMPAIGNS.items():
                print(f"[{brand}] {campaign['title']} -> {campaign['prices'][brand]:.2f} TL")
        return 0

    results: dict[tuple[str, str], tuple[str, str]] = {}
    for brand in ("keyvadi", "lisansarena"):
        for key in CAMPAIGNS:
            if (brand, key) in KNOWN_IDS:
                result = _update_existing(brand, key)
                if result:
                    print(f"[{brand}] güncellendi: {key} -> {result[0]}")
                    results[(brand, key)] = result
                    continue
            try:
                result = _create(brand, key)
                print(f"[{brand}] oluşturuldu: {key} -> {result[0]}")
                results[(brand, key)] = result
            except RuntimeError as exc:
                print(f"[{brand}] HATA: {key}: {exc}")
                return 1
    _write_catalogs(results)
    Path(ROOT / "campaign_shopier_results.json").write_text(
        json.dumps(
            [
                {"brand": brand, "campaign": key, "id": product_id, "url": url}
                for (brand, key), (product_id, url) in sorted(results.items())
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Shopier senkronizasyonu tamamlandı: {len(results)} ürün")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
