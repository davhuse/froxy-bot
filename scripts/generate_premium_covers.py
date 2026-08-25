"""Generate clean, product-id keyed catalogue covers for the two mini apps.

The generated artwork intentionally keeps prices, keys, account ids and claims out
of the bitmap.  Those values belong to the live product catalogue, not the cover.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
LA_DB = ROOT / "miniapp_lisansarena" / "products_db.json"
KV_DB = ROOT / "miniapp" / "products_db.json"
LA_ASSETS = ROOT / "miniapp_lisansarena" / "assets" / "products"
KV_ASSETS = ROOT / "miniapp" / "assets" / "products"
BASE_DIR = ROOT / "scratch"
OUT_NAME = "premium_v2"

FONT_REG = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")


def norm(value: str) -> str:
    value = value.lower().replace("İ", "i").replace("ı", "i").replace("ş", "s")
    value = value.replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, bold: bool = False):
    size = start
    while size > 18:
        f = font(size, bold)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            return f
        size -= 2
    return font(18, bold)


def round_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def logo(draw: ImageDraw.ImageDraw, family: str, cx: int, cy: int, r: int, accent: tuple[int, int, int]):
    """Small deterministic brand marks; no model-generated lettering is used."""
    family = family.lower()
    if family == "youtube":
        round_rect(draw, (cx - r, cy - int(r * .62), cx + r, cy + int(r * .62)), int(r * .25), (238, 45, 55))
        draw.polygon([(cx - 10, cy - 20), (cx - 10, cy + 20), (cx + 24, cy)], fill=(255, 255, 255))
    elif family == "spotify":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(30, 215, 96))
        for off, width in [(-12, 8), (2, 7), (15, 6)]:
            draw.arc((cx - int(r * .62), cy + off - int(r * .32), cx + int(r * .62), cy + off + int(r * .32)), 205, 335, fill=(8, 38, 26), width=width)
    elif family == "instagram":
        round_rect(draw, (cx - r, cy - r, cx + r, cy + r), int(r * .28), (218, 55, 140))
        draw.ellipse((cx - int(r * .52), cy - int(r * .52), cx + int(r * .52), cy + int(r * .52)), outline=(255, 255, 255), width=max(5, r // 8))
        draw.ellipse((cx + int(r * .40), cy - int(r * .55), cx + int(r * .60), cy - int(r * .35)), fill=(255, 255, 255))
    elif family == "netflix":
        f = font(int(r * 1.55), True)
        draw.text((cx, cy - int(r * .82)), "N", font=f, anchor="mm", fill=(229, 9, 20))
    elif family == "canva":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(71, 202, 211), outline=(255, 255, 255), width=3)
        draw.text((cx, cy - 3), "C", font=font(int(r * 1.2), True), anchor="mm", fill=(116, 62, 214))
    elif family in {"gemini", "grok"}:
        pts = []
        for i in range(8):
            import math
            a = math.pi / 4 * i - math.pi / 2
            rr = r if i % 2 == 0 else int(r * .28)
            pts.append((cx + int(math.cos(a) * rr), cy + int(math.sin(a) * rr)))
        draw.polygon(pts, fill=accent)
        if family == "grok":
            draw.text((cx, cy), "X", font=font(int(r * .92), True), anchor="mm", fill=(20, 26, 35))
    elif family == "adobe":
        draw.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=int(r * .15), fill=(237, 70, 45))
        f = font(int(r * 1.1), True)
        draw.text((cx, cy + 2), "A", font=f, anchor="mm", fill=(255, 255, 255))
    elif family == "windows":
        s = int(r * .8)
        for dx, dy in [(-s - 4, -s - 4), (4, -s - 4), (-s - 4, 4), (4, 4)]:
            draw.rectangle((cx + dx, cy + dy, cx + dx + s, cy + dy + s), fill=(82, 177, 255))
    elif family == "gmail":
        round_rect(draw, (cx - r, cy - int(r * .72), cx + r, cy + int(r * .72)), int(r * .12), (255, 255, 255))
        draw.line([(cx - r + 8, cy - int(r * .65)), (cx, cy + 5), (cx + r - 8, cy - int(r * .65))], fill=(215, 55, 52), width=max(6, r // 7))
    elif family == "telegram":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(35, 160, 220))
        draw.polygon([(cx - int(r * .65), cy + int(r * .05)), (cx + int(r * .7), cy - int(r * .58)), (cx + int(r * .12), cy + int(r * .7)), (cx - int(r * .06), cy + int(r * .15))], fill=(255, 255, 255))
    elif family == "steam":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(28, 85, 132), outline=(255, 255, 255), width=4)
        draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), outline=(255, 255, 255), width=5)
        draw.line([(cx - 20, cy + 25), (cx - 2, cy + 8)], fill=(255, 255, 255), width=7)
    elif family == "roblox":
        draw.polygon([(cx - r + 8, cy - r // 2), (cx + r // 2, cy - r + 8), (cx + r - 8, cy + r // 2), (cx - r // 2, cy + r - 8)], fill=(235, 235, 240))
        draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(27, 31, 43))
    elif family == "shell":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 194, 27), outline=(220, 45, 30), width=5)
        for a in range(0, 180, 30):
            import math
            x = cx + int(math.cos(math.radians(a)) * r * .85)
            y = cy - int(math.sin(math.radians(a)) * r * .85)
            draw.line((cx, cy, x, y), fill=(220, 45, 30), width=4)
    elif family in {"trendyol_market", "trendyol_yemek"}:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 105, 35))
        draw.text((cx, cy), "t", font=font(int(r * 1.25), True), anchor="mm", fill=(255, 255, 255))
    elif family == "zula":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(235, 171, 45))
        draw.line((cx - int(r * .6), cy, cx + int(r * .6), cy), fill=(32, 35, 45), width=8)
        draw.line((cx, cy - int(r * .6), cx, cy + int(r * .6)), fill=(32, 35, 45), width=8)
    elif family == "freepik":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 203, 183))
        draw.text((cx, cy - 2), "f", font=font(int(r * 1.35), True), anchor="mm", fill=(255, 255, 255))
    elif family == "envato":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(126, 204, 74))
        draw.arc((cx - int(r * .45), cy - int(r * .75), cx + int(r * .75), cy + int(r * .55)), 280, 80, fill=(18, 80, 48), width=9)
    elif family == "semrush":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 115, 30))
        draw.polygon([(cx - 18, cy + 25), (cx - 4, cy - 18), (cx + 10, cy + 25)], fill=(255, 255, 255))
    elif family == "disney":
        draw.arc((cx - r, cy - int(r * .5), cx + r, cy + int(r * .9)), 190, 350, fill=(255, 255, 255), width=8)
        draw.text((cx, cy + 5), "Disney+", font=font(int(r * .55), True), anchor="mm", fill=(255, 255, 255))
    elif family == "magnific":
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(120, 86, 255))
        draw.text((cx, cy), "✦", font=font(int(r * 1.1), True), anchor="mm", fill=(255, 255, 255))
    else:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)


def classify(title: str) -> tuple[str, str, str] | None:
    t = norm(title)
    def months(default: str = ""):
        m = re.search(r"(1|3|4|6|12|14|18)\s*ay", t)
        return f"{m.group(1)} aylık" if m else default

    if "instagram" in t:
        return "instagram", "Instagram", "Takipçi paketi"
    if "canva" in t:
        if "ogretmen" in t: return "canva", "Canva Pro", "Öğretmen lisansı"
        if "ogrenci" in t: return "canva", "Canva Pro", "Öğrenci lisansı"
        return "canva", "Canva Pro", "1 yıllık yetki"
    if "netflix" in t:
        return "netflix", "Netflix", "4K · " + ("özel profil" if "ozel" in t or "kisisel" in t else "ortak profil")
    if "youtube" in t:
        return "youtube", "YouTube Premium", ("1 aylık davet" if "1 ay" in t else "3 aylık lisans")
    if "spotify" in t:
        return "spotify", "Spotify Premium", months("Premium erişim")
    if "exxen" in t:
        return "exxen", "Exxen", "Reklamsız · 3 aylık"
    if "gemini" in t:
        plan = "Ultra" if "ultra" in t else ("Advanced Pro" if "advanced" in t else "Pro")
        if "kredili" in t: return "gemini", "Gemini", f"{plan} · kredi hesabı"
        if "18 ay" in t: return "gemini", "Gemini", "Pro · 18 aylık"
        if "3 ay" in t: return "gemini", "Gemini", "Advanced Pro · 3 aylık"
        if "1 yillik" in t or "12 ay" in t: return "gemini", "Gemini", f"{plan} · 12 aylık"
        return "gemini", "Gemini", f"{plan} · davet"
    if "grok" in t:
        return "grok", "Grok", months("Premium hesap")
    if "telegram" in t:
        return "telegram", "Telegram", "Eski tarihli hesap"
    if "magnific" in t:
        return "magnific", "Magnific AI", "Business · ortak"
    if "adobe express" in t:
        return "adobe", "Adobe Express", months("3 aylık")
    if "adobe" in t:
        who = "bireysel" if "bireysel" in t or "kendi" in t else "ortak"
        return "adobe", "Adobe Creative Cloud", f"{months('1 aylık')} · {who}"
    if "prime video" in t or "amazon prime" in t:
        who = "özel profil" if "ozel" in t else "ortak profil"
        return "prime", "Prime Video", f"{months('4K')} · {who}"
    if "roblox" in t:
        return "roblox", "Roblox", "Offsale hesap paketi"
    if "envato" in t:
        return "envato", "Envato Elements", "1 aylık kişisel"
    if "freepik" in t:
        return "freepik", "Freepik Premium", "1 aylık kişisel"
    if "windows" in t:
        return "windows", "Windows Pro", "Windows 10/11 · dijital lisans"
    if "gmail" in t:
        return "gmail", "Gmail", "Hazır hesap"
    if "steam" in t and "istediginiz oyun" not in t:
        return "steam", "Steam", "Random Key"
    if "shell" in t:
        return "shell", "Shell", "Akaryakıt puanı"
    if "zula" in t:
        return "zula", "Zula", "Random hesap"
    if "semrush" in t:
        return "semrush", "Semrush", "Pro · 14 günlük"
    if "trendyol market" in t:
        return "trendyol_market", "Trendyol Market", "Kupon"
    if "trendyol yemek" in t:
        return "trendyol_yemek", "Trendyol Yemek", "Kupon"
    if "disney" in t:
        return "disney", "Disney+", "UHD · reklamsız · 1 aylık"
    if "capcut" in t:
        who = "ortak hesap" if "ortak" in t else ("kişisel lisans" if "kisisel" in t else "hesap")
        return "capcut", "CapCut Pro", f"{months('1 aylık')} · {who}"
    return None


THEME = {
    "instagram": "social", "canva": "design", "netflix": "streaming", "youtube": "streaming",
    "spotify": "streaming", "exxen": "streaming", "gemini": "ai", "grok": "ai",
    "telegram": "communication", "magnific": "design", "adobe": "design", "prime": "streaming",
    "roblox": "gaming", "steam": "gaming", "envato": "design", "freepik": "design",
    "windows": "security", "gmail": "security", "shell": "commerce", "zula": "gaming",
    "semrush": "ai", "trendyol_market": "commerce", "trendyol_yemek": "commerce", "disney": "streaming",
    "capcut": "design",
}

ACCENT = {
    "instagram": (224, 66, 155), "canva": (71, 202, 211), "netflix": (229, 9, 20), "youtube": (238, 45, 55),
    "spotify": (30, 215, 96), "exxen": (248, 201, 34), "gemini": (112, 187, 255), "grok": (255, 160, 92),
    "telegram": (35, 160, 220), "magnific": (144, 118, 255), "adobe": (237, 70, 45), "prime": (45, 172, 220),
    "roblox": (235, 235, 240), "steam": (100, 170, 235), "envato": (126, 204, 74), "freepik": (26, 203, 183),
    "windows": (82, 177, 255), "gmail": (237, 75, 70), "shell": (255, 194, 27), "zula": (235, 171, 45),
    "semrush": (255, 115, 30), "trendyol_market": (250, 105, 35), "trendyol_yemek": (250, 105, 35), "disney": (125, 180, 255),
    "capcut": (240, 240, 245),
}


def cover(product_id: str, family: str, title: str, package: str, base: Image.Image, store_label: str) -> Image.Image:
    img = base.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    # Darken the generated backdrop to guarantee readable deterministic typography.
    shade = Image.new("RGBA", img.size, (7, 12, 24, 58))
    img = Image.alpha_composite(img.convert("RGBA"), shade)
    d = ImageDraw.Draw(img)
    accent = ACCENT[family]
    # Top and bottom translucent panels form a consistent catalogue system.
    round_rect(d, (52, 52, 972, 224), 34, (7, 12, 24, 195), outline=(*accent, 110), width=2)
    round_rect(d, (52, 710, 972, 972), 34, (7, 12, 24, 210), outline=(*accent, 120), width=2)
    d.ellipse((88, 88, 200, 200), fill=(13, 20, 36, 225), outline=(*accent, 180), width=3)
    logo(d, family, 144, 144, 42, accent)
    d.text((232, 108), "PREMIUM ÜRÜN", font=font(24, True), fill=(190, 202, 222))
    d.text((232, 145), title, font=fit_text(d, title, 690, 54, True), fill=(255, 255, 255))
    # A clean package pill; no prices or claims are embedded.
    round_rect(d, (88, 770, 936, 882), 24, (*accent, 220))
    d.text((512, 826), package, font=fit_text(d, package, 780, 34, True), anchor="mm", fill=(10, 14, 26))
    d.text((88, 918), "Canlı katalogdan güvenli teslimat", font=font(22, False), fill=(205, 214, 230))
    d.text((936, 918), store_label, font=font(18, False), anchor="ra", fill=(150, 163, 184))
    # Keep a small neutral product id hash only for internal QA? No: never expose ids.
    return img.convert("RGB")


def load_products(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    LA_ASSETS.mkdir(parents=True, exist_ok=True)
    KV_ASSETS.mkdir(parents=True, exist_ok=True)
    bases = {k: Image.open(BASE_DIR / f"covergen_{k}.png") for k in {"social", "streaming", "ai", "design", "gaming", "commerce", "security", "communication"}}
    manifest: dict[str, dict[str, str]] = {"lisansarena": {}, "keyvadi": {}}
    changed = 0
    for label, db_path, asset_dir in [("lisansarena", LA_DB, LA_ASSETS), ("keyvadi", KV_DB, KV_ASSETS)]:
        data = load_products(db_path)
        for p in data:
            result = classify(p.get("title", ""))
            if not result:
                continue
            family, display_title, package = result
            # Preserve the already-good Steam game artwork, which is intentionally outside this refresh.
            if family == "steam" and "random" not in norm(p.get("title", "")) and "key" not in norm(p.get("title", "")):
                continue
            image_name = f"{OUT_NAME}_{p['id']}.jpg"
            out = asset_dir / image_name
            image = cover(str(p["id"]), family, display_title, package, bases[THEME[family]], "LisansArena" if label == "lisansarena" else "KeyVadi")
            image.save(out, format="JPEG", quality=93, optimize=True, progressive=True)
            p["image"] = f"assets/products/{image_name}"
            manifest[label][str(p["id"])] = {"image": p["image"], "family": family, "title": display_title, "package": package}
            changed += 1
        db_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (ROOT / "product_image_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated_products": changed, "lisansarena": len(manifest["lisansarena"]), "keyvadi": len(manifest["keyvadi"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
