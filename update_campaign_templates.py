"""Refresh automatic advertisement templates with the canonical campaign prices."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = [*sorted((ROOT / "messages").glob("*.txt")), *sorted(ROOT.glob("message*.txt"))]

KEY_BLOCK = (
    "\n• Yemeksepeti İlk Sipariş 360/270: 45₺ | 450/350: 50₺\n"
    "• Trendyol Market 800/300: 50₺ | Trendyol Yemek 750/250: 50₺\n"
    "• Positive 110 TL: 30₺ | GastroClub: 20₺ | Enterprise %40: 30₺\n"
    "• Garenta %40: 20₺ | ENUYGUN %10: 20₺\n"
)
GEMINI_CANVA_LINE = "\n• Gemini Pro 18 Ay Kişiye Özel - 5 Davet Alana 1 Adet Canva Pro Hediye: 149,90₺\n"
LA_BLOCK = (
    "\n» Yemeksepeti İlk Sipariş 360/270: 55₺ | 450/350: 60₺\n"
    "» Trendyol Market 800/300: 60₺ | Trendyol Yemek 750/250: 60₺\n"
    "» Positive 110 TL: 35₺ | GastroClub: 25₺ | Enterprise %40: 35₺\n"
    "» Garenta %40: 30₺ | ENUYGUN %10: 30₺\n"
)


def main() -> int:
    changed = 0
    for path in FILES:
        name = path.name.casefold()
        is_keyvadi = "keyvadi" in name or name.startswith("message_2")
        is_lisansarena = "lisansarena" in name or name.startswith("message_3")
        if not (is_keyvadi or is_lisansarena):
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        if is_lisansarena:
            text = text.replace("450/350₺: 70₺", "450/350₺: 60₺")
            text = text.replace("450/350 Kupon 70₺", "450/350 Kupon 60₺")
            text = text.replace("450/350 70₺", "450/350 60₺")
            text = text.replace("450₺'ye 350₺ İndirim Kodu · 70₺", "450₺'ye 350₺ İndirim Kodu · 60₺")
            text = text.replace("Yemeksepeti 350 TL Kupon: 70 TL", "Yemeksepeti 450/350 Kupon: 60 TL")
        if is_keyvadi:
            text = text.replace(
                "Trendyol Market (800₺'ye 300₺ İndirim): 49.99₺",
                "Trendyol Market 800/300 İndirim Kodu: 50,00₺",
            )
            text = text.replace("Trendyol Market 49,99₺", "Trendyol Market 800/300 50₺")
            text = text.replace("Trendyol Market 49.99₺", "Trendyol Market 800/300 50₺")
            if "Gemini Pro 18 Ay Kişiye Özel" not in text and "short" not in name:
                text = text.rstrip() + GEMINI_CANVA_LINE
        # Long and regular store rotations receive the complete compact block.
        # The deliberately short strict templates are handled by
        # strict_group_safe_copy in otomatik_katil.py instead.
        if "short" not in name and "Positive 110 TL" not in text:
            text = text.rstrip() + (KEY_BLOCK if is_keyvadi else LA_BLOCK)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    print(f"Güncellenen reklam şablonu: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
