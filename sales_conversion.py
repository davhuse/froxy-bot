"""Shared sales catalog, matching, purchase-link, and CTA experiment helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parent
CATALOG_FILES = {
    "keyvadi": ROOT / "keyvadi_shopier_links.json",
    "froxy": ROOT / "froxy_shopier_links.json",
    "lisansarena": ROOT / "miniapp_lisansarena" / "products_db.json",
    "jarvis": ROOT / "jarvis_shopier_products.json",
}
AUXILIARY_CATALOG_FILES = {}
SHOPIER_HOSTS = {"shopier.com", "www.shopier.com"}
PUBLIC_BASE_URL = (
    os.environ.get("PUBLIC_BASE_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or "https://froxy-bot-live.onrender.com"
).rstrip("/")
CATALOG_REFRESH_STATUS: dict[str, dict] = {}

TEXT_ALIASES = {
    "alt limitsiz": "alt limitsiz",
    "alt limitsiz yemek": "trendyol yemek alt limitsiz",
    "550 200": "yemeksepeti 550",
    "500 250": "yemeksepeti 500",
    "taraftar paketi": "tod",
    "tod tv": "tod",
    "tod": "tod",
    "uber indirim": "uber",
    "uber kupon": "uber",
    "uber": "uber",
    "tiklagelsin": "tıkla gelsin",
    "tıklagelsin": "tıkla gelsin",
    "tikla gelsin": "tıkla gelsin",
    "tıkla gelsin": "tıkla gelsin",
    "gptgo": "gpt go",
    "gpt go": "gpt go",
    "mc": "minecraft",
    "minecraft": "minecraft",
    "mine craft": "minecraft",
    "mc pre": "minecraft",
    "mc premium": "minecraft",
    "minecraft pre": "minecraft",
    "gamepass": "xbox",
    "game pass": "xbox",
    "x box": "xbox",
    "fifa": "fc 26",
    "fifa26": "fc 26",
    "fc26": "fc 26",
    "fc 26": "fc 26",
    "dc": "discord",
    "nitro": "discord",
    "discord nitro": "discord",
    "yt": "youtube",
    "yt premium": "youtube",
    "you tube": "youtube",
    "netfilix": "netflix",
    "netfli": "netflix",
    "chat gpt": "chatgpt",
    "chatgbt": "chatgpt",
    "chat gbt": "chatgpt",
    "plas": "plus",
    "pluss": "plus",
    "gpt": "chatgpt",
    "personal": "kisisel",
    "personel": "kisisel",
    "30 gunluk": "30 gun",
    "1 aylik": "1 ay",
    "3 aylik": "3 ay",
    "blu tv": "blutv",
    "blue tv": "blutv",
    "win10": "windows 10",
    "win11": "windows 11",
    "office365": "office 365",
    "ofis": "office",
    "win key": "windows key",
    "adobe cc": "adobe creative cloud",
    "creative cloud": "adobe creative cloud",
    "marketu": "trendyol market",
    "market": "trendyol market",
    "yemek kuponu": "trendyol yemek",
    "yemek": "trendyol yemek",
    "tg hesap": "telegram hesap",
    "telegram account": "telegram hesap",
    "random key": "steam random key",
    "vip key": "steam random key",
    "steam key": "steam random key",
    "steam oyun": "steam oyun",
    "cap cut": "capcut",
    "capcut pro": "capcut",
    "ssport": "s sport",
    "s sport plus": "s sport",
    "ssport plus": "s sport",
    "yemek sepeti": "yemeksepeti",
    "yemeksepeti kupon": "yemeksepeti",
    "yemeksepeti 200": "yemeksepeti 200",
    "360 270": "yemeksepeti 360",
    "yemeksepeti 360": "yemeksepeti 360",
    "yemeksepeti 450": "yemeksepeti 450",
    "200 200": "yemeksepeti 200",
    "450 350": "yemeksepeti 450",
    "positive puan": "positive",
    "positive": "positive",
    "gastro club": "gastroclub",
    "gastroclub": "gastroclub",
    "enterprise": "enterprise",
    "garenta": "garenta",
    "enuygun 10": "enuygun plus",
    "enuygun plus": "enuygun plus",
    "trendyol go": "trendyol market",
    "800 300": "trendyol market 800",
    "750 250": "trendyol yemek 750",
    "market 800": "trendyol market 800",
    "yemek 750": "trendyol yemek 750",
    "turna": "turna",
    "turna.com": "turna",
    "ucak bileti": "turna",
    "bilet kuponu": "turna",
    "coffy": "coffy",
    "cofy": "coffy",
    "cofi": "coffy",
    "kahve kuponu": "coffy",
    "migros": "migros",
    "migros bakiye": "migros",
    "migros kupon": "migros",
}

BRAND_PHRASES = (
    "chatgpt", "netflix", "youtube", "adobe", "canva", "windows", "office",
    "gemini", "grok", "xbox", "spotify", "exxen", "trendyol", "trendyol yemek",
    "trendyol market", "alt limitsiz", "duolingo", "semrush", "capcut", "scribd", "gamma",
    "kiro", "steam", "shell", "whatsapp", "apple", "crunchyroll", "telegram", "blutv",
    "midjourney", "tradingview", "nordvpn", "vpn", "kaspersky", "envato",
    "freepik", "autocad", "figma", "elementor", "grammarly", "deepl",
    "ideogram", "quillbot", "discord", "hbo", "prime video", "prime", "amazon", "perplexity",
    "magnific", "zula", "fc 26", "fc26", "codex", "antigravity", "disney", "minecraft",
    "cape", "pelerin", "roblox", "instagram", "takipci", "gmail", "claude",
    "s sport", "yemeksepeti", "turna", "coffy", "cofy", "migros",
    "tiktak", "flo", "lumberjack", "in street", "enuygun", "garenta", "enterprise",
    "positive", "gastroclub", "tıkla gelsin", "tikla gelsin",
    "uber", "tod", "gpt go",
    "yemeksepeti 200", "yemeksepeti 360", "yemeksepeti 450", "positive", "gastroclub",
    "garenta", "enterprise", "enuygun plus", "trendyol market 800", "trendyol yemek 750",
    "baslangic", "populer", "profesyonel", "gelistirici", "isletme", "kurumsal"
)

VARIANT_TERMS = {
    "kisisel", "ortak", "ozel", "profil", "davet", "ultra", "pro", "plus",
    "ay", "aylik", "yil", "yillik", "hafta", "haftalik", "kredili", "kredisiz",
    "1", "2", "3", "4", "6", "12", "18", "30", "2500", "5k", "15k", "50k",
    "gun", "gunluk",
}

# Froxy's approved customer-facing prices. The public showroom can lag behind
# the configured campaign/catalog price, so these IDs must not be overwritten
# by a stale showroom value during a bot restart.
FROXY_PRICE_OVERRIDES = {
    "49489691": "499,90 TL",  # ChatGPT Plus 30 Gün - Kişisel
    "49489721": "599,90 TL",  # ChatGPT Plus + Codex (1 Aylık)
}

# Customer-facing campaign prices must not drift when a stale Shopier cache is
# refreshed.  The live listing is still the checkout source; these overrides
# keep bots, automatic replies and Mini App deep-link cards consistent.
BRAND_PRICE_OVERRIDES = {
    ("keyvadi", "50576030"): "50,00 TL",
    ("keyvadi", "47669486"): "50,00 TL",
    ("keyvadi", "51024906"): "45,00 TL",
    ("keyvadi", "51024908"): "50,00 TL",
    ("keyvadi", "51024903"): "30,00 TL",
    ("keyvadi", "51024902"): "20,00 TL",
    ("keyvadi", "51024899"): "30,00 TL",
    ("keyvadi", "51024901"): "20,00 TL",
    ("keyvadi", "51024900"): "20,00 TL",
    ("keyvadi", "51024904"): "50,00 TL",
    ("keyvadi", "51024905"): "50,00 TL",
    ("keyvadi", "51025109"): "149,90 TL",
    ("keyvadi", "51051020"): "199,90 TL",
    ("keyvadi", "51051022"): "499,90 TL",
    ("keyvadi", "50858094"): "80,00 TL",
    ("keyvadi", "50857983"): "150,00 TL",
    ("keyvadi", "50857984"): "100,00 TL",
    ("keyvadi", "50857985"): "75,00 TL",
    ("keyvadi", "50857986"): "60,00 TL",
    ("keyvadi", "50857987"): "125,00 TL",
    ("keyvadi", "50857988"): "100,00 TL",
    ("keyvadi", "50857990"): "85,00 TL",
    ("keyvadi", "47669117"): "79,90 TL",
    ("froxy", "49489691"): "499,90 TL",
    ("froxy", "49489721"): "599,90 TL",
    ("lisansarena", "la_netflix_ozel"): "84,90 TL",
    ("lisansarena", "49002144"): "84,90 TL",
    ("lisansarena", "la_tiklagelsin_400"): "95,00 TL",
    ("lisansarena", "la_yemeksepeti_500"): "120,00 TL",
    ("lisansarena", "la_yemeksepeti_550"): "90,00 TL",
    ("lisansarena", "la_yemeksepeti_360"): "55,00 TL",
    ("lisansarena", "la_yemeksepeti_450"): "60,00 TL",
    ("lisansarena", "la_positive_110"): "35,00 TL",
    ("lisansarena", "la_gastroclub_200"): "25,00 TL",
    ("lisansarena", "la_enterprise_40"): "35,00 TL",
    ("lisansarena", "la_garenta_40"): "30,00 TL",
    ("lisansarena", "la_enuygun_plus_10"): "30,00 TL",
    ("lisansarena", "la_trendyol_market_800"): "60,00 TL",
    ("lisansarena", "la_trendyol_yemek_750"): "60,00 TL",
    ("lisansarena", "la_duolingo_super_12_personal"): "249,90 TL",
    ("lisansarena", "la_adobe_express_12_personal"): "599,90 TL",
    ("lisansarena", "la_trendyol_yemek_200"): "75,00 TL",
    ("lisansarena", "la_uber_70"): "150,00 TL",
    ("lisansarena", "la_uber_1000"): "100,00 TL",
    ("lisansarena", "la_tod_taraftar"): "120,00 TL",
    ("lisansarena", "la_gpt_go"): "180,00 TL",
    ("lisansarena", "la_tiktak_1000"): "40,00 TL",
    ("lisansarena", "la_flo_800"): "30,00 TL",
    ("lisansarena", "50821443"): "95,00 TL",
    ("lisansarena", "50821444"): "120,00 TL",
    ("lisansarena", "50821445"): "90,00 TL",
    ("lisansarena", "50821446"): "75,00 TL",
    ("lisansarena", "50821447"): "150,00 TL",
    ("lisansarena", "50821448"): "100,00 TL",
    ("lisansarena", "50821449"): "120,00 TL",
    ("lisansarena", "50821450"): "180,00 TL",
    ("lisansarena", "50821451"): "40,00 TL",
    ("lisansarena", "50821452"): "30,00 TL",
}

STOP_WORDS = {
    "var", "mi", "mu", "ve", "de", "da", "icin", "misiniz", "olur", "yok",
    "acaba", "urun", "hesap", "kodu", "kupon", "hocam", "kanka", "bir",
    "istiyorum", "lazim", "kac", "fiyat", "ne", "tl", "lira", "nasil", "nedir",
    "site", "link", "al", "almak", "satin", "bilgi", "hakkinda",
}


def normalize_sales_text(value: str) -> str:
    text = str(value or "").casefold().replace("ı", "i")
    text = text.replace("�", "")
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    for source, target in sorted(TEXT_ALIASES.items(), key=lambda item: -len(item[0])):
        source_norm = re.sub(r"[^a-z0-9]+", " ", normalize_alias_literal(source)).strip()
        text = re.sub(rf"(?<!\w){re.escape(source_norm)}(?!\w)", target, text)
    # The generic ``gpt`` alias is useful for queries such as "gpt kişisel",
    # but it must never rewrite the distinct GPT GO product into ChatGPT GO.
    # Keep that product name isolated so a ChatGPT query cannot fall through
    # to the GPT GO listing when the requested product is absent.
    text = re.sub(r"\bchatgpt\s+go\b", "gpt go", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_alias_literal(value: str) -> str:
    text = str(value or "").casefold().replace("ı", "i").replace("�", "")
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def apply_froxy_price_overrides(product: dict) -> dict:
    """Apply approved Froxy prices to showroom/API product records."""
    result = dict(product or {})
    override = FROXY_PRICE_OVERRIDES.get(str(result.get("id") or ""))
    if override:
        result["price"] = override
    return result


def _normalize_product(item: dict, brand: str = "") -> dict | None:
    product_id = str(item.get("id") or "").strip()
    title = str(item.get("title") or "").strip()
    url = str(item.get("shopier_url") or item.get("url") or item.get("link") or "").strip()
    if not url and str(brand).lower() == "lisansarena" and product_id:
        url = f"{PUBLIC_BASE_URL}/la/app?product={quote(product_id, safe='')}"
    if not product_id or not title or not (is_allowed_shopier_url(url) or is_allowed_internal_purchase_url(url)):
        return None
    lower_title = title.lower()
    if (
        "keyvadi cüzdan" in lower_title
        or "keyvadi cuzdan" in lower_title
        or "bakiye yükleme" in lower_title
        or "bakiye yukleme" in lower_title
        or "cüzdan bakiye" in lower_title
        or "cuzdan bakiye" in lower_title
    ):
        return None
    price = BRAND_PRICE_OVERRIDES.get((str(brand).lower(), product_id), item.get("price"))
    if not price and isinstance(item.get("priceData"), dict):
        price = item["priceData"].get("price")
    normalized = dict(item)
    normalized.update({"id": product_id, "title": title, "price": str(price or ""), "url": url})
    return normalized


def load_sales_catalog(brand: str) -> list[dict]:
    path = CATALOG_FILES.get(str(brand).lower())
    if not path:
        return []
    data_sets = []
    try:
        data_sets.append(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        data_sets.append([])
    auxiliary = AUXILIARY_CATALOG_FILES.get(str(brand).lower())
    if auxiliary and auxiliary.exists():
        try:
            data_sets.append(json.loads(auxiliary.read_text(encoding="utf-8")))
        except Exception:
            pass
    products = []
    seen = set()
    for data in data_sets:
        for item in data if isinstance(data, list) else []:
            product = _normalize_product(item, brand) if isinstance(item, dict) else None
            if product and product["id"] not in seen:
                seen.add(product["id"])
                products.append(product)
    # Dynamic campaigns never rewrite the source catalog.  When explicitly
    # enabled, overlay the active price in bot/Mini App cards so the CTA and
    # the one-off Shopier listing show the same amount.
    if os.environ.get("SHOPIER_DYNAMIC_SALE_LISTINGS_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }:
        try:
            from shopier_campaigns import apply_dynamic_campaign_prices

            products = apply_dynamic_campaign_prices(brand, products)
        except Exception:
            # A campaign state outage must not make the catalog unavailable.
            pass
    return products


def _fetch_shopier_products(token: str) -> list[dict]:
    """Read every Shopier product using the documented 50-item page limit."""
    products = []
    seen_ids = set()
    for page in range(1, 101):
        request = urllib.request.Request(
            f"https://api.shopier.com/v1/products?limit=50&page={page}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload if isinstance(payload, list) else (
            payload.get("data") or payload.get("products") or []
        )
        if not isinstance(rows, list):
            raise RuntimeError("Shopier API returned an invalid products payload")
        for row in rows:
            if not isinstance(row, dict):
                continue
            product_id = str(row.get("id") or "").strip()
            dedupe_key = product_id or json.dumps(row, ensure_ascii=False, sort_keys=True)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            products.append(row)
        if len(rows) < 50:
            break
    return products


def refresh_catalog_from_shopier_api(brand: str) -> int:
    """Refresh one catalog when a Shopier personal access token is configured."""
    brand = str(brand).lower()
    token_key = {
        "keyvadi": "SHOPIER_KEYVADI_ACCESS_TOKEN",
        "froxy": "SHOPIER_FROXY_ACCESS_TOKEN",
        "lisansarena": "SHOPIER_LISANSARENA_ACCESS_TOKEN",
    }.get(brand, "")
    token = os.environ.get(token_key, "").strip()
    path = CATALOG_FILES.get(brand)
    if not path:
        return 0
    if not token:
        CATALOG_REFRESH_STATUS[brand] = {
            "state": "not_configured",
            "catalog_source": "local_cache",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return 0
    raw_products = _fetch_shopier_products(token)
    current = {item["id"]: item for item in load_sales_catalog(brand)}
    try:
        from announcement_delivery import record_stock_changes

        stock_result = record_stock_changes(brand, raw_products)
        if stock_result.get("queued"):
            print(f"[Catalog] Stock transitions queued for {brand}: {stock_result}")
    except Exception as exc:
        # Stock announcements must never make a valid catalog refresh fail.
        print(f"[Catalog] Stock transition tracking skipped for {brand}: {type(exc).__name__}")
    refreshed = []
    for raw in raw_products:
        if (
            not isinstance(raw, dict)
            or raw.get("active") is False
            or raw.get("stockStatus") == "outOfStock"
        ):
            continue
        product_id = str(raw.get("id") or "").strip()
        old = current.get(product_id, {})
        price_data = raw.get("priceData") if isinstance(raw.get("priceData"), dict) else {}
        price = raw.get("price") or price_data.get("discountedPrice") or price_data.get("price") or old.get("price")
        if isinstance(price, dict):
            price = price.get("price_legacy_formatted") or price.get("price_code_formatted")
        item = _normalize_product({
            **old,
            "id": product_id,
            "title": raw.get("name") or raw.get("title") or old.get("title"),
            "price": price,
            "url": raw.get("link") or raw.get("url") or old.get("url"),
            "description": raw.get("description") or old.get("description", ""),
            "image_url": (
                raw.get("image_url")
                or raw.get("image")
                or raw.get("cover_url")
                or old.get("image_url")
                or old.get("image")
                or old.get("cover_url")
                or ""
            ),
            "stockStatus": raw.get("stockStatus") or old.get("stockStatus", ""),
            "stockQuantity": raw.get("stockQuantity", old.get("stockQuantity")),
        }, brand)
        if item:
            refreshed.append(item)
    if not refreshed:
        raise RuntimeError(f"Shopier API returned no usable {brand} products")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    # New product announcements are queued only for IDs that were not already
    # present in the last valid catalog.  The queue itself is idempotent, so a
    # repeated Shopier refresh cannot notify the same product twice.
    try:
        from announcement_delivery import enqueue_new_product

        for product in refreshed:
            if product.get("id") not in current:
                enqueue_new_product(brand, product)
    except Exception:
        # Catalog refresh must remain available when announcement storage is
        # temporarily unavailable.
        pass
    CATALOG_REFRESH_STATUS[brand] = {
        "state": "fresh",
        "catalog_source": "shopier_api",
        "product_count": len(refreshed),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return len(refreshed)


def refresh_configured_catalogs() -> dict[str, int]:
    result = {}
    for brand in CATALOG_FILES:
        try:
            result[brand] = refresh_catalog_from_shopier_api(brand)
        except Exception as exc:
            result[brand] = 0
            CATALOG_REFRESH_STATUS[brand] = {
                "state": "refresh_failed",
                "catalog_source": "local_cache",
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "code", None),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    return result


def catalog_refresh_status() -> dict[str, dict]:
    """Return non-secret freshness metadata for the health dashboard."""
    result = {}
    for brand, path in CATALOG_FILES.items():
        status = dict(CATALOG_REFRESH_STATUS.get(brand) or {})
        status.setdefault(
            "state",
            "not_checked" if os.environ.get({
                "keyvadi": "SHOPIER_KEYVADI_ACCESS_TOKEN",
                "froxy": "SHOPIER_FROXY_ACCESS_TOKEN",
                "lisansarena": "SHOPIER_LISANSARENA_ACCESS_TOKEN",
            }[brand], "").strip() else "not_configured",
        )
        status.setdefault("catalog_source", "local_cache")
        status["cached_product_count"] = len(load_sales_catalog(brand))
        try:
            status["cache_updated_at"] = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat()
        except OSError:
            status["cache_updated_at"] = None
        result[brand] = status
    return result


def is_allowed_shopier_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url))
        return parsed.scheme == "https" and (parsed.hostname or "").lower() in SHOPIER_HOSTS
    except Exception:
        return False


def is_allowed_internal_purchase_url(url: str) -> bool:
    """Allow only this deployment's Mini App as a temporary LA fallback."""
    try:
        parsed = urlparse(str(url))
        base_host = (urlparse(PUBLIC_BASE_URL).hostname or "").lower()
        return (
            parsed.scheme == "https"
            and (parsed.hostname or "").lower() == base_host
            and parsed.path == "/la/app"
        )
    except Exception:
        return False


