"""Build deterministic, price-safe KeyVadi covers from generated category art."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "miniapp" / "products_db.json"
ASSET_ROOT = ROOT / "miniapp" / "assets"
BACKGROUND_ROOT = ASSET_ROOT / "cover_backgrounds"
OUTPUT_ROOT = ASSET_ROOT / "products" / "premium"

CATEGORY_MAP = {
    "ai": ("ai", "YAPAY ZEKÂ"),
    "design": ("design", "TASARIM & ÇALIŞMA"),
    "software": ("design", "TASARIM & ÇALIŞMA"),
    "entertainment": ("entertainment", "EĞLENCE"),
    "streaming": ("entertainment", "EĞLENCE"),
    "gaming": ("gaming", "OYUN"),
    "security": ("security", "GÜVENLİK"),
    "coupons": ("deals", "FIRSATLAR"),
    "other": ("deals", "FIRSATLAR"),
}

TITLE_FIXES = {
    "49362885": "Kaspersky Premium 1 Yıl / 1 Cihaz",
    "49362864": "YouTube Premium 1 Ay - Kendi Hesabına Davet",
    "49362861": "ChatGPT Plus 30 Gün - Ortak Hesap",
    "49362708": "Gemini Advanced Pro 3 Ay - Davet Bağlantısı",
    "49099017": "FC 26 Hesabı - Bilgileri Değiştirilebilir",
    "47669390": "Duolingo Super - Sınıf Daveti",
    "47669356": "Adobe Creative Cloud (1 Aylık)",
    "47669321": "Canva Pro 1 Yıl - Kendi Hesabına Davet",
    "49682367": "Gemini Pro 18 Ay - Davet Bağlantısı",
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


FONT_BRAND = font("segoeuib.ttf", 28)
FONT_LABEL = font("seguisb.ttf", 24)
FONT_TITLE = font("segoeuib.ttf", 58)
FONT_PRICE_LABEL = font("seguisb.ttf", 22)
FONT_PRICE = font("segoeuib.ttf", 66)
FONT_MONOGRAM = font("segoeuib.ttf", 50)


def wrap_text(draw: ImageDraw.ImageDraw, value: str, max_width: int, max_lines: int = 4):
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposed = f"{current} {word}".strip()
        if draw.textbbox((0, 0), proposed, font=FONT_TITLE)[2] <= max_width:
            current = proposed
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textbbox((0, 0), lines[-1] + "…", font=FONT_TITLE)[2] > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def product_category(product: dict) -> tuple[str, str]:
    title = str(product.get("title") or "").casefold()
    if any(word in title for word in ("kaspersky", "antivir", "vpn")):
        return "security", "GÜVENLİK"
    if any(word in title for word in ("netflix", "youtube", "spotify", "exxen", "disney", "prime video", "hbo", "crunchyroll", "scribd", "duolingo")):
        return "entertainment", "EĞLENCE"
    if any(word in title for word in ("office", "windows", "semrush", "canva", "adobe", "capcut", "gamma", "grammarly")):
        return "design", "TASARIM & ÇALIŞMA"
    return CATEGORY_MAP.get(str(product.get("category") or "other"), ("deals", "FIRSATLAR"))


def category_mark(background_key: str) -> str:
    return {
        "ai": "AI",
        "design": "PRO",
        "entertainment": "PLAY",
        "gaming": "GAME",
        "security": "SAFE",
        "deals": "DEAL",
    }.get(background_key, "KV")


def build_cover(product: dict, background_key: str, label: str) -> Path:
    source = BACKGROUND_ROOT / f"{background_key}.png"
    image = ImageOps.fit(Image.open(source).convert("RGB"), (1024, 1024), method=Image.Resampling.LANCZOS)
    digest = hashlib.sha256(str(product["id"]).encode()).digest()
    if digest[0] % 2:
        image = ImageOps.mirror(image)
    image = ImageEnhance.Color(image).enhance(0.88 + (digest[1] / 255) * 0.20)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pixels = overlay.load()
    for x in range(1024):
        alpha = int(max(24, 232 - x * 0.20))
        for y in range(1024):
            bottom = int(max(0, (y - 660) * 0.22))
            pixels[x, y] = (4, 8, 14, min(245, alpha + bottom))
    composed = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(composed)

    draw.rounded_rectangle((58, 54, 258, 101), radius=20, fill=(8, 18, 26, 220), outline=(59, 224, 238, 130), width=2)
    draw.text((78, 63), "KEYVADI", font=FONT_BRAND, fill=(228, 251, 255, 255))
    label_box = draw.textbbox((0, 0), label, font=FONT_LABEL)
    label_width = label_box[2] - label_box[0]
    draw.rounded_rectangle((58, 130, 92 + label_width, 174), radius=18, fill=(255, 255, 255, 24))
    draw.text((76, 137), label, font=FONT_LABEL, fill=(119, 237, 246, 255))

    lines = wrap_text(draw, product["title"], 610)
    title_y = 220
    for line in lines:
        draw.text((58, title_y), line, font=FONT_TITLE, fill=(250, 252, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 170))
        title_y += 72

    badge_x, badge_y = 790, 90
    draw.ellipse((badge_x, badge_y, badge_x + 150, badge_y + 150), fill=(7, 15, 24, 215), outline=(255, 255, 255, 48), width=3)
    mark = category_mark(background_key)
    box = draw.textbbox((0, 0), mark, font=FONT_MONOGRAM)
    draw.text((badge_x + 75 - (box[2] - box[0]) / 2, badge_y + 70 - (box[3] - box[1]) / 2), mark, font=FONT_MONOGRAM, fill=(255, 255, 255, 225))

    draw.text((60, 839), "GÜNCEL FİYAT", font=FONT_PRICE_LABEL, fill=(158, 174, 190, 255))
    draw.text((58, 870), product["price"], font=FONT_PRICE, fill=(255, 255, 255, 255))
    draw.rounded_rectangle((58, 966, 430, 994), radius=14, fill=(48, 216, 232, 42))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_ROOT / f"kv_premium_{product['id']}.jpg"
    composed.convert("RGB").save(output, "JPEG", quality=90, optimize=True, progressive=True)
    return output


def main():
    products = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for product in products:
        product_id = str(product.get("id"))
        if product_id in TITLE_FIXES:
            product["title"] = TITLE_FIXES[product_id]
        background_key, category_label = product_category(product)
        product["category"] = background_key
        product["category_label"] = category_label
        product["price_num"] = round(float(product.get("price_num") or 0), 2)
        product["price"] = f"{product['price_num']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
        product["delivery_type"] = str(product.get("delivery_type") or "manual")
        product["delivery_label"] = str(product.get("delivery_label") or "Teslimat ve uygunluk ödeme öncesi doğrulanır")
        product["max_qty"] = max(1, min(int(product.get("max_qty") or 1), 10))
        product["description"] = (
            f"{product['title']}. Teslimat yöntemi, hesap uygunluğu ve varsa garanti süresi "
            "ödeme öncesinde ürün detayında doğrulanır."
        )
        output = build_cover(product, background_key, category_label)
        product["image"] = output.relative_to(ROOT / "miniapp").as_posix()

    CATALOG_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(products)} covers in {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
