"""Small, dependency-free Shopier showroom catalog helpers."""

from __future__ import annotations

import html
import re
import unicodedata
import urllib.request


def fetch_shopier_catalog(store_slug: str, timeout: int = 15) -> list[dict]:
    url = f"https://www.shopier.com/{store_slug}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TelegramSupportBot/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return parse_shopier_catalog(body, store_slug)


def parse_shopier_catalog(body: str, store_slug: str) -> list[dict]:
    products = []
    cards = body.split('class="product-card shopier--product-card')
    escaped_slug = re.escape(store_slug)
    for card in cards[1:]:
        link = re.search(
            rf'href="(https://www\.shopier\.com/{escaped_slug}/(\d+))"', card
        )
        title = re.search(
            r'class="shopier-store--store-product-card-title">([^<]+)</h3>', card
        )
        price = re.search(r'data-price="([^"]+)"', card)
        if not (link and title and price):
            continue
        products.append(
            {
                "id": link.group(2),
                "title": html.unescape(title.group(1).strip()),
                "price": re.sub(r"\s+", " ", price.group(1).strip()),
                "url": link.group(1),
            }
        )
    return products


def normalize_search_text(value: str) -> str:
    value = value.casefold().replace("ı", "i")
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def match_catalog_products(message: str, products: list[dict], limit: int = 4) -> list[dict]:
    query = normalize_search_text(message)
    if not query:
        return []
    query_tokens = set(query.split())
    aliases = {
        "gpt": "chatgpt",
        "antigravity": "gemini",
        "starter": "baslangic",
        "popular": "populer",
        "professional": "profesyonel",
        "5k": "baslangic",
        "15k": "populer",
        "50k": "profesyonel",
    }
    expanded_tokens = query_tokens | {aliases[token] for token in query_tokens if token in aliases}
    scored = []
    for product in products:
        title = normalize_search_text(str(product.get("title") or ""))
        title_tokens = set(title.split())
        overlap = expanded_tokens & title_tokens
        score = len(overlap) * 10
        if title and title in query:
            score += 50
        if "kisisel" in expanded_tokens and "kisisel" not in title_tokens:
            score -= 25
        if "ortak" in expanded_tokens and "ortak" not in title_tokens:
            score -= 25
        if "kredili" in expanded_tokens and "kredisiz" in title_tokens:
            score -= 25
        if "kredisiz" in expanded_tokens and "kredili" in title_tokens:
            score -= 25
        if score >= 10:
            scored.append((score, product))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("title") or "")))
    return [product for _score, product in scored[:limit]]
