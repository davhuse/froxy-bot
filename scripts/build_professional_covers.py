"""Replace the old generic Mini App covers with product-specific campaign art.

The seven illustrated backgrounds were generated with ImageGen. This script
typesets catalog text deterministically, so prices and Turkish characters are
not guessed by the image model. Existing campaign covers are left untouched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SIZE = 1200
FONT = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
BACKGROUNDS = ROOT / "cover_backgrounds"

PALETTES = {
    "food": ((255, 70, 84), (255, 255, 255)),
    "deals": ((255, 124, 36), (255, 255, 255)),
    "ai": ((33, 218, 252), (255, 255, 255)),
    "design": ((233, 92, 255), (255, 255, 255)),
    "gaming": ((118, 255, 91), (255, 255, 255)),
    "streaming": ((121, 110, 255), (255, 255, 255)),
    "education": ((114, 240, 91), (255, 255, 255)),
}


def face(size: int, bold: bool = True):
    return ImageFont.truetype(str(FONT if bold else FONT_REGULAR), size)


def classify(product: dict) -> str:
    title = str(product.get("title") or "").casefold()
    category = str(product.get("category") or "").casefold()
    if any(x in title for x in ("duolingo", "busuu", "lingokids", "eğitim", "kurs")):
        return "education"
    if any(x in title for x in ("yemeksepeti", "trendyol yemek", "migros", "coffy", "getir", "market")):
        return "food"
    if category in {"coupons", "deals"} or any(x in title for x in ("kupon", "uber", "uçak", "tiktak", "enuygun")):
        return "deals"
    if category in {"entertainment", "cinema", "social"} or any(x in title for x in ("disney", "netflix", "spotify", "youtube")):
        return "streaming"
    if category == "gaming":
        return "gaming"
    if category == "design":
        return "design"
    return "ai"


def wrap(draw: ImageDraw.ImageDraw, text: str, text_font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fitted_title(draw: ImageDraw.ImageDraw, title: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(76, 39, -2):
        current_font = face(size)
        lines = wrap(draw, title, current_font, 940)
        if len(lines) <= 4 and all(draw.textbbox((0, 0), line, font=current_font)[2] <= 940 for line in lines):
            return current_font, lines
    current_font = face(40)
    return current_font, wrap(draw, title, current_font, 940)


def render(product: dict, brand: str, destination: Path) -> None:
    kind = classify(product)
    accent, white = PALETTES[kind]
    image = ImageOps.fit(Image.open(BACKGROUNDS / f"{kind}.png").convert("RGB"), (SIZE, SIZE), method=Image.Resampling.LANCZOS)
    base = image.convert("RGBA")
    veil = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    vd.rounded_rectangle((55, 45, 1145, 1155), radius=45, fill=(2, 10, 32, 42), outline=(*accent, 225), width=4)
    vd.rounded_rectangle((112, 275, 1088, 875), radius=44, fill=(2, 10, 28, 185), outline=(*accent, 220), width=4)
    vd.rounded_rectangle((135, 936, 1065, 1085), radius=32, fill=(*accent, 235))
    base = Image.alpha_composite(base, veil)
    draw = ImageDraw.Draw(base)
    draw.text((110, 96), brand.upper(), font=face(36), fill=white, stroke_width=1, stroke_fill=(0, 0, 0))
    is_disney = str(product.get("title") or "").casefold().startswith("disney+")
    draw.rounded_rectangle((860, 88, 1080, 152), radius=28, fill=(3, 12, 34, 210), outline=accent, width=2)
    draw.text((970, 120), "1 AY" if is_disney else "DİJİTAL ÜRÜN",
              font=face(30 if is_disney else 27), fill=white, anchor="mm")

    title = re.sub(r"\s+", " ", str(product.get("title") or "").strip())
    if is_disney:
        draw.text((600, 360), "Disney+", font=face(112), fill=white,
                  anchor="mm", stroke_width=3, stroke_fill=(1, 8, 29))
        title = "KİŞİSEL (ÖZEL) PROFİL" if "özel" in title.casefold() or "kişisel" in title.casefold() else "ORTAK PROFİL"
    title_font, lines = fitted_title(draw, title)
    line_height = title_font.size + 17
    total_height = len(lines) * line_height
    top = max(330, (620 if is_disney else 548) - total_height // 2)
    for index, line in enumerate(lines):
        draw.text((600, top + index * line_height), line, font=title_font, fill=white,
                  anchor="ma", stroke_width=2, stroke_fill=(1, 8, 29))

    footer = "30 GÜN GARANTİ  •  MANUEL TESLİMAT" if is_disney else "ÜRÜN DETAYI VE TESLİMAT BİLGİSİ İLANDA"
    draw.text((600, 807), footer, font=face(30 if is_disney else 26, is_disney),
              fill=(211, 225, 244), anchor="mm")
    product_id = str(product.get("id") or "")
    price = str(product.get("price") or "").strip()
    if product_id in {"47669105", "47669159"} or not price:
        price = "FİYATI İLANDA GÖR"
    price_font = face(76 if len(price) < 18 else 57)
    draw.text((600, 1012), price, font=price_font, fill=(4, 14, 35), anchor="mm")
    destination.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destination, format="JPEG", quality=88, optimize=True, subsampling=0)


def update_app(app: str, brand: str) -> int:
    path = ROOT / app / "products_db.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for product in products:
        image = Path(str(product.get("image") or "")).name
        if not (image.startswith("cover_v7_") or image.startswith("la_")):
            continue
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(product["id"]))
        relative = f"assets/products/pro_{safe_id}.jpg"
        render(product, brand, ROOT / app / relative)
        product["image"] = relative
        count += 1
    path.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return count


if __name__ == "__main__":
    print("KeyVadi", update_app("miniapp", "KeyVadi"))
    print("LisansArena", update_app("miniapp_lisansarena", "LisansArena"))
