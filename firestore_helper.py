"""Small Firestore REST client used by the Telegram workers.

Production authentication prefers a Google service-account JSON supplied via
``FIREBASE_SERVICE_ACCOUNT_JSON``.  ``FIREBASE_API_KEY`` remains as a temporary
compatibility path while the existing Firebase project is migrated; no key is
kept in source control.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "bot-2-63772").strip()
API_KEY = os.environ.get("FIREBASE_API_KEY", "").strip()
BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/"
    "databases/(default)/documents/reklam"
)
COMMIT_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/"
    "databases/(default)/documents:commit"
)
DOCUMENT_PREFIX = (
    f"projects/{PROJECT_ID}/databases/(default)/documents/reklam"
)

_TOKEN_LOCK = threading.Lock()
_GOOGLE_CREDENTIALS = None
_LOCAL_LOCK = threading.Lock()


def _local_db_path():
    return os.environ.get("RUNTIME_CLAIM_DB", "runtime_claims.db").strip() or "runtime_claims.db"


def _local_connect():
    connection = sqlite3.connect(_local_db_path(), timeout=10)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS runtime_claims ("
        "doc_id TEXT PRIMARY KEY, fields TEXT NOT NULL, updated_at REAL NOT NULL)"
    )
    return connection


def _local_get(doc_id):
    try:
        with _LOCAL_LOCK:
            connection = _local_connect()
            row = connection.execute(
                "SELECT fields FROM runtime_claims WHERE doc_id = ?", (doc_id,)
            ).fetchone()
            connection.close()
        return json.loads(row[0]) if row else None
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return None


def _local_claim(doc_id, fields_dict):
    try:
        with _LOCAL_LOCK:
            connection = _local_connect()
            cursor = connection.execute(
                "INSERT OR IGNORE INTO runtime_claims(doc_id, fields, updated_at) VALUES (?, ?, ?)",
                (doc_id, json.dumps(fields_dict or {}, ensure_ascii=False), time.time()),
            )
            connection.commit()
            connection.close()
            return cursor.rowcount == 1
    except (OSError, sqlite3.Error, TypeError):
        return None


def _local_set(doc_id, fields_dict):
    try:
        with _LOCAL_LOCK:
            connection = _local_connect()
            connection.execute(
                "INSERT INTO runtime_claims(doc_id, fields, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(doc_id) DO UPDATE SET fields=excluded.fields, updated_at=excluded.updated_at",
                (doc_id, json.dumps(fields_dict or {}, ensure_ascii=False), time.time()),
            )
            connection.commit()
            connection.close()
        return True
    except (OSError, sqlite3.Error, TypeError):
        return False


def _local_delete(doc_id):
    try:
        with _LOCAL_LOCK:
            connection = _local_connect()
            connection.execute("DELETE FROM runtime_claims WHERE doc_id = ?", (doc_id,))
            connection.commit()
            connection.close()
        return True
    except (OSError, sqlite3.Error):
        return False


def _service_account_credentials():
    global _GOOGLE_CREDENTIALS
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    with _TOKEN_LOCK:
        if _GOOGLE_CREDENTIALS is None:
            from google.oauth2 import service_account

            info = json.loads(raw)
            _GOOGLE_CREDENTIALS = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/datastore"],
            )
        return _GOOGLE_CREDENTIALS


def _auth_headers():
    credentials = _service_account_credentials()
    if credentials is None:
        if not API_KEY:
            raise RuntimeError(
                "Firestore credentials missing: set FIREBASE_SERVICE_ACCOUNT_JSON "
                "or the temporary FIREBASE_API_KEY compatibility variable."
            )
        return {}

    from google.auth.transport.requests import Request

    with _TOKEN_LOCK:
        if not credentials.valid or credentials.expired:
            credentials.refresh(Request())
    return {"Authorization": f"Bearer {credentials.token}"}


def remote_credentials_configured():
    """Whether this process can use Firestore as a durable coordination store."""
    return bool(os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip() or API_KEY)


def _url(url):
    if _service_account_credentials() is not None:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}key={urllib.parse.quote(API_KEY)}"


def _value_to_firestore(value):
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if value is None:
        return {"nullValue": None}
    # Preserve the legacy storage format for lists/dicts so existing documents
    # and bot readers do not silently change shape during the security rollout.
    return {"stringValue": str(value)}


def _fields_to_firestore(fields_dict):
    return {key: _value_to_firestore(value) for key, value in fields_dict.items()}


def _value_from_firestore(value):
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return value["booleanValue"]
    if "nullValue" in value:
        return None
    return None


def _request(url, method="GET", payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(_url(url), data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in _auth_headers().items():
        req.add_header(key, value)
    return urllib.request.urlopen(req, timeout=timeout)


def get_document_with_meta(doc_id, quiet=False):
    try:
        with _request(f"{BASE_URL}/{urllib.parse.quote(doc_id)}") as response:
            data = json.loads(response.read().decode("utf-8"))
        fields = {
            key: _value_from_firestore(value)
            for key, value in data.get("fields", {}).items()
        }
        return fields, data.get("updateTime")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, None
        if not quiet:
            print(f"Firestore read error for doc {doc_id}: HTTP {exc.code}")
        return None, None
    except Exception as exc:
        if not quiet:
            print(f"Firestore read error for doc {doc_id}: {type(exc).__name__}")
        return None, None


def get_document(doc_id):
    fields, _ = get_document_with_meta(doc_id)
    return fields if fields is not None else _local_get(doc_id)


def set_document(doc_id, fields_dict):
    try:
        with _request(
            f"{BASE_URL}/{urllib.parse.quote(doc_id)}",
            method="PATCH",
            payload={"fields": _fields_to_firestore(fields_dict)},
        ) as response:
            ok = response.status in (200, 201)
            if ok:
                _local_set(doc_id, fields_dict)
            return ok
    except Exception as exc:
        print(f"Firestore save error for doc {doc_id}: {type(exc).__name__}")
        return _local_set(doc_id, fields_dict)


def _commit(write, quiet=False):
    try:
        with _request(COMMIT_URL, method="POST", payload={"writes": [write]}) as response:
            return response.status in (200, 201)
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 409):
            return False
        if not quiet:
            print(f"Firestore conditional write error: HTTP {exc.code}")
        return None
    except Exception as exc:
        if not quiet:
            print(f"Firestore conditional write error: {type(exc).__name__}")
        return None


def claim_document(doc_id, fields_dict=None, quiet=False):
    """Atomically create a document; False means another worker claimed it."""
    # Keep a local create-only mirror. It prevents duplicates during a
    # Firestore outage and also stops a recovered Firestore instance from
    # creating a second claim for a key already reserved locally.
    if _local_get(doc_id) is not None:
        return False
    result = _commit({
        "update": {
            "name": f"{DOCUMENT_PREFIX}/{doc_id}",
            "fields": _fields_to_firestore(fields_dict or {}),
        },
        "currentDocument": {"exists": False},
    }, quiet=quiet)
    if result is True:
        _local_set(doc_id, fields_dict or {})
        return True
    if result is None:
        return _local_claim(doc_id, fields_dict or {})
    return result


def claim_remote_document(doc_id, fields_dict=None, quiet=False):
    """Atomically claim a document without falling back to ephemeral disk.

    Customer-facing replies and distributed blast sends must not silently use
    Render's temporary filesystem.  ``None`` means the durable backend is not
    configured or unavailable; callers should fail closed in that case.
    """
    if not remote_credentials_configured():
        return None
    return _commit({
        "update": {
            "name": f"{DOCUMENT_PREFIX}/{doc_id}",
            "fields": _fields_to_firestore(fields_dict or {}),
        },
        "currentDocument": {"exists": False},
    }, quiet=quiet)


def health_check():
    """Return a non-secret Firestore connectivity/configuration summary."""
    if not remote_credentials_configured():
        return {"configured": False, "reachable": False, "status": "missing_credentials"}
    try:
        # Do not probe with a synthetic document ID: Firestore reserves IDs
        # beginning and ending with double underscores (for example
        # ``__codex_health__``) and answers with INVALID_ARGUMENT.  Listing a
        # single document from the existing collection proves the same API,
        # project and credentials are reachable without mutating data.
        url = f"{BASE_URL}?pageSize=1"
        with _request(url) as response:
            response.read(1)
        return {"configured": True, "reachable": True, "status": "ready"}
    except urllib.error.HTTPError as exc:
        # A missing document still proves that the project/API key is reachable.
        if exc.code == 404:
            return {"configured": True, "reachable": True, "status": "ready"}
        return {"configured": True, "reachable": False, "status": f"http_{exc.code}"}
    except Exception as exc:
        return {"configured": True, "reachable": False, "status": type(exc).__name__}


def compare_and_set_document(doc_id, fields_dict, update_time, quiet=False):
    if not update_time:
        return False
    return _commit({
        "update": {
            "name": f"{DOCUMENT_PREFIX}/{doc_id}",
            "fields": _fields_to_firestore(fields_dict),
        },
        "currentDocument": {"updateTime": update_time},
    }, quiet=quiet)


def delete_document(doc_id, update_time=None):
    write = {"delete": f"{DOCUMENT_PREFIX}/{doc_id}"}
    if update_time:
        write["currentDocument"] = {"updateTime": update_time}
        result = _commit(write)
        _local_delete(doc_id)
        return result
    try:
        with _request(
            f"{BASE_URL}/{urllib.parse.quote(doc_id)}", method="DELETE"
        ) as response:
            _local_delete(doc_id)
            return response.status in (200, 204)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return True
        print(f"Firestore delete error for doc {doc_id}: HTTP {exc.code}")
        return _local_delete(doc_id)
    except Exception as exc:
        print(f"Firestore delete error for doc {doc_id}: {type(exc).__name__}")
        return _local_delete(doc_id)


def delete_remote_document(doc_id):
    """Delete a durable coordination claim without touching local fallback state."""
    if not remote_credentials_configured():
        return False
    try:
        with _request(
            f"{BASE_URL}/{urllib.parse.quote(doc_id)}", method="DELETE"
        ) as response:
            return response.status in (200, 204)
    except urllib.error.HTTPError as exc:
        return exc.code == 404
    except Exception:
        return False
def acquire_lease(doc_id, owner_id, ttl_seconds=120):
    """Acquire or renew an expiring single-owner lease with Firestore CAS."""
    now = int(time.time())
    fields, update_time = get_document_with_meta(doc_id)
    new_fields = {
        "owner_id": owner_id,
        "heartbeat_at": now,
        "expires_at": now + int(ttl_seconds),
    }
    if fields is None:
        # Firestore can be temporarily unavailable while the running Render
        # instance still owns the local fallback lease. Renew that local copy
        # instead of stopping the Telegram worker every heartbeat interval.
        local_fields = _local_get(doc_id)
        if local_fields is not None:
            local_owner = str(local_fields.get("owner_id", ""))
            local_expires_at = int(local_fields.get("expires_at", 0) or 0)
            if local_owner != owner_id and local_expires_at > now:
                return False
            return _local_set(doc_id, new_fields)
        return claim_document(doc_id, new_fields)
    current_owner = str(fields.get("owner_id", ""))
    expires_at = int(fields.get("expires_at", 0) or 0)
    if current_owner != owner_id and expires_at > now:
        return False
    return compare_and_set_document(doc_id, new_fields, update_time)


def release_lease(doc_id, owner_id):
    fields, update_time = get_document_with_meta(doc_id)
    if fields is None:
        return True
    if str(fields.get("owner_id", "")) != str(owner_id):
        return False
    return delete_document(doc_id, update_time=update_time)
