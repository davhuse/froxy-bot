"""Create a readable approval copy of the eleven prepared Shopier listings."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
products = json.loads((ROOT / "jarvis_subscriptions.json").read_text(encoding="utf-8"))
published = json.loads((ROOT / "jarvis_shopier_products.json").read_text(encoding="utf-8"))
by_key = {row.get("key"): row for row in published}
parts = [
    "# JarvisCraft Shopier ilanları",
    "",
    "On bir ürün Shopier API üzerinden yayımlandı. Tüm ürünler manuel teslim edilir.",
    "",
]
for product in products:
    image = f"../static/jarvis_subscriptions/{product['key']}-ai.png"
    listing = by_key.get(product["key"], {})
    parts += [
        f"## {product['title']}",
        "",
        f"- **Fiyat:** {product['price'].replace('.', ',')} TL",
        "- **Teslimat:** Manuel teslimat",
        f"- **Garanti:** {product['warranty'] or 'Belirtilmiyor'}",
        f"- **Kapak:** [{product['key']}-ai.png]({image})",
        f"- **Shopier bağlantısı:** {listing.get('url') or 'Henüz yayımlanmadı'}",
        "",
        "**Shopier açıklaması**",
        "",
        product["description"],
        "",
    ]

output = ROOT / "previews" / "shopier-ilanlari.md"
output.write_text("\n".join(parts), encoding="utf-8")
print(f"{output}: {len(products)} published listings")
