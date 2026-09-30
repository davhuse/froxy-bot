"""Build exact-text Disney profile listing covers for both storefronts."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SIZE = 1200
FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")

PRODUCTS = (
    ("KeyVadi", "Ortak Profil", "49,90 TL", "miniapp/assets/products/disney_ortak_49.png", (55, 190, 255)),
    ("KeyVadi", "Kişisel (Özel) Profil", "99,90 TL", "miniapp/assets/products/disney_ozel_99.png", (164, 120, 255)),
    ("LisansArena", "Ortak Profil", "69,90 TL", "miniapp_lisansarena/assets/products/disney_ortak_69.png", (52, 216, 196)),
    ("LisansArena", "Kişisel (Özel) Profil", "119,90 TL", "miniapp_lisansarena/assets/products/disney_ozel_119.png", (255, 180, 93)),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, size: int, fill, bold: bool = False) -> None:
    draw.text((SIZE // 2, y), text, font=font(size, bold), fill=fill, anchor="ma")


def cover(brand: str, profile: str, price: str, destination: str, accent: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (SIZE, SIZE))
    pixels = image.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        for x in range(SIZE):
            radial = max(0, 1 - ((x - 580) ** 2 + (y - 330) ** 2) ** .5 / 820)
            pixels[x, y] = (
                int(5 + 8 * (1 - t) + accent[0] * radial * .08),
                int(13 + 16 * (1 - t) + accent[1] * radial * .08),
                int(34 + 33 * (1 - t) + accent[2] * radial * .10),
            )

    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((180, 85, 1020, 915), fill=(*accent, 36))
    gd.arc((125, 110, 1075, 930), 205, 336, fill=(*accent, 150), width=10)
    gd.arc((175, 165, 1025, 875), 19, 152, fill=(255, 255, 255, 75), width=5)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    draw = ImageDraw.Draw(image)
    white = (245, 249, 255)
    muted = (169, 187, 215)
    draw.rounded_rectangle((62, 62, 1138, 1138), radius=42, outline=(*accent, 150), width=3)
    draw.text((108, 105), brand.upper(), font=font(36, True), fill=white)
    draw.rounded_rectangle((948, 94, 1090, 150), radius=27, fill=(*accent, 45), outline=accent, width=2)
    draw.text((1019, 121), "1 AY", font=font(30, True), fill=white, anchor="mm")
    centered(draw, "Disney+", 295, 148, white, True)
    draw.rounded_rectangle((210, 410, 990, 628), radius=35, fill=(12, 27, 56, 246), outline=(*accent, 235), width=4)
    centered(draw, "PROFİL TÜRÜ", 454, 29, muted, True)
    if profile == "Ortak Profil":
        centered(draw, "ORTAK PROFİL", 500, 67, white, True)
    else:
        centered(draw, "KİŞİSEL", 477, 67, white, True)
        centered(draw, "(ÖZEL) PROFİL", 553, 52, white, True)
    centered(draw, "MANUEL TESLİMAT", 685, 33, muted, True)
    draw.rounded_rectangle((160, 770, 1040, 948), radius=34, fill=(*accent, 48), outline=accent, width=3)
    centered(draw, price, 799, 86, white, True)
    centered(draw, "30 GÜN GARANTİ", 984, 40, white, True)
    centered(draw, "Sipariş bilgileri ürün açıklamasında", 1064, 25, muted)
    output = ROOT / destination
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    print(output)


if __name__ == "__main__":
    for product in PRODUCTS:
        cover(*product)
