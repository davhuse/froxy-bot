"""Marketing cards module for high-converting Telegram broadcast notifications.

Generates visually rich, animated-emoji cards inspired by top digital stores:
- Price Drop! (Flash sales, strikethrough old prices, savings)
- Selling Fast — Only X Left! (Urgency / Scarcity FOMO)
- Custom Deal / Announcements
"""

import re
from telethon import Button


def get_product_brand_icon(title: str) -> str:
    """Return a fitting lively emoji based on product category or brand."""
    t = (title or "").lower()
    t_words = re.findall(r"\w+", t)
    if any(k in t for k in ["gemini", "grok", "chatgpt", "midjourney", "perplexity", "claude"]) or "ai" in t_words:
        return "💠"
    if any(k in t for k in ["capcut", "adobe", "canva", "figma", "video", "edit"]):
        return "✂️"
    if any(k in t for k in ["netflix", "prime", "disney", "exxen", "blutv", "hbo", "spotify", "crunchyroll"]):
        return "🎬"
    if any(k in t for k in ["xbox", "minecraft", "game pass", "steam", "fc26", "zula", "roblox", "pubg", "valorant"]):
        return "🎮"
    if any(k in t for k in ["windows", "office", "microsoft", "kaspersky", "antivirus", "vpn", "lisans"]):
        return "💻"
    return "⚡"


def format_price_str(price_val) -> str:
    """Format price nicely with TL currency if not already formatted."""
    if not price_val:
        return "0 TL"
    s = str(price_val).strip()
    if "tl" not in s.lower() and "$" not in s and "€" not in s:
        s = f"{s} TL"
    return s


def build_price_drop_card(
    title: str,
    new_price: str,
    old_price: str,
    buy_url: str,
    bulk_price: str = None,
    extra_details: str = None,
) -> tuple[str, list]:
    """Build a high-conversion 'Price Drop!' message card and action button."""
    icon = get_product_brand_icon(title)
    new_p = format_price_str(new_price)
    old_p = format_price_str(old_price)

    # Calculate discount percentage if numeric
    discount_pct = ""
    try:
        n_val = float(re.sub(r"[^\d.]", "", new_p.replace(",", ".")))
        o_val = float(re.sub(r"[^\d.]", "", old_p.replace(",", ".")))
        if o_val > n_val > 0:
            pct = round((1 - (n_val / o_val)) * 100)
            if pct > 0:
                discount_pct = f" *(%{pct} İndirim)*"
    except Exception:
        pass

    bulk_section = ""
    if bulk_price:
        b_p = format_price_str(bulk_price)
        bulk_section = (
            "\n💰 **Çok Al & Daha Çok Kazan:**\n"
            f"• 1 Adet: {new_p}\n"
            f"• 2+ Adet: {b_p}/adet\n"
        )

    text = (
        "🔥 **Price Drop! (Flaş Fiyat Düştü)**\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"{icon} **{title}**\n"
        f"💵 **Şimdi: {new_p}** · ~~{old_p}~~{discount_pct}\n"
        f"{bulk_section}\n"
        "⚡ **Anında Otomatik Teslimat**\n"
        "🎁 **7/24 Kesintisiz Değişim Garantisi**\n"
        "━━━━━━━━━━━━━━━━━\n"
        "👉 *Fırsat stoklarla sınırlıdır, hemen yakalayın!*"
    )

    buttons = [[Button.url(f"{icon} Fırsatı Yakala (Satın Al)", buy_url)]]
    return text, buttons


def build_selling_fast_card(
    title: str,
    price: str,
    remaining_count: int | str,
    buy_url: str,
    extra_note: str = None,
) -> tuple[str, list]:
    """Build a high-urgency 'Selling Fast — Only X Left!' message card and button."""
    icon = get_product_brand_icon(title)
    p_str = format_price_str(price)
    count_str = str(remaining_count).strip()

    note_text = extra_note or "Saniyeler içinde bot üzerinden anında teslim!"

    text = (
        f"🔥 **Selling Fast — Son {count_str} Stok Kaldı!**\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"{icon} **{title}**\n"
        f"💵 **Fiyat: {p_str}**\n\n"
        f"🎁 **Hazır Teslimat:** Stokta Son **{count_str}** Adet!\n"
        f"⚡ {note_text}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "👉 *Tükenmeden hemen sepetinize ekleyin!*"
    )

    buttons = [[Button.url(f"{icon} Tükenmeden Satın Al", buy_url)]]
    return text, buttons


def parse_fiyatdusur_args(raw_text: str):
    """Parse product query, new price, old price, and optional bulk price.

    Format: <urun> <yeni_fiyat> <eski_fiyat> [toplu_fiyat]
    Returns (prod_query, new_p, old_p, bulk_p) or None
    """
    if not raw_text or not raw_text.strip():
        return None
    tokens = raw_text.strip().split()
    if len(tokens) < 3:
        return None

    def _is_num(t):
        cleaned = re.sub(r"[^\d.]", "", t.replace(",", "."))
        return bool(cleaned and cleaned.replace(".", "", 1).isdigit())

    if len(tokens) >= 4 and _is_num(tokens[-1]) and _is_num(tokens[-2]) and _is_num(tokens[-3]):
        prod_query = " ".join(tokens[:-3])
        new_p = tokens[-3]
        old_p = tokens[-2]
        bulk_p = tokens[-1]
    elif _is_num(tokens[-1]) and _is_num(tokens[-2]):
        prod_query = " ".join(tokens[:-2])
        new_p = tokens[-2]
        old_p = tokens[-1]
        bulk_p = None
    else:
        return None

    if not prod_query:
        return None
    return prod_query, new_p, old_p, bulk_p


def parse_sonstok_args(raw_text: str):
    """Parse product query, remaining count, and optional price.

    Format: <urun> <kalan_adet> [fiyat]
    Returns (prod_query, count, price) or None
    """
    if not raw_text or not raw_text.strip():
        return None
    tokens = raw_text.strip().split()
    if len(tokens) < 2:
        return None

    def _is_num(t):
        cleaned = re.sub(r"[^\d.]", "", t.replace(",", "."))
        return bool(cleaned and cleaned.replace(".", "", 1).isdigit())

    if len(tokens) >= 3 and _is_num(tokens[-1]) and tokens[-2].isdigit():
        prod_query = " ".join(tokens[:-2])
        count = int(tokens[-2])
        price = tokens[-1]
    elif tokens[-1].isdigit():
        prod_query = " ".join(tokens[:-1])
        count = int(tokens[-1])
        price = None
    else:
        return None

    if not prod_query:
        return None
    return prod_query, count, price