def is_lisansarena_shopier_url(url: str) -> bool:
    """Accept only listings owned by the LisansArena Shopier storefront.

    Legacy catalog rows used bare Shopier product URLs.  Those IDs are not
    enough to prove seller ownership and can point at KeyVadi or another
    account, so LisansArena falls back to its own Mini App until a canonical
    ``/lisansarena/<id>`` listing is present.
    """
    try:
        parsed = urlparse(str(url))
        path = (parsed.path or "").rstrip("/").lower()
        return (
            parsed.scheme == "https"
            and (parsed.hostname or "").lower() in SHOPIER_HOSTS
            and path.startswith("/lisansarena/")
            and path.rsplit("/", 1)[-1].isdigit()
        )
    except Exception:
        return False


def purchase_target_url(brand: str, product: dict) -> str:
    """Return the product-specific Shopier or Mini App purchase target."""
    target = str(product.get("shopier_url") or product.get("url") or "")
    if str(brand).lower() == "lisansarena" and any(
        marker in target.casefold() for marker in ("/keyvadi/", "/froxyai/")
    ):
        pid = product.get("id", "")
        return f"https://t.me/LisansArenaBot/app?startapp=p_{pid}" if pid else "https://t.me/LisansArenaBot/app"
    if target and (is_allowed_shopier_url(target) or is_allowed_internal_purchase_url(target)):
        return target
    if str(brand).lower() == "lisansarena":
        pid = product.get("id", "")
        return f"https://t.me/LisansArenaBot/app?startapp=p_{pid}" if pid else "https://t.me/LisansArenaBot/app"
    return target


