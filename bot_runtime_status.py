"""Shared, non-secret runtime readiness state for Telegram sales bots."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
VALID_BRANDS = {"keyvadi", "froxy", "lisansarena", "jarvis"}


def token_fingerprint(token: str) -> str:
    """Identify a token without ever persisting the credential itself."""
    value = (token or "").strip()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] if value else ""


def _safe_brand(brand: str) -> str:
    value = str(brand or "").strip().lower()
    if value not in VALID_BRANDS:
        raise ValueError(f"Unknown bot brand: {brand}")
    return value


def status_path(brand: str) -> Path:
    return BASE_DIR / f"sales_bot_status_{_safe_brand(brand)}.json"


def read_bot_status(brand: str) -> dict[str, Any]:
    try:
        value = json.loads(status_path(brand).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def write_bot_status(
    brand: str,
    *,
    state: str,
    telegram_ready: bool,
    token: str = "",
    last_error: str | None = None,
    bot_username: str | None = None,
    connected: bool = False,
) -> dict[str, Any]:
    """Atomically publish readiness without exposing token material."""
    key = _safe_brand(brand)
    previous = read_bot_status(key)
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "brand": key,
        "pid": os.getpid(),
        "state": str(state),
        "telegram_ready": bool(telegram_ready),
        "last_error": str(last_error)[:300] if last_error else None,
        "bot_username": bot_username or previous.get("bot_username"),
        "token_fingerprint": token_fingerprint(token),
        "updated_at": now,
        "last_connected_at": now if connected else previous.get("last_connected_at"),
    }
    target = status_path(key)
    fd, temp_name = tempfile.mkstemp(
        prefix=f"{target.stem}-", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        try:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        except OSError:
            pass
    return payload


def invalid_token_error(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return (
        name in {"accesstokenexpirederror", "accesstokeninvaliderror"}
        or "bot token expired" in message
        or "access token is invalid" in message
        or "invalid bot token" in message
    )


def restart_blocked_for_token(brand: str, token: str) -> bool:
    status = read_bot_status(brand)
    return (
        status.get("state") == "invalid_token"
        and status.get("token_fingerprint") == token_fingerprint(token)
    )
