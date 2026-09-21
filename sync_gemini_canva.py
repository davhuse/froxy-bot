"""Replace the KeyVadi Gemini 18-month listing with the Canva referral offer."""

from __future__ import annotations

import json
from pathlib import Path

from sync_campaign_shopier import API, ROOT, _request
from upload_campaign_covers import upload


OLD_ID = "50602543"
TITLE = "Gemini Pro 18 Ay Kişiye Özel - 5 Davet Alana 1 Adet Canva Pro Hediye"
PRICE = 149.90
IMAGE_RELATIVE = "assets/products/campaign_gemini_18_canva.png"
IMAGE_PATH = ROOT / "miniapp" / "assets" / "products" / "campaign_gemini_18_canva.png"
DESCRIPTION = (
    "Google Gemini Pro (Advanced) 18 aylık kişiye özel aktivasyon bağlantısıdır; "
    "kendi Google hesabınızda kullanılır. 5 geçerli davet tamamlayan müşteriye "
    "1 adet Canva Pro hediye edilir. Hediye, 5 davetin doğrulanmasından sonra teslim edilir.\n\n"
    "Ürün; 5 kişiye kadar aile/arkadaş daveti, 2 TB Google One depolama alanı ve "
    "Gemini 1.5 Pro gelişmiş yapay zekâ modeline erişim içerir. Aktivasyon bağlantısı "
    "ödeme sonrası anında iletilir."
)


def payload(media_url: str) -> dict:
    price = f"{PRICE:.2f}"
    return {
        "title": TITLE,
        "type": "digital",
        "description": DESCRIPTION,
        "media": [{"type": "image", "url": media_url, "placement": 1}],
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


def shopier_url(body: dict, product_id: str) -> str:
    return str(body.get("url") or f"https://www.shopier.com/{product_id}").strip()


def replace_item(items: list[dict], new_item: dict, *, links: bool) -> list[dict]:
    result: list[dict] = []
    replaced = False
    for item in items:
        if str(item.get("id") or "") == OLD_ID:
            if not replaced:
                result.append(new_item)
                replaced = True
            continue
        result.append(item)
    if not replaced:
        result.insert(0, new_item)
    return result


def main() -> int:
    if not IMAGE_PATH.is_file():
        raise SystemExit(f"Kapak bulunamadı: {IMAGE_PATH}")

    media_url = upload(IMAGE_PATH)
    print(f"Kapak yüklendi: {media_url}")
    body = _request("keyvadi", "POST", API, payload(media_url))
    product_id = str(body.get("id") or "").strip()
    if not product_id:
        raise SystemExit("Shopier yeni ürün ID döndürmedi")
    url = shopier_url(body, product_id)
    print(f"Yeni ilan oluşturuldu: {product_id}")

    # Replacement is created first so the existing listing is never lost if POST fails.
    try:
        _request("keyvadi", "DELETE", f"{API}/{OLD_ID}")
        print(f"Eski ilan silindi: {OLD_ID}")
    except RuntimeError as exc:
        print(f"UYARI: eski ilan silinemedi ({OLD_ID}): {exc}")

    links_path = ROOT / "keyvadi_shopier_links.json"
    links = json.loads(links_path.read_text(encoding="utf-8"))
    links = replace_item(
        links,
        {"id": product_id, "title": TITLE, "price": "149.90 TL", "url": url},
        links=True,
    )
    links_path.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mini_path = ROOT / "miniapp" / "products_db.json"
    products = json.loads(mini_path.read_text(encoding="utf-8"))
    product = {
        "id": product_id,
        "title": TITLE,
        "price": "149,90 TL",
        "price_num": PRICE,
        "category": "ai",
        "image": IMAGE_RELATIVE,
        "badge": "🎁 5 Davet = Canva Pro",
        "url": url,
        "description": DESCRIPTION,
        "showcase": True,
        "is_vitrin": True,
        "category_label": "YAPAY ZEKA & AI",
        "delivery_type": "instant",
        "delivery_label": "Anında Bağlantı Teslimatı",
        "max_qty": 1,
    }
    products = replace_item(products, product, links=False)
    mini_path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_path = ROOT / "gemini_canva_shopier_result.json"
    result_path.write_text(
        json.dumps(
            {
                "old_id": OLD_ID,
                "id": product_id,
                "url": url,
                "title": TITLE,
                "price": PRICE,
                "media_url": media_url,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Yerel kataloglar güncellendi: {product_id} -> {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
