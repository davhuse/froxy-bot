"""Telegram advertising group policy and moderation state.

Policies are resolved by Telegram's permanent numeric chat id first.  Usernames
are retained only as bootstrap aliases because they can be renamed.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
import re
import unicodedata


POLICY_FILE = os.environ.get("GROUP_POLICY_FILE", "group_policies.json")
MODERATION_FILE = os.environ.get("GROUP_MODERATION_FILE", "group_moderation.json")
PLAIN_KEYVADI_CTA = "Sipariş için Telegram aramasına KeyVadiSatisBot yazabilirsiniz."

DEFAULT_POLICY = {
    "allow_urls": True,
    "allow_deep_links": True,
    "allow_mentions": True,
    "allow_media": True,
    "allow_emojis": True,
    "max_lines": None,
    "forbidden_products": [],
    "account_hold": [],
    "hold_reason": "",
}

SEEDED_POLICIES = {
    # 𝐊𝐎𝐃 𝐕𝐄 𝐊𝐔𝐏𝐎𝐍 𝐒𝐀𝐓𝐈Ş 𝐆𝐑𝐔𝐁𝐔 / @ceksatkupon2
    "id:3065608337": {
        "aliases": ["ceksatkupon2"],
        "allow_urls": False,
        "allow_deep_links": False,
        "allow_mentions": False,
        "allow_media": False,
        "allow_emojis": False,
        "max_lines": None,
        "forbidden_products": [],
        "account_hold": [],
        "hold_reason": "Link ve bağlantı önizlemesi yasak; yalnız sade metin.",
    },
    # Kupon Çek Kod Satışı / @kuponcekkodsatis
    "id:1511926667": {
        "aliases": ["kuponcekkodsatis"],
        "allow_urls": False,
        "allow_deep_links": False,
        "allow_mentions": False,
        "allow_media": False,
        "allow_emojis": False,
        "max_lines": None,
        "forbidden_products": [],
        "account_hold": ["keyvadi"],
        "hold_reason": "@ceksatkupon2 sade metin smoke testi 10 dakika görünür kalana kadar beklemede.",
    },
    # İbr Çek-Sat Kupon / @ceksatkupon
    "id:2780340773": {
        "aliases": ["ceksatkupon"],
        "allow_urls": False,
        "allow_deep_links": False,
        "allow_mentions": False,
        "allow_media": False,
        "allow_emojis": False,
        "max_lines": None,
        "forbidden_products": [],
        "account_hold": ["keyvadi"],
        "hold_reason": "Combot CAS spam incelemesi bekleniyor; denetim aşılmayacak.",
    },
}


def _atomic_json(path: str, value: dict) -> None:
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def normalize_group(value) -> str:
    text = str(value or "").strip().lower().lstrip("@")
    return re.sub(r"[^a-z0-9_-]", "", text)


def numeric_group_id(value) -> str:
    text = str(value or "").strip().lstrip("-")
    if text.startswith("100") and len(text) >= 12:
        text = text[3:]
    return text if text.isdigit() else ""


def policy_key(group_name=None, entity=None) -> str:
    entity_id = numeric_group_id(getattr(entity, "id", None)) if entity is not None else ""
    supplied_id = numeric_group_id(group_name)
    if entity_id or supplied_id:
        return f"id:{entity_id or supplied_id}"
    return f"alias:{normalize_group(group_name)}"


def load_policies() -> dict:
    policies = deepcopy(SEEDED_POLICIES)
    for key, value in _load(POLICY_FILE).items():
        if isinstance(value, dict):
            policies[key] = {**policies.get(key, {}), **value}
    return policies


def resolve_group_policy(group_name=None, entity=None) -> tuple[str, dict]:
    policies = load_policies()
    key = policy_key(group_name, entity)
    selected = policies.get(key)
    if selected is None:
        aliases = {
            normalize_group(group_name),
            normalize_group(getattr(entity, "username", "") if entity is not None else ""),
        }
        for candidate_key, candidate in policies.items():
            candidate_aliases = {normalize_group(item) for item in candidate.get("aliases", [])}
            if aliases.intersection(candidate_aliases):
                selected = candidate
                break
    return key, {**deepcopy(DEFAULT_POLICY), **deepcopy(selected or {})}


def update_policy(group_name=None, entity=None, **changes) -> dict:
    key, current = resolve_group_policy(group_name, entity)
    stored = _load(POLICY_FILE)
    current.update({name: value for name, value in changes.items() if name in DEFAULT_POLICY})
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    stored[key] = current
    _atomic_json(POLICY_FILE, stored)
    return current


def account_is_held(policy: dict, brand: str) -> bool:
    held = policy.get("account_hold", [])
    if held is True:
        return True
    if isinstance(held, str):
        held = [held]
    return brand.lower() in {str(item).lower() for item in held}


def apply_telegram_rights(policy: dict, entity=None) -> dict:
    result = deepcopy(policy)
    rights = getattr(entity, "default_banned_rights", None)
    if rights is not None:
        if bool(getattr(rights, "embed_links", False)):
            result["allow_urls"] = False
            result["allow_deep_links"] = False
        if bool(getattr(rights, "send_media", False)):
            result["allow_media"] = False
    return result


def _remove_forbidden_product_lines(message: str, forbidden: list[str]) -> str:
    folded_forbidden = [unicodedata.normalize("NFKD", item).encode("ascii", "ignore").decode().lower() for item in forbidden]
    kept = []
    for line in message.splitlines():
        folded = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode().lower()
        if not any(term and term in folded for term in folded_forbidden):
            kept.append(line)
    return "\n".join(kept)


def make_policy_compliant(message: str, policy: dict, brand: str) -> tuple[str, dict]:
    """Return final Telegram text and send options after every experiment step."""
    text = _remove_forbidden_product_lines(message or "", policy.get("forbidden_products", []))
    no_links = not policy.get("allow_urls") or not policy.get("allow_deep_links")
    if no_links:
        # Remove both Markdown text URLs and bare links.  A visible @mention is
        # also an entity, so it is removed when mentions are disabled.
        text = re.sub(r"\[([^\]]+)\]\((?:https?://|tg://)[^)]+\)", r"\1", text)
        text = re.sub(r"(?i)(?:https?://|tg://|t\.me/)\S+", "", text)
        text = re.sub(r"(?i)\?start=[A-Za-z0-9_-]+", "", text)
    if not policy.get("allow_mentions"):
        text = re.sub(r"(?<!\w)@[A-Za-z0-9_]{4,}", "", text)
    if not policy.get("allow_emojis"):
        text = "".join(ch for ch in text if unicodedata.category(ch) not in {"So", "Sk", "Cs"})
    text = re.sub(r"[*_`~]", "", text) if no_links else text
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if no_links and brand.lower() == "keyvadi":
        # Remove any CTA fragments left by Markdown stripping and add the one
        # approved plain-text CTA.  It deliberately has no @ or URL entity.
        text = "\n".join(
            line for line in text.splitlines()
            if "hemen satın al" not in line.casefold() and "hemen satin al" not in line.casefold()
        ).strip()
        if PLAIN_KEYVADI_CTA not in text:
            text = f"{text}\n{PLAIN_KEYVADI_CTA}".strip()
    max_lines = policy.get("max_lines")
    if isinstance(max_lines, int) and max_lines > 0:
        text = "\n".join(text.splitlines()[:max_lines]).strip()
    return text, {
        "link_preview": False if no_links else None,
        "parse_mode": None if no_links else "md",
        "allow_media": bool(policy.get("allow_media")),
    }


WARNING_PATTERNS = (
    "izin verilmeyen link",
    "mesaj silindi",
    "sessize aldım",
    "sessize aldim",
    "spam göndericisi",
    "spam gondericisi",
    "yasaklı ürün",
    "yasakli urun",
)


def is_moderation_warning(text: str) -> bool:
    folded = (text or "").casefold()
    return any(pattern in folded for pattern in WARNING_PATTERNS)


def warning_targets_brand(text: str, brand: str) -> bool:
    folded = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower())
    markers = {
        "keyvadi": ("keyvadi", "keyvadionline"),
        "froxy": ("froxy", "froxyonline"),
        "lisansarena": ("lisansarena", "lisansarenaonline"),
    }
    return any(marker in folded for marker in markers.get(brand.lower(), (brand.lower(),)))


def record_delivery_state(group_name, account, status, *, entity=None, message_id=None, reason="") -> None:
    data = _load(MODERATION_FILE)
    key = policy_key(group_name, entity)
    data.setdefault(key, {})[account] = {
        "status": status,
        "message_id": message_id,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(MODERATION_FILE, data)


def record_moderation_hold(group_name, account, reason, *, entity=None, hours=24) -> None:
    data = _load(MODERATION_FILE)
    key = policy_key(group_name, entity)
    now = datetime.now(timezone.utc)
    data.setdefault(key, {})[account] = {
        "status": "moderation_deleted",
        "reason": reason,
        "hold_until": (now + timedelta(hours=hours)).isoformat(),
        "updated_at": now.isoformat(),
    }
    _atomic_json(MODERATION_FILE, data)


def moderation_hold_active(group_name, account, *, entity=None) -> bool:
    now = datetime.now(timezone.utc)
    data = _load(MODERATION_FILE)
    for key in {policy_key(group_name, entity), f"alias:{normalize_group(group_name)}"}:
        state = data.get(key, {}).get(account, {})
        try:
            if now < datetime.fromisoformat(state.get("hold_until", "")):
                return True
        except (TypeError, ValueError):
            continue
    return False


def moderation_snapshot() -> dict:
    return _load(MODERATION_FILE)
