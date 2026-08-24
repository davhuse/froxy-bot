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
PLAIN_FROXY_CTA = "Detaylar için Telegram aramasına FroxyDestekBOT yazabilirsiniz."
PLAIN_LISANSARENA_CTA = "LisansArena ürün ve teslimat bilgisi için Telegram aramasında LisansArenaBot yazabilirsiniz."
VISIBLE_KEYVADI_CTA = "Sipariş ve güncel fiyat: @KeyVadiSatisBot"
VISIBLE_FROXY_CTA = "Detay ve destek: @FroxyDestekBOT"
VISIBLE_LISANSARENA_CTA = "Sipariş ve destek: @LisansArenaBot"

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
    "smoke_required": False,
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
        "account_hold": [],
        "hold_reason": "Bağlantısız sade metin ve kontrollü smoke zorunlu.",
        "smoke_required": True,
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
    # KUPON-KOD SATIŞ GRUBU / @indirim363
    # 13 Ağustos 2026 canlı grup kaydında Darcy Güvenlik hem
    # @KeyVadiDestek hem de @Froxy_Ai mesajını silip hesapları "grup veya
    # kanal spamı" gerekçesiyle susturdu. Bu bir link biçimi sorunu olarak
    # varsayılmamalı; hesaplar yönetici incelemesi olmadan yeniden denenmez.
    "id:2846540634": {
        "aliases": ["indirim363"],
        "allow_urls": False,
        "allow_deep_links": False,
        "allow_mentions": False,
        "allow_media": False,
        "allow_emojis": False,
        "max_lines": None,
        "forbidden_products": [],
        "account_hold": [],
        "hold_reason": "Darcy uyarısı sonrası bağlantısız sade metin smoke zorunlu.",
        "smoke_required": True,
    },
    # Kullanıcı yeniden açılmasını onayladı; kimlik canlı çözümlemede kalıcı
    # Telegram ID'sine taşınır.
    "alias:kuponceking": {
        "aliases": ["kuponceking"],
        "allow_urls": False,
        "allow_deep_links": False,
        "allow_mentions": False,
        "allow_media": False,
        "allow_emojis": False,
        "max_lines": 18,
        "forbidden_products": [],
        "account_hold": [],
        "hold_reason": "Bağlantısız sade metin ve kontrollü smoke zorunlu.",
        "smoke_required": True,
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


def apply_brand_link_safety(policy: dict, brand: str) -> dict:
    """Apply brand-wide safety without overriding a group's own policy.

    Link restrictions are group-specific. Security warnings persist a strict
    policy for that Telegram group, while unaffected groups keep the measured
    CTA flow.
    """
    return deepcopy(policy)


def persistent_moderation_warning(group_name=None, *, entity=None) -> bool:
    """Keep historically warned groups on the safest CTA indefinitely."""
    data = _load(MODERATION_FILE)
    keys = {policy_key(group_name, entity), f"alias:{normalize_group(group_name)}"}
    warning_statuses = {"moderation_deleted", "moderation_warning", "security_warning"}
    warning_words = (
        "izin verilmeyen link", "mesaj silindi", "spam", "sessize",
        "yasaklı ürün", "yasakli urun",
    )
    for key in keys:
        for state in (data.get(key, {}) or {}).values():
            if not isinstance(state, dict):
                continue
            status = str(state.get("status", "")).casefold()
            reason = str(state.get("reason", "")).casefold()
            if status in warning_statuses or any(word in reason for word in warning_words):
                return True
    return False


def apply_persistent_moderation_safety(policy: dict, group_name=None, *, entity=None) -> dict:
    """Disable mention/link CTAs for groups with prior moderation evidence."""
    result = deepcopy(policy)
    if persistent_moderation_warning(group_name, entity=entity):
        result.update({
            "allow_urls": False,
            "allow_deep_links": False,
            "allow_mentions": False,
        })
    return result


def visible_mention_allowed(policy: dict) -> bool:
    """Whether a plain @bot CTA is safe for the current group policy."""
    return all(bool(policy.get(name)) for name in (
        "allow_urls", "allow_deep_links", "allow_mentions",
    )) and not policy.get("smoke_required") and not policy.get("account_hold")


def _brand_cta(brand: str, *, visible: bool) -> str:
    ctas = {
        "keyvadi": VISIBLE_KEYVADI_CTA if visible else PLAIN_KEYVADI_CTA,
        "froxy": VISIBLE_FROXY_CTA if visible else PLAIN_FROXY_CTA,
        "lisansarena": VISIBLE_LISANSARENA_CTA if visible else PLAIN_LISANSARENA_CTA,
    }
    return ctas.get(brand.casefold(), "")


def _remove_brand_cta_lines(text: str, brand: str) -> str:
    """Remove old CTA lines before adding exactly one policy-approved CTA."""
    terms = {
        "keyvadi": ("keyvadisatisbot", "sipariş adresi", "siparis adresi", "telegram aramas"),
        "froxy": ("froxydestekbot", "froxy_destek", "detaylar için", "detaylar icin", "telegram aramas"),
        "lisansarena": ("lisansarenabot", "sipariş ve destek", "siparis ve destek", "stok, teslimat", "ürünü yaz", "urunu yaz", "telegram aramas"),
    }.get(brand.casefold(), ())
    return "\n".join(
        line for line in text.splitlines()
        if not any(term in line.casefold() for term in terms)
    ).strip()


def _remove_forbidden_product_lines(message: str, forbidden: list[str]) -> str:
    folded_forbidden = [unicodedata.normalize("NFKD", item).encode("ascii", "ignore").decode().lower() for item in forbidden]
    kept = []
    for line in message.splitlines():
        folded = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode().lower()
        if not any(term and term in folded for term in folded_forbidden):
            kept.append(line)
    return "\n".join(kept)


def make_policy_compliant(message: str, policy: dict, brand: str) -> tuple[str, dict]:
    """Return final entity-free Telegram text and the policy CTA mode."""
    text = _remove_forbidden_product_lines(message or "", policy.get("forbidden_products", []))
    # All outbound ads use raw text. This removes legacy deep-links and any
    # TextUrl/Markdown syntax before the visible CTA is added.
    text = re.sub(r"\[([^\]]+)\]\((?:https?://|tg://)[^)]+\)", r"\1", text)
    text = re.sub(r"(?i)(?:https?://|tg://|t\.me/)\S+", "", text)
    text = re.sub(r"(?i)\?start=[A-Za-z0-9_-]+", "", text)
    text = re.sub(r"[*_`~]", "", text)
    if not policy.get("allow_mentions"):
        text = re.sub(r"(?<!\w)@[A-Za-z0-9_]{4,}", "", text)
    if not policy.get("allow_emojis"):
        text = "".join(ch for ch in text if unicodedata.category(ch) not in {"So", "Sk", "Cs"})
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()

    visible = visible_mention_allowed(policy)
    text = _remove_brand_cta_lines(text, brand)
    required_cta = _brand_cta(brand, visible=visible)
    if required_cta and required_cta not in text:
        text = f"{text}\n{required_cta}".strip()

    max_lines = policy.get("max_lines")
    if isinstance(max_lines, int) and max_lines > 0:
        lines = text.splitlines()
        if required_cta and required_cta in lines and len(lines) > max_lines:
            lines = [line for line in lines if line != required_cta]
            lines = lines[:max_lines - 1] + [required_cta]
        else:
            lines = lines[:max_lines]
        text = "\n".join(lines).strip()
    return text, {
        "link_preview": False,
        "parse_mode": None,
        "allow_media": bool(policy.get("allow_media")),
        "cta_mode": "plain_mention" if visible else "policy_plain_text",
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
    "grup veya kanal spamı gönderdi",
    "grup veya kanal spami gonderdi",
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
    previous = data.setdefault(key, {}).get(account, {})
    state = {
        **previous,
        "status": status,
        "message_id": message_id,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if status == "policy_smoke_sent":
        state["smoke_started_at"] = state["updated_at"]
        state.pop("smoke_passed_at", None)
    elif status == "visible_10m" and previous.get("smoke_started_at"):
        state["smoke_passed_at"] = state["updated_at"]
    data[key][account] = state
    _atomic_json(MODERATION_FILE, data)


def record_moderation_hold(group_name, account, reason, *, entity=None, hours=None) -> None:
    data = _load(MODERATION_FILE)
    key = policy_key(group_name, entity)
    now = datetime.now(timezone.utc)
    previous = data.setdefault(key, {}).get(account, {})
    attempts = int(previous.get("moderation_attempt_count", 0) or 0) + 1
    hold_hours = hours if hours is not None else (1 if attempts == 1 else 6 if attempts == 2 else 24)
    data.setdefault(key, {})[account] = {
        "status": "moderation_deleted",
        "reason": reason,
        "hold_until": (now + timedelta(hours=hold_hours)).isoformat(),
        "moderation_attempt_count": attempts,
        "updated_at": now.isoformat(),
    }
    _atomic_json(MODERATION_FILE, data)


def policy_smoke_pending(group_name, account, policy, *, entity=None) -> bool:
    if not policy.get("smoke_required"):
        return False
    data = _load(MODERATION_FILE)
    account_state = data.get(policy_key(group_name, entity), {}).get(account, {})
    return not bool(account_state.get("smoke_passed_at"))


def policy_smoke_available(group_name, account, *, entity=None, window_minutes=15) -> bool:
    """Serialize smoke attempts for different accounts in the same group."""
    now = datetime.now(timezone.utc)
    states = _load(MODERATION_FILE).get(policy_key(group_name, entity), {})
    for other_account, state in states.items():
        if other_account == account or not isinstance(state, dict):
            continue
        started = state.get("smoke_started_at")
        if not started or state.get("smoke_passed_at"):
            continue
        try:
            if now - datetime.fromisoformat(started) < timedelta(minutes=window_minutes):
                return False
        except (TypeError, ValueError):
            continue
    return True


def visibility_check_pending(group_name, *, entity=None, window_minutes=15) -> bool:
    """Prevent another account sending before a prior advert is confirmed."""
    now = datetime.now(timezone.utc)
    states = _load(MODERATION_FILE).get(policy_key(group_name, entity), {})
    for state in states.values():
        if not isinstance(state, dict) or state.get("status") not in {
            "policy_smoke_sent", "telegram_accepted", "visible"
        }:
            continue
        updated = state.get("updated_at")
        try:
            if updated and now - datetime.fromisoformat(updated) < timedelta(minutes=window_minutes):
                return True
        except (TypeError, ValueError):
            continue
    return False


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
