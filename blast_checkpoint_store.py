"""Independent durable mirror for the group-ad checkpoint.

Render's service filesystem is replaced on deploy. Firestore can be quota-
limited, so the existing store database provides a second recovery copy.
This table contains only the blast checkpoint, not customer store records.
"""

from __future__ import annotations

import json
import os
import threading

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from lisansarena_store import normalize_database_url


_LOCK = threading.Lock()
_ENGINE = None
_ENGINE_URL = None


def _database_url():
    return (
        os.environ.get("BLAST_CHECKPOINT_DATABASE_URL")
        or os.environ.get("LISANSARENA_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()


def _engine():
    global _ENGINE, _ENGINE_URL
    raw_url = _database_url()
    if not raw_url:
        return None
    normalized = normalize_database_url(raw_url)
    if (
        make_url(normalized).get_backend_name() != "postgresql"
        and not os.environ.get("BLAST_CHECKPOINT_DATABASE_URL")
    ):
        # A Render-local SQLite database vanishes with the service instance.
        return None
    with _LOCK:
        if _ENGINE is not None and _ENGINE_URL == raw_url:
            return _ENGINE
        candidate = create_engine(normalized, pool_pre_ping=True, future=True)
        with candidate.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS blast_checkpoint_backup ("
                "id INTEGER PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)"
            ))
        _ENGINE = candidate
        _ENGINE_URL = raw_url
        return _ENGINE


def load_checkpoint():
    try:
        engine = _engine()
        if engine is None:
            return None
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT payload FROM blast_checkpoint_backup WHERE id = 1"
            )).first()
        value = json.loads(row[0]) if row else None
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def save_checkpoint(state):
    try:
        engine = _engine()
        if engine is None:
            return False
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO blast_checkpoint_backup (id, payload, updated_at) "
                "VALUES (1, :payload, :updated_at) "
                "ON CONFLICT (id) DO UPDATE SET "
                "payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at"
            ), {
                "payload": json.dumps(state, ensure_ascii=False),
                "updated_at": str(state.get("updated_at") or ""),
            })
        return True
    except Exception:
        return False


def health_check():
    """Report backup connectivity without exposing the database URL."""
    if not _database_url():
        return {"configured": False, "reachable": False, "status": "missing_database"}
    try:
        engine = _engine()
        if engine is None:
            return {
                "configured": True,
                "reachable": False,
                "status": "local_database_not_durable",
            }
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT updated_at FROM blast_checkpoint_backup WHERE id = 1"
            )).first()
        return {
            "configured": True,
            "reachable": True,
            "status": "ready",
            "has_checkpoint": row is not None,
            "updated_at": row[0] if row else None,
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "status": type(exc).__name__,
        }
