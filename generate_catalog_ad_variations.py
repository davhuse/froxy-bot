"""Generate long ad variations from the three Mini App product catalogs.

The generated files are deliberately prefixed with ``full_`` so legacy
template tests do not confuse catalog slices with the hand-written fixtures.
Product titles are copied verbatim from the source JSON; this keeps the ad
catalog in sync with the storefront and makes product-name searches reliable.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MESSAGES = ROOT / "messages"


def load_products(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a product list in {path}")
    return [item for item in data if item.get("title")]


def price_text(item: dict) -> str:
    raw = item.get("price")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().replace(" TL", "₺")
    value = float(item.get("price_num", 0))
    return f"{value:,.2f}₺".replace(",", "X").replace(".", ",").replace("X", ".")


def balanced_chunks(items: list[dict], count: int) -> list[list[dict]]:
    count = max(1, min(count, len(items)))
    base, remainder = divmod(len(items), count)
    chunks: list[list[dict]] = []
    start = 0
    for index in range(count):
        size = base + (1 if index < remainder else 0)
        chunks.append(items[start : start + size])
        start += size
    return chunks


def write_keyvadi(chunks: list[list[dict]]) -> None:
    for index, products in enumerate(chunks, 1):
        lines = [
            f"[ KEYVADİ :: TAM KATALOG {index}/{len(chunks)} ] [ 7/24 ]",
            "KATEGORİ / GÜNCEL STOK VE FİYATLAR",
            "────────────────────────────────",
            "✓ Kod, davet, ortak ve kişisel seçenekler",
            "✓ Ürün adını yazarak doğru ilanı açtırabilirsiniz",
        ]
        for item in products:
            lines.append(f"• {item['title']} | {price_text(item)}")
        lines.extend([
            "────────────────────────────────",
            "✓ Fiyatlar mağazadaki güncel satış seçenekleridir",
            "✓ Anlık stok, hızlı teslimat ve canlı destek",
            "Mağaza, anlık stok ve güvenli ödeme: @KeyVadiSatisBot",
        ])
        (MESSAGES / f"full_keyvadi_{index}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_lisansarena(chunks: list[list[dict]]) -> None:
    for index, products in enumerate(chunks, 1):
        lines = [
            f"[ LİSANSARENA | TAM VİTRİN {index}/{len(chunks)} ] [ 7/24 ]",
            "━━ ÜRÜN KATALOĞU / BUGÜNÜN FIRSATLARI ━━",
            "✓ Lisans, abonelik, oyun ve kupon seçenekleri",
            "✓ Ürün adıyla arayın; güncel ilan doğrudan açılır",
            "✓ Katalogdaki her ürün bu rotasyonda yer alır",
        ]
        for item in products:
            lines.append(f"» {item['title']} · {price_text(item)}")
        lines.extend([
            "━━ ANLIK TESLİMAT ━━",
            "✓ Güvenli ödeme · hızlı teslimat · canlı destek",
            "✓ Stok ve fiyat bilgisi mağazayla senkron tutulur",
            "✓ Yeni varyasyonda farklı ürünler dönüşümlü gösterilir",
            "Mağaza ve sipariş hattı: @LisansArenaBot",
        ])
        (MESSAGES / f"full_lisansarena_{index}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_froxy(products: list[dict]) -> None:
    # Froxy has a compact catalogue, so every long variation carries the full
    # model menu.  The second variation reverses the product order to create a
    # real rotation while never hiding an available model.
    variants = [products, list(reversed(products))]
    for index, variant in enumerate(variants, 1):
        lines = [
            f"╭─ FROXY AI // TAM MODEL MENÜSÜ {index}/2 ─╮",
            "│ Gemini, ChatGPT, Codex ve üretim paketleri",
            "│ Model adını yazın; uygun Shopier ilanı açılsın",
            "│ Tüm ürünlerde güncel fiyat ve stok görünür",
        ]
        for item in variant:
            lines.append(f"│ {item['title']} .... {price_text(item)}")
        lines.extend([
            "│ Anlık stok · güvenli ödeme · hızlı teslimat",
            "╰─ Shopier mağazası ve anlık teslimat: @FroxyDestekBOT ─╯",
        ])
        (MESSAGES / f"full_froxy_{index}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    MESSAGES.mkdir(exist_ok=True)
    keyvadi = load_products(ROOT / "miniapp" / "products_db.json")
    lisansarena = load_products(ROOT / "miniapp_lisansarena" / "products_db.json")
    froxy = load_products(ROOT / "miniapp_froxy" / "products_db.json")
    write_keyvadi(balanced_chunks(keyvadi, 5))
    write_lisansarena(balanced_chunks(lisansarena, 5))
    write_froxy(froxy)
    print(f"Generated {len(keyvadi)} KeyVadi, {len(lisansarena)} LisansArena, {len(froxy)} Froxy products")


if __name__ == "__main__":
    main()
