"""Deterministic, privacy-safe classification for incoming sales messages.

The classifier deliberately uses conservative keyword rules.  It never makes
delivery or warranty promises and it keeps post-sale conversations out of the
automatic product-card flow.
"""

from __future__ import annotations

import re
import unicodedata


INTENT_SALES_LEAD = "sales_lead"
INTENT_AFTER_SALES = "after_sales"
INTENT_DELIVERY_PROBLEM = "delivery_problem"
INTENT_PAYMENT_QUESTION = "payment_question"
INTENT_HUMAN_SUPPORT = "human_support"


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold().replace("ı", "i"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    padded = f" {text} "
    return any(f" {phrase} " in padded or phrase in text for phrase in phrases)


_DELIVERY_PROBLEM = (
    "gelmedi", "ulasamadi", "teslim edilmedi", "kod calismiyor", "kod olmadi",
    "acilmiyor", "giremiyorum", "hatali", "yanlis", "patladi", "kapandi",
    "iptal oldu", "kullanamiyorum", "sifre yanlis", "bakiye yansimadi",
    "link calismiyor", "calismiyor", "sorun var", "hata veriyor", "iade",
)
_AFTER_SALES = (
    "tesekkur", "sagol", "aldim", "geldi", "teslim aldim", "tamamdir",
    "nasil kullan", "kurulum", "aktivasyon", "nereden gir", "hesaba nasil",
)
_PAYMENT = (
    "odeme", "iban", "dekont", "havale", "eft", "kartla", "taksit",
    "bakiye yukle", "para yatir", "shopier", "siparis notu",
)
_SALES = (
    "fiyat", "ne kadar", "almak", "alabilir", "satin", "stok", "mevcut",
    "kisisel", "ortak", "premium", "plus", "pro", "uyelik", "lisans",
    "kod", "profil", "paket", "aylik", "yillik", "garanti", "teslimat",
    "chatgpt", "chat gpt", "gpt", "gemini", "netflix", "youtube", "spotify",
    "canva", "capcut", "duolingo", "windows", "office", "adobe", "discord",
    "envato", "freepik", "exxen", "hbo", "prime", "perplexity", "vpn",
    "kaspersky", "trendyol", "steam", "xbox", "lisansarena", "froxy",
)


def classify_customer_message(message: str, *, product_matched: bool = False,
                              has_sales_context: bool = False) -> str:
    """Return one stable funnel/support class for a customer message."""
    text = _normalize(message)
    if not text:
        return INTENT_HUMAN_SUPPORT
    if _contains(text, _DELIVERY_PROBLEM):
        return INTENT_DELIVERY_PROBLEM
    if has_sales_context and _contains(text, _AFTER_SALES):
        return INTENT_AFTER_SALES
    if _contains(text, _PAYMENT) and not product_matched:
        return INTENT_PAYMENT_QUESTION
    if product_matched or _contains(text, _SALES):
        return INTENT_SALES_LEAD
    if has_sales_context:
        return INTENT_AFTER_SALES
    return INTENT_HUMAN_SUPPORT


def should_route_to_human(intent: str) -> bool:
    return intent in {
        INTENT_AFTER_SALES,
        INTENT_DELIVERY_PROBLEM,
        INTENT_PAYMENT_QUESTION,
        INTENT_HUMAN_SUPPORT,
    }