def _brand_phrases_in(text: str) -> list[str]:
    return [phrase for phrase in BRAND_PHRASES if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text)]


def has_sales_query(message: str) -> bool:
    query = normalize_sales_text(message)
    return bool(_brand_phrases_in(query) or set(query.split()) & {"fiyat", "urun", "satin", "link"})


def match_sales_products(message: str, products: list[dict], limit: int = 3) -> list[dict]:
    """Return one specific match or at most three variants for a query."""
    query = normalize_sales_text(message)
    if not query:
        return []
    query_tokens = set(query.split())
    useful_query = query_tokens - STOP_WORDS
    brands = _brand_phrases_in(query)
    if not brands:
        return []
    variant_tokens = query_tokens & VARIANT_TERMS
    scored = []
    
    for product in products:
        title = normalize_sales_text(product.get("title", ""))
        title_tokens = set(title.split())
        matching_brands = [brand for brand in brands if brand in title] if brands else []
        overlap = useful_query & title_tokens
        
        # Candidate qualification: matches a brand OR has at least 1 significant title token
        if brands and not matching_brands:
            continue
        elif not brands and not overlap:
            continue
            
        score = 100 * len(matching_brands) + 20 * len(overlap)
        if title and title in query:
            score += 150
        for token in variant_tokens:
            score += 40 if token in title_tokens else -25
        if "yemek" in query_tokens and "yemek" not in title_tokens:
            score -= 100
        if "market" in query_tokens and "market" not in title_tokens:
            score -= 100
        if "kisisel" in query_tokens and "ortak" in title_tokens:
            score -= 120
        if "kisisel" in query_tokens and "kisisel" in title_tokens:
            score += 140
        if "ortak" in query_tokens and "kisisel" in title_tokens:
            score -= 120
        if "ortak" in query_tokens and "ortak" in title_tokens:
            score += 140
        if "1 ay" in query or "1 aylik" in query:
            if "1 ay" in title or "1 aylik" in title:
                score += 80
            elif "3 ay" in title or "12 ay" in title:
                score -= 60
        if "3 ay" in query or "3 aylik" in query:
            if "3 ay" in title or "3 aylik" in title:
                score += 80
            elif "1 ay" in title or "12 ay" in title:
                score -= 60
        if "minecraft" in query_tokens and "minecraft" in title_tokens:
            score += 150
        if "steam" in query_tokens and "steam" in title_tokens:
            score += 120
        if "capcut" in query_tokens and "capcut" in title_tokens:
            score += 120
        if "codex" in query_tokens and "chatgpt" in query_tokens:
            if "codex" in title_tokens and "chatgpt" in title_tokens:
                score += 180
            elif "sms" in title_tokens:
                score -= 160
        if "gemini" in query_tokens or "gemini" in brands:
            if any(term in query for term in ["18", "18 ay", "18 aylik", "promosyon", "link", "baglanti"]):
                if "18" in title_tokens or "18 ay" in title:
                    score += 160
            elif "18" in title_tokens or "18 ay" in title:
                score += 50
            if "promosyon" in query_tokens and ("promosyon" in title_tokens or "indirim" in title_tokens):
                score += 120
            if product.get("is_vitrin") or product.get("showcase"):
                score += 40
        scored.append((score, product))
        
    scored.sort(key=lambda pair: (-pair[0], _price_number(pair[1].get("price")), pair[1]["title"]))
    if not scored:
        return []

    MULTI_VARIANT_BRANDS = {
        "netflix", "minecraft", "yemeksepeti", "canva", "gemini", "duolingo"
    }

    is_multi_variant_brand = any(b in MULTI_VARIANT_BRANDS for b in brands)
    is_ultra_specific = len(variant_tokens) >= 3 or (
        ("kisisel" in query_tokens or "ortak" in query_tokens)
        and any(d in query for d in ["1 ay", "1 aylik", "3 ay", "3 aylik", "30 gun"])
        and "plus" in query_tokens
    )

    if not is_ultra_specific and is_multi_variant_brand:
        primary = scored[0][1]
        results = [primary]
        seen_titles = {primary["title"]}
        for _score, product in scored[1:]:
            if product["title"] not in seen_titles:
                results.append(product)
                seen_titles.add(product["title"])
            if len(results) >= max(1, limit):
                break
        return results

    if is_ultra_specific and scored:
        return [scored[0][1]]
    if "chatgpt" in query_tokens and "codex" in query_tokens and scored:
        return [scored[0][1]]
    if ("kisisel" in query_tokens or "ortak" in query_tokens) and scored:
        return [scored[0][1]]
    if variant_tokens and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 25):
        return [scored[0][1]]
    return [product for _score, product in scored[: max(1, limit)]]


