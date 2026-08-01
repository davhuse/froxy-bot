import html
import http.cookiejar
import json
import os
import re
import ssl
import sys
import tempfile
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_SHOP_SLUG = "keyvadi"
CATALOG_FILE = "keyvadi_shopier_links.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/138.0.0.0 Safari/537.36"
)


def _request(opener, url, *, data=None, headers=None):
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    )
    with opener.open(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _initial_products(source, shop_slug):
    products = []
    cards = source.split(
        '<div class="product-card shopier--product-card product-card-store">'
    )
    for card in cards[1:]:
        id_match = re.search(r'data-back-id="(\d+)"', card)
        link_match = re.search(
            rf'href="(https://www\.shopier\.com/{re.escape(shop_slug)}/\d+)"', card
        )
        title_match = re.search(
            r'class="shopier-store--store-product-card-title">([^<]+)</h3>', card
        )
        price_match = re.search(r'data-price="([^"]+)"', card)
        if not (id_match and link_match and title_match and price_match):
            continue
        products.append(
            {
                "id": id_match.group(1),
                "title": html.unescape(title_match.group(1).strip()),
                "price": html.unescape(price_match.group(1).strip()),
                "url": link_match.group(1),
            }
        )
    return products


def _normalize_api_product(product, shop_url):
    product_id = str(product.get("id") or "").strip()
    title = html.unescape(str(product.get("name") or "").strip())
    link = str(product.get("link") or "").strip()
    raw_price = product.get("price") or ""
    if isinstance(raw_price, dict):
        raw_price = (
            raw_price.get("price_legacy_formatted")
            or raw_price.get("price_code_formatted")
            or raw_price.get("price_symbol_formatted")
            or raw_price.get("price_formatted")
            or ""
        )
    price = html.unescape(str(raw_price).strip())
    if not (product_id and title and link and price):
        return None
    return {
        "id": product_id,
        "title": title,
        "price": price,
        "url": urllib.parse.urljoin(shop_url, link),
    }


def fetch_live_catalog(shop_slug=DEFAULT_SHOP_SLUG):
    """Shopier vitrininin ilk sayfasını ve tüm sonsuz-kaydırma sayfalarını getir."""
    shop_slug = shop_slug.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", shop_slug):
        raise ValueError("Geçersiz Shopier mağaza adı.")
    shop_url = f"https://www.shopier.com/{shop_slug}"
    load_more_url = f"https://www.shopier.com/s/api/v1/search_product/{shop_slug}"

    cookie_jar = http.cookiejar.CookieJar()
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler(context=context),
    )
    source = _request(opener, shop_url)

    count_match = re.search(r"const\s+\$product_count\s*=\s*(\d+)", source)
    csrf_match = re.search(
        r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)',
        source,
        flags=re.I,
    )
    page_size_match = re.search(r'"default_product_count"\s*:\s*(\d+)', source)
    if not (count_match and csrf_match):
        raise RuntimeError("Shopier ürün sayısı veya CSRF anahtarı bulunamadı.")

    expected_count = int(count_match.group(1))
    page_size = int(page_size_match.group(1)) if page_size_match else 24
    products = _initial_products(source, shop_slug)
    seen_ids = {product["id"] for product in products}
    show_more = len(products) < expected_count

    while show_more and len(products) < expected_count:
        form = urllib.parse.urlencode(
            {
                "start": page_size,
                # Shopier son görünür kartı bir sonraki yanıtta tekrar döndürüyor.
                "offset": max(0, len(products) - 1),
                "filter": 0,
                "sort": 0,
                "filterMaxPrice": "",
                "filterMinPrice": "",
                "datesort": -1,
                "pricesort": -1,
                "value": "",
            }
        ).encode("utf-8")
        payload = json.loads(
            _request(
                opener,
                load_more_url,
                data=form,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://www.shopier.com",
                    "Referer": shop_url,
                    "X-CSRF-TOKEN": csrf_match.group(1),
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
        )
        before = len(products)
        for raw_product in payload.get("products", []):
            product = _normalize_api_product(raw_product, shop_url)
            if not product or product["id"] in seen_ids:
                continue
            seen_ids.add(product["id"])
            products.append(product)
        show_more = bool(payload.get("show_more"))
        if len(products) == before:
            raise RuntimeError("Shopier sayfalaması ilerlemedi; mevcut katalog korunuyor.")

    if len(products) != expected_count:
        raise RuntimeError(
            f"Shopier {expected_count} ürün bildirdi fakat {len(products)} ürün alındı; "
            "mevcut katalog korunuyor."
        )
    return products


def write_catalog_atomic(products, destination=CATALOG_FILE):
    target = os.path.abspath(destination)
    directory = os.path.dirname(target) or os.getcwd()
    existing_by_id = {}
    try:
        with open(target, "r", encoding="utf-8") as existing_file:
            existing = json.load(existing_file)
        existing_by_id = {
            str(item.get("id")): item for item in existing if isinstance(item, dict)
        }
    except (OSError, ValueError, TypeError):
        pass

    # The storefront listing endpoint omits long descriptions and legacy media
    # metadata. Preserve those fields for products that are still live, while
    # still removing every product ID absent from the current storefront.
    for product in products:
        previous = existing_by_id.get(str(product.get("id")), {})
        for key in ("description", "desc", "type", "primary_image"):
            if previous.get(key) and not product.get(key):
                product[key] = previous[key]

    fd, temp_path = tempfile.mkstemp(prefix="shopier_catalog_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as catalog_file:
            json.dump(products, catalog_file, ensure_ascii=False, indent=2)
            catalog_file.write("\n")
        os.replace(temp_path, target)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def main():
    shop_slug = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHOP_SLUG
    destination = sys.argv[2] if len(sys.argv) > 2 else CATALOG_FILE
    products = fetch_live_catalog(shop_slug)
    write_catalog_atomic(products, destination)
    print(f"SUCCESS: Shopier vitrininin {len(products)} ürününün tamamı yazıldı.")


if __name__ == "__main__":
    main()
