"""Refresh approved storefront covers while preserving product data.

Campaign artwork already has purpose-built covers, so this script keeps those
files intact and regenerates the older generic/mismatched product covers from
the existing KeyVadi/LisansArena cover engines.  Each generated cover gets the
current product title and price rendered from the live local catalogue.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from build_exact_listing_covers import create_product_banner
from build_lisansarena_unique_covers import create_lisansarena_banner


ROOT = Path(__file__).resolve().parent


def refresh(path: Path, output_dir: Path, prefix: str, renderer) -> int:
    products = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for product in products:
        current = str(product.get("image") or "")
        # Purpose-built campaign artwork is already a corrected cover.
        if "campaign_" in Path(current).name:
            continue
        product_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(product.get("id") or "product"))
        filename = f"{prefix}_{product_id}.jpg"
        destination = output_dir / filename
        renderer(product, str(destination))
        product["image"] = f"assets/products/{filename}"
        changed += 1
    path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    kv_count = refresh(
        ROOT / "miniapp" / "products_db.json",
        ROOT / "miniapp" / "assets" / "products",
        "cover_v7",
        create_product_banner,
    )
    la_count = refresh(
        ROOT / "miniapp_lisansarena" / "products_db.json",
        ROOT / "miniapp_lisansarena" / "assets" / "products",
        "la_gold_v7",
        create_lisansarena_banner,
    )
    print(f"KeyVadi kapakları yenilendi: {kv_count}")
    print(f"LisansArena kapakları yenilendi: {la_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
