"""Replace campaign Shopier listings when their media cannot be PUT-updated.

Shopier currently rejects PUT for the legacy/API product IDs in these shops.
This command creates a correct-cover replacement first, then deletes the old
listing and updates every local catalog with the replacement ID.
"""

from __future__ import annotations

import json
from pathlib import Path

from campaign_catalog import CAMPAIGNS
from sync_campaign_shopier import (
    ROOT,
    _create,
    _payload,
    _request,
    _shopier_url,
    _write_catalogs,
)


RESULTS = ROOT / "campaign_shopier_results.json"


def main() -> int:
    previous = json.loads(RESULTS.read_text(encoding="utf-8"))
    replacements: dict[tuple[str, str], tuple[str, str]] = {}
    old_ids: list[tuple[str, str, str]] = []
    for row in previous:
        brand = str(row["brand"])
        key = str(row["campaign"])
        old_id = str(row["id"])
        # Use the same POST implementation as the initial sync, but with the
        # corrected campaign_catalog image path.
        new_id, url = _create(brand, key)
        replacements[(brand, key)] = (new_id, url)
        old_ids.append((brand, key, old_id))
        print(f"[{brand}] yeni kapak: {key} -> {new_id}")

    # Only remove old listings after every replacement has been created.
    for brand, key, old_id in old_ids:
        try:
            _request(brand, "DELETE", f"https://api.shopier.com/v1/products/{old_id}")
            print(f"[{brand}] eski ilan kaldırıldı: {key} ({old_id})")
        except RuntimeError as exc:
            print(f"[{brand}] eski ilan silinemedi ({old_id}): {exc}")

    _write_catalogs(replacements)
    RESULTS.write_text(
        json.dumps(
            [
                {"brand": brand, "campaign": key, "id": product_id, "url": url}
                for (brand, key), (product_id, url) in sorted(replacements.items())
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Kapak yenileme tamamlandı: {len(replacements)} ürün")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

