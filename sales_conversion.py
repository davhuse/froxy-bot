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
}

BRAND_PHRASES = (
    "chatgpt", "netflix", "youtube", "adobe", "canva", "windows", "office",
    "gemini", "grok", "xbox", "spotify", "exxen", "trendyol yemek",
    "trendyol market", "duolingo", "semrush", "capcut", "scribd", "gamma",
    "kiro", "steam", "shell", "whatsapp", "apple", "crunchyroll", "telegram", "blutv",
    "midjourney", "tradingview", "nordvpn", "vpn", "kaspersky", "envato",
    "freepik", "autocad", "figma", "elementor", "grammarly", "deepl",
    "ideogram", "quillbot", "discord", "hbo", "prime video", "prime", "perplexity",
    "magnific", "zula", "fc 26", "fc26", "codex", "antigravity", "disney", "minecraft",
    "cape", "pelerin", "roblox", "instagram", "takipci", "gmail", "claude",
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
    ("keyvadi", "47669117"): "79,90 TL",
    ("lisansarena", "la_netflix_ozel"): "84,90 TL",
    ("lisansarena", "49002144"): "84,90 TL",
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
    url = str(item.get("url") or item.get("link") or "").strip()
    if not url and str(brand).lower() == "lisansarena" and product_id:
        url = f"{PUBLIC_BASE_URL}/la/app?product={quote(product_id, safe='')}"
    if not product_id or not title or not (is_allowed_shopier_url(url) or is_allowed_internal_purchase_url(url)):
        return None
    lower_title = title.lower()
    if any(k in lower_title for k in ("bakiye", "cüzdan", "cuzdan", "yükleme", "yukleme")):
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


def purchase_target_url(brand: str, product: dict) -> str:
    """Return the product-specific Shopier or Mini App purchase target."""
    if str(brand).lower() == "lisansarena":
        pid = product.get("id", "")
        return f"https://t.me/LisansArenaBot/app?startapp=p_{pid}" if pid else "https://t.me/LisansArenaBot/app"
    return str(product.get("url") or product.get("shopier_url") or "")


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
        if brands and not matching_brands and len(overlap) < 2:
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
        scored.append((score, product))
        
    scored.sort(key=lambda pair: (-pair[0], _price_number(pair[1].get("price")), pair[1]["title"]))
    if not scored:
        return []
    if ("kisisel" in query_tokens or "ortak" in query_tokens) and scored:
        return [scored[0][1]]
    if "chatgpt" in query_tokens and "codex" in query_tokens and scored:
        return [scored[0][1]]
    if variant_tokens and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 25):
        return [scored[0][1]]
    return [product for _score, product in scored[: max(1, min(limit, 3))]]


def _price_number(value: str) -> float:
    cleaned = re.sub(r"[^0-9,.]", "", str(value or "")).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 999999.0


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
    if str(brand).lower() == "lisansarena":
        pid = product.get("id", "")
        return f"https://t.me/LisansArenaBot/app?startapp=p_{pid}" if pid else "https://t.me/LisansArenaBot/app"
    token = make_purchase_token(
        brand, product.get("id", ""), source, arm, product.get("_cta_id", "")
    )
    return f"{PUBLIC_BASE_URL}/go/{token}" if token else str(product.get("url") or product.get("shopier_url") or "")


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
