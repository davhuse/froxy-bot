import os
from pathlib import Path

p_dir = Path("miniapp/assets")
mockups = list(p_dir.glob("*mockup*.png"))
products_png = list((p_dir / "products").glob("product_*.png"))

print(f"KeyVadi Mockups found: {len(mockups)}")
for m in mockups[:15]:
    print(" ", m.name)

print(f"KeyVadi Products PNG found: {len(products_png)}")
for p in products_png[:15]:
    print(" ", p.name)
