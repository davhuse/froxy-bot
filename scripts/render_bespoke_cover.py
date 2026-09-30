"""Typeset exact catalog text on a product-specific generated scene."""

from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


SIZE = 1200
BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")


def font(size: int, *, bold: bool = True):
    return ImageFont.truetype(str(BOLD if bold else REGULAR), size)


def wrap(draw, value: str, text_font, max_width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in value.split():
        candidate = word if not line else line + " " + word
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit(draw, title: str, max_width: int = 910, max_lines: int = 4):
    for size in range(92, 37, -2):
        candidate_font = font(size)
        lines = wrap(draw, title, candidate_font, max_width)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), x, font=candidate_font)[2] <= max_width for x in lines):
            return candidate_font, lines
    candidate_font = font(38)
    return candidate_font, wrap(draw, title, candidate_font, max_width)


def render(source: Path, output: Path, *, brand: str, title: str, price: str,
           badge: str = "DİJİTAL ÜRÜN", guarantee: str = "") -> None:
    image = ImageOps.fit(Image.open(source).convert("RGB"), (SIZE, SIZE), method=Image.Resampling.LANCZOS).convert("RGBA")
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dark = (11, 23, 46)
    white = (255, 255, 255)
    orange = (255, 123, 36)
    draw.rounded_rectangle((58, 45, 1142, 161), radius=38, fill=(5, 16, 38, 224), outline=(255, 255, 255, 155), width=3)
    draw.text((103, 101), brand.upper(), font=font(37), fill=white, anchor="lm")
    draw.rounded_rectangle((865, 71, 1097, 137), radius=29, fill=orange)
    draw.text((981, 103), badge, font=font(27), fill=dark, anchor="mm")

    # Solid paper card gives the text the visual priority of the supplied ad references.
    draw.rounded_rectangle((82, 635, 1118, 1125), radius=48, fill=(255, 255, 255, 251), outline=orange, width=6)
    draw.rounded_rectangle((118, 922, 1082, 1039), radius=26, fill=orange)
    draw.rounded_rectangle((345, 1060, 855, 1109), radius=23, fill=dark)
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)
    if title.casefold().startswith("disney+"):
        draw.text((600, 495), "Disney+", font=font(126), fill=white, anchor="mm", stroke_width=6, stroke_fill=dark)
        main = "KİŞİSEL (ÖZEL) PROFİL" if "kişisel" in title.casefold() or "özel" in title.casefold() else "ORTAK PROFİL"
    else:
        main = title
    title_font, lines = fit(draw, main)
    line_height = title_font.size + 13
    start_y = 780 - (len(lines) - 1) * line_height // 2
    for index, line in enumerate(lines):
        draw.text((600, start_y + index * line_height), line, font=title_font, fill=dark, anchor="mm")
    draw.text((600, 981), price, font=font(90 if len(price) < 18 else 62), fill=dark, anchor="mm")
    draw.text((600, 1084), guarantee or "DETAYLAR İLAN AÇIKLAMASINDA", font=font(26), fill=white, anchor="mm")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="JPEG", quality=90, optimize=True, subsampling=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--price", required=True)
    parser.add_argument("--badge", default="DİJİTAL ÜRÜN")
    parser.add_argument("--guarantee", default="")
    args = parser.parse_args()
    render(args.source, args.output, brand=args.brand, title=args.title, price=args.price,
           badge=args.badge, guarantee=args.guarantee)