def _price_number(value: str) -> float:
    cleaned = re.sub(r"[^0-9,.]", "", str(value or "")).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 999999.0


SPECIFIC_BRANDS_FOR_ROADMAP = {
    "netflix", "minecraft", "chatgpt", "canva", "adobe", "windows", "office",
    "spotify", "s sport", "turna", "duolingo", "capcut",
    "kaspersky", "exxen", "prime", "amazon", "hbo", "disney", "roblox", "steam",
    "fc 26", "fc26", "fifa", "zula", "gemini", "grok", "claude", "perplexity",
    "crunchyroll", "deepl", "grammarly", "nordvpn", "vpn", "envato", "freepik",
    "coffy", "cofy", "migros", "yemeksepeti"
}


def resolve_smart_roadmap_reply(message: str, brand: str = "keyvadi") -> str | None:
    """Return a roadmap/flowchart reply when the user asks categorical, duration, or plan questions."""
    norm = normalize_sales_text(message)
    if not norm:
        return None

    # If the user explicitly asked for a specific product/brand, let product matching handle it
    if any(re.search(rf"(?<!\w){re.escape(b)}(?!\w)", norm) for b in SPECIFIC_BRANDS_FOR_ROADMAP):
        return None

    # Marka bazlı kişisel yıllık ürün bağlantıları; genel akışta yanlış mağaza
    # fiyatı gösterilmemesi için aynı ürünün iki mağaza kaydını ayrı tut.
    is_lisansarena = str(brand or "").lower().startswith("lisans")
    personal_duolingo_price = "249,90" if is_lisansarena else "199,90"
    personal_duolingo_url = "https://www.shopier.com/51051023" if is_lisansarena else "https://www.shopier.com/51051020"
    personal_adobe_price = "599,90" if is_lisansarena else "499,90"
    personal_adobe_url = "https://www.shopier.com/51051024" if is_lisansarena else "https://www.shopier.com/51051022"

    # 1. 3 Aylık / 3 Ay
    if re.search(r"\b3\s*ay(lik)?\b", norm):
        return (
            "🗓️ **3 Aylık Popüler Üyelik ve Lisans Seçeneklerimiz:**\n\n"
            "1️⃣ **Minecraft Premium + Xbox Game Pass (3 Aylık)** — 119,90 ₺\n"
            "   👉 [Hemen Satın Al](https://www.shopier.com/50454347)\n\n"
            "2️⃣ **Gemini Advanced AI (3 Aylık Lisans)** — 59,90 ₺\n"
            "   👉 [Hemen Satın Al](https://www.shopier.com/50060935)\n\n"
            "3️⃣ **Duolingo Plus / Super (3 Aylık)** — 49,90 ₺\n"
            "   👉 [Hemen Satın Al](https://www.shopier.com/47669112)\n\n"
            "📌 Farklı bir 3 aylık servis (Örn: Spotify, VPN, Canva) mi arıyorsunuz? Servis adını yazmanız yeterlidir!\n"
            "🛍️ Tüm Ürünler: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 2. 1 Aylık / Aylık
    if re.search(r"\b(1\s*ay(lik)?|aylik)\b", norm):
        return (
            "🗓️ **1 Aylık En Çok Tercih Edilen Üyelikler:**\n\n"
            "1️⃣ **Netflix 4K UHD Ortak Profil** — 39,99 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50665156)\n\n"
            "2️⃣ **S Sport Plus Canlı Maç & Spor** — 70,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50576029)\n\n"
            "3️⃣ **ChatGPT Plus 4o (1 Aylık)** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669110)\n\n"
            "4️⃣ **Spotify Premium (1 Aylık)** — 29,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669111)\n\n"
            "5️⃣ **Minecraft Premium + Game Pass (1 Ay)** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50460191)\n\n"
            "📌 Hangi platform için aylık üyelik arıyorsunuz? Servis adını yazabilirsiniz.\n"
            "🛍️ Tüm Ürünler: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 3. Yıllık / 12 Aylık
    if re.search(r"\b(yillik|1\s*yillik|12\s*ay(lik)?)\b", norm):
        return (
            "🗓️ **1 Yıllık Orijinal Lisans ve Üyelik Seçeneklerimiz:**\n\n"
            "1️⃣ **Canva Pro (1 Yıllık Orijinal Lisans)** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669113)\n\n"
            "2️⃣ **Office 365 Pro Plus (1 Yıl / Ömür Boyu)** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669116)\n\n"
            "3️⃣ **Windows 10 / 11 Pro Orijinal Lisans** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669115)\n\n"
            "4️⃣ **CapCut Pro PC (1 Yıllık)** — 99,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669118)\n\n"
            "5️⃣ **Kaspersky Total Security Lisans** — 89,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669123)\n\n"
            f"6️⃣ **Duolingo Super 12 Ay - Kendi Hesabına Aktivasyon** — {personal_duolingo_price} ₺\n"
            f"   👉 [Hemen Satın Al]({personal_duolingo_url})\n\n"
            f"7️⃣ **Adobe Express 12 Ay - Kendi Hesabına Aktivasyon** — {personal_adobe_price} ₺\n"
            f"   👉 [Hemen Satın Al]({personal_adobe_url})\n\n"
            "📌 Aradığınız farklı bir program veya lisans var mı?\n"
            "🛍️ Tüm Ürünler: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 4. Ortak Profil / Ortak Hesap
    if re.search(r"\b(ortak|ortak profil|ortak hesap)\b", norm):
        return (
            "👥 **Ekonomik Ortak Profil Seçeneklerimiz:**\n\n"
            "1️⃣ **Netflix 4K UHD Ortak Profil** — 39,99 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50665156)\n\n"
            "2️⃣ **ChatGPT Plus Ortak Hesap** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669110)\n\n"
            "3️⃣ **Minecraft Premium Ortak Hesap** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50460191)\n\n"
            "4️⃣ **CapCut Pro Ortak Hesap** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669118)\n\n"
            "5️⃣ **Exxen Reklamsız Ortak** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669119)\n\n"
            "📌 Hangi servis için ortak profil istiyorsunuz? Servis adını yazarak direkt satın alma linkini alabilirsiniz.\n"
            "🛍️ Tüm Ürünler: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 5. Kişisel Profil / Kişisel Hesap
    if re.search(r"\b(kisisel|ozel|kendi hesabim)\b", norm):
        return (
            "👤 **Kişisel & Özel Profil Lisans Seçeneklerimiz:**\n\n"
            "1️⃣ **Netflix 4K UHD Kişisel Profil (Özel Pinli)** — 79,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669117)\n\n"
            "2️⃣ **Canva Pro Kişisel Mailinize Davet** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669113)\n\n"
            "3️⃣ **Office 365 Kişisel Lisans** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669116)\n\n"
            "4️⃣ **Spotify Premium Aile Daveti (Kendi Hesabınız)** — 29,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669111)\n\n"
            "5️⃣ **YouTube Premium Aile Daveti** — 39,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669114)\n\n"
            "📌 Hangi servis için kişisel hesap arıyorsunuz?\n"
            "🛍️ Tüm Ürünler: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 6. Kuponlar / İndirim Kodları
    if re.search(r"\b(kupon|indirim kodu|kuponlar|kodlar)\b", norm):
        return (
            "🎟️ **Güncel İndirim Kuponu & Kod Fırsatlarımız:**\n\n"
            "1️⃣ **Yemeksepeti İlk Sipariş 360/270** — 45,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024906)\n\n"
            "2️⃣ **Yemeksepeti İlk Sipariş 450/350** — 50,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024908)\n\n"
            "3️⃣ **Trendyol Market 800/300** — 50,00 ₺ | **Trendyol Yemek 750/250** — 50,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024904)\n\n"
            "4️⃣ **Positive 2.000 TL'ye 110 TL Puan** — 30,00 ₺ | **GastroClub 200 TL + %20** — 20,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024903)\n\n"
            "5️⃣ **Garenta %40** — 20,00 ₺ | **Enterprise %40** — 30,00 ₺ | **ENUYGUN Plus %10** — 20,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024901)\n\n"
            "6️⃣ **TikTak 1.000 TL Araç Kiralama Kodu** — 30,00 ₺ | **Coffy 2+1** — 45,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50641700)\n\n"
            "⚡ Kodlar sepette anında düşer, 7/24 otomatik teslim edilir!\n"
            "🛍️ Tüm Kuponlar: @KeyVadiSatisBot | Canlı Destek: @KeyvadiDestek"
        )

    # 7. Yemek
    if re.search(r"\b(yemek|yemek kuponu|restoran)\b", norm):
        return (
            "🍔 **Yemek & Restoran İndirim Kuponları:**\n\n"
            "1️⃣ **Yemeksepeti İlk Sipariş 360/270** — 45,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024906)\n\n"
            "2️⃣ **Yemeksepeti İlk Sipariş 450/350** — 50,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024908)\n\n"
            "3️⃣ **Trendyol Yemek 750/250** — 50,00 ₺ | **GastroClub 200 TL + %20** — 20,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024905)\n\n"
            "4️⃣ **Coffy 2 Kahve Alana 1'i Bedava Kodu** — 45,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50594322)\n\n"
            "⚡ Sepette anında indirim düşer, 7/24 anında teslimattır."
        )

    # 8. Market
    if re.search(r"\b(market|market kuponu|market bakiyesi)\b", norm):
        return (
            "🛒 **Süpermarket & Alışveriş Kuponları:**\n\n"
            "1️⃣ **Migros 100 TL Alışveriş Bakiye Kodu** — 50,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50594323)\n\n"
            "2️⃣ **Trendyol Market 800/300 İndirim Kodu** — 50,00 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/51024904)\n\n"
            "⚡ Kasada veya uygulamada anında 100 TL indirim sağlar!"
        )

    # 9. Oyun
    if re.search(r"\b(oyun|oyunlar|game)\b", norm):
        return (
            "🎮 **Popüler Oyun & Lisans Seçeneklerimiz:**\n\n"
            "1️⃣ **Minecraft + Game Pass (1 Aylık)** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50460191)\n\n"
            "2️⃣ **Minecraft + Game Pass (3 Aylık)** — 119,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/50454347)\n\n"
            "3️⃣ **Steam VIP Random Key** — 19,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669121)\n\n"
            "4️⃣ **EA FC 26 / FIFA Hesabı** — 89,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/49099017)\n\n"
            "5️⃣ **Roblox Offsale Kostümlü Hesap** — 49,90 ₺\n"
            "   👉 [Satın Al](https://www.shopier.com/47669124)\n\n"
            "📌 Aradığınız özel bir oyun varsa adını yazabilirsiniz!"
        )

    # 10. Fiyat Listesi / Katalog
    if re.search(r"\b(fiyat listesi|fiyatlar|katalog|menu|liste|urunler)\b", norm):
        return (
            "📋 **KeyVadi Popüler Ürün ve Fiyat Rehberi:**\n\n"
            "🎬 **Dizi, Film & Canlı Spor:**\n"
            "• Netflix 4K Ortak: 39,99 ₺ | Kişisel: 79,90 ₺\n"
            "• S Sport Plus (1 Ay): 70,00 ₺ | Exxen: 39,90 ₺ | Prime: 29,90 ₺\n\n"
            "🤖 **Yapay Zekâ (AI):**\n"
            "• ChatGPT Plus 4o: 39,90 ₺ | Gemini Adv (3 Ay): 59,90 ₺\n"
            "• Perplexity Pro: 49,90 ₺ | Claude Pro: 49,90 ₺\n\n"
            "💻 **Tasarım & Yazılım & Lisans:**\n"
            "• Canva Pro (1 Yıl): 39,90 ₺ | CapCut Pro: 39,90 ₺\n"
            f"• Duolingo Super 12 Ay kişisel: {personal_duolingo_price} ₺ | Adobe Express 12 Ay kişisel: {personal_adobe_price} ₺\n"
            "• Windows 10/11 Pro: 49,90 ₺ | Office 365: 49,90 ₺\n\n"
            "🎟️ **Yemek, Market & Kupon:**\n"
            "• Yemeksepeti 360/270: 45,00 ₺ | 450/350: 50,00 ₺ | Coffy 2+1: 45,00 ₺\n"
            "• Trendyol Market 800/300: 50,00 ₺ | Trendyol Yemek 750/250: 50,00 ₺\n"
            "• Positive 110 TL: 30,00 ₺ | GastroClub: 20,00 ₺ | Enterprise %40: 30,00 ₺\n"
            "• Garenta %40: 20,00 ₺ | ENUYGUN Plus %10: 20,00 ₺ | TikTak 1000 TL: 30,00 ₺\n"
            "• FLO / Lumberjack / In Street: 20,00 ₺ | Migros: 50,00 ₺\n\n"
            "🛍️ **Tüm 60+ Ürün:** @KeyVadiSatisBot\n"
            "💬 **Canlı Destek:** @KeyvadiDestek"
        )

    return None


def product_by_id(brand: str, product_id: str) -> dict | None:
    return next((item for item in load_sales_catalog(brand) if item["id"] == str(product_id)), None)


def _signing_secret() -> bytes:
    value = (
        os.environ.get("PURCHASE_LINK_SECRET")
        or os.environ.get("SHOPIER_CALLBACK_SECRET")
        or os.environ.get("TELEGRAM_API_HASH")
        or ""
    )
    return value.encode("utf-8")


def make_purchase_token(brand: str, product_id: str, source: str, arm: str = "",
                        cta_id: str = "") -> str | None:
    secret = _signing_secret()
    if not secret:
        return None
    payload = {
        "b": str(brand).lower(), "p": str(product_id), "s": str(source)[:40],
        "a": str(arm)[:16], "e": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
        "c": str(cta_id or os.urandom(8).hex())[:32],
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=")
    signature = hmac.new(secret, body, hashlib.sha256).digest()[:16]
    return (body + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode("ascii")


def parse_purchase_token(token: str) -> dict | None:
    secret = _signing_secret()
    if not secret or "." not in str(token):
        return None
    try:
        body, supplied = str(token).split(".", 1)
        expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()[:16]
        supplied_bytes = base64.urlsafe_b64decode(supplied + "=" * (-len(supplied) % 4))
        if not hmac.compare_digest(expected, supplied_bytes):
            return None
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        payload = json.loads(raw.decode("utf-8"))
        if int(payload.get("e", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None
        if payload.get("b") not in CATALOG_FILES or not product_by_id(payload["b"], payload.get("p", "")):
            return None
        return payload
    except Exception:
        return None


def purchase_url(product: dict, brand: str, source: str, arm: str = "") -> str:
    shopier_link = str(product.get("shopier_url") or product.get("url") or "")
    brand_name = str(brand).lower()
    if shopier_link and (
        is_allowed_shopier_url(shopier_link)
        and (
            brand_name != "lisansarena"
            or is_lisansarena_shopier_url(shopier_link)
            or str(product.get("shopier_owner") or "").casefold() == "lisansarena"
        )
    ):
        token = make_purchase_token(
            brand, product.get("id", ""), source, arm, product.get("_cta_id", "")
        )
        return f"{PUBLIC_BASE_URL}/go/{token}" if token else shopier_link
    if brand_name == "lisansarena":
        pid = product.get("id", "")
        return f"https://t.me/LisansArenaBot/app?startapp=p_{pid}" if pid else "https://t.me/LisansArenaBot/app"
    token = make_purchase_token(
        brand, product.get("id", ""), source, arm, product.get("_cta_id", "")
    )
    return f"{PUBLIC_BASE_URL}/go/{token}" if token else shopier_link


def listing_url(product: dict) -> str:
    """Return the public product listing URL shown to customers."""
    return str(product.get("url") or product.get("shopier_url") or "")


EXPERIMENT_START = datetime.fromisoformat(
    os.environ.get("CTA_EXPERIMENT_START", "2026-08-13T00:00:00+00:00").replace("Z", "+00:00")
)


def cta_experiment_status(now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    initial_end = EXPERIMENT_START + timedelta(days=3)
    final_end = EXPERIMENT_START + timedelta(days=7)
    if current < EXPERIMENT_START:
        phase = "scheduled"
    elif current < initial_end:
        phase = "initial_3_days"
    elif current < final_end:
        # Baseline traffic is below a reliable three-day sample, so keeping the
        # original split through day seven is the plan's automatic extension.
        phase = "extended_to_7_days"
    else:
        phase = "complete"
    return {
        "phase": phase,
        "start": EXPERIMENT_START.isoformat(),
        "initial_end": initial_end.isoformat(),
        "final_end": final_end.isoformat(),
    }


def cta_experiment_arm(brand: str, group_key: str) -> str:
    digest = hashlib.sha256(f"{brand.lower()}|{group_key.lower()}".encode("utf-8")).digest()
    return "test" if digest[0] % 2 else "control"


def cta_start_parameter(brand: str, group_key: str, arm: str) -> str:
    group_hash = hashlib.sha256(group_key.lower().encode("utf-8")).hexdigest()[:10]
    short_brand = "k" if brand.lower() == "keyvadi" else "f"
    short_arm = "t" if arm == "test" else "c"
    return f"cta_{short_brand}_{short_arm}_{group_hash}"


def parse_cta_start_parameter(value: str) -> dict | None:
    match = re.fullmatch(r"cta_([kf])_([ct])_([a-f0-9]{10})", str(value or ""))
    if not match:
        return None
    return {
        "brand": "keyvadi" if match.group(1) == "k" else "froxy",
        "arm": "test" if match.group(2) == "t" else "control",
        "group_hash": match.group(3),
    }


def apply_cta_experiment(message: str, brand: str, group_key: str) -> tuple[str, str]:
    """Legacy compatibility wrapper for the retired deep-link experiment.

    Outbound ads now use a raw visible @ handle.  Keeping this function
    entity-free prevents older callers from reintroducing a hidden start URL.
    """
    usernames = {
        "keyvadi": "KeyVadiSatisBot",
        "froxy": "FroxyDestekBOT",
        "lisansarena": "LisansArenaBot",
    }
    username = usernames.get(str(brand).casefold())
    if not username:
        return message, "none"
    updated = re.sub(r"\[([^\]]+)\]\((?:https?://|tg://)[^)]+\)", r"\1", message or "")
    updated = re.sub(r"(?i)(?:https?://|tg://|t\.me/)\S+", "", updated)
    updated = re.sub(r"(?i)\?start=[A-Za-z0-9_-]+", "", updated)
    if f"@{username}" not in updated:
        updated = f"{updated.rstrip()}\n@{username}".strip()
    return updated, "plain_mention"
