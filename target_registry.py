"""Shared discovery candidates and approved Telegram advertising targets.

The main publisher is the only writer for discovery/approval metadata.  All
publishers may read the approved target set.  Firestore is the durable source
on Render; a JSON file keeps local development and temporary outages usable.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

import requests


REGISTRY_FILE = Path(__file__).resolve().with_name("group_target_registry.json")
REGISTRY_DOCUMENT = "reklam/target_registry"
_LOCK = threading.RLock()

PRODUCT_TERMS = (
    "kupon", "kod", "çek", "cek", "indirim", "promosyon", "hediye çeki",
    "dijital ürün", "premium hesap", "lisans", "epin", "oyun kodu",
)
INTENT_TERMS = (
    "satış", "satis", "alım satım", "alim satim", "ilan", "pazar",
    "ticaret", "takas",
)
MARKET_TERMS = ("grup", "grubu", "merkezi", "pazarı", "pazari", "platformu")
NEGATIVE_TERMS = (
    "bahis", "casino", "kumar", "kripto", "airdrop", "referans kasma",
    "sigara", "puff", "escort", "ifşa", "ifsa", "porno",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_group(value: object) -> str:
    text = str(value or "").strip().lower().lstrip("@")
    text = re.sub(r"^https?://(?:t|telegram)\.me/", "", text)
    return text.split("?", 1)[0].strip("/")


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char)).replace("ı", "i")


def generate_discovery_queries(configured=None, limit: int = 120) -> list[str]:
    """Build bounded, deterministic search queries from config and core families."""
    result: list[str] = []
    seen: set[str] = set()

    def add(value: object) -> None:
        query = re.sub(r"\s+", " ", str(value or "").strip())
        key = _fold(query)
        if query and key not in seen and len(result) < max(1, int(limit)):
            seen.add(key)
            result.append(query)

    configured_cap = max(1, int(max(1, limit) * 0.7))
    for query in configured or ():
        add(query)
        if len(result) >= configured_cap:
            break
    for product in PRODUCT_TERMS:
        for intent in INTENT_TERMS[:5]:
            add(f"{product} {intent}")
            if len(result) >= limit:
                return result
    for product in PRODUCT_TERMS[:7]:
        for market in MARKET_TERMS:
            add(f"{product} {market}")
            if len(result) >= limit:
                return result
    return result


def closest_targets(username: str, title: str, existing_targets, limit: int = 3) -> list[str]:
    candidate = _fold(f"{username} {title}").replace("_", " ")
    ranked = []
    for target in existing_targets or ():
        normalized = normalize_group(target)
        ratio = SequenceMatcher(None, candidate, _fold(normalized).replace("_", " ")).ratio()
        if ratio >= 0.32:
            ranked.append((ratio, normalized))
    ranked.sort(reverse=True)
    return [name for _ratio, name in ranked[:limit]]


def score_candidate(*, username: str, title: str, members: int = 0,
                    days_inactive: int = 999, unique_senders: int = 0,
                    join_request: bool = False, write_forbidden: bool = False,
                    existing_targets=()) -> dict:
    """Return an explainable relevance/quality score for a public group."""
    searchable = _fold(f"{username} {title}")
    product_hits = sorted({term for term in PRODUCT_TERMS if _fold(term) in searchable})
    intent_hits = sorted({term for term in INTENT_TERMS if _fold(term) in searchable})
    negatives = sorted({term for term in NEGATIVE_TERMS if _fold(term) in searchable})
    score = min(35, len(product_hits) * 12) + min(20, len(intent_hits) * 10)
    reasons = []
    if product_hits:
        reasons.append("ürün: " + ", ".join(product_hits[:3]))
    if intent_hits:
        reasons.append("niyet: " + ", ".join(intent_hits[:2]))
    if members >= 5000:
        score += 18
        reasons.append(f"{members} üye")
    elif members >= 1000:
        score += 13
        reasons.append(f"{members} üye")
    elif members >= 500:
        score += 8
        reasons.append(f"{members} üye")
    if days_inactive <= 1:
        score += 15
        reasons.append("son 24 saatte aktif")
    elif days_inactive <= 4:
        score += 8
        reasons.append(f"{days_inactive} gün önce aktif")
    if unique_senders >= 5:
        score += 12
        reasons.append(f"{unique_senders} farklı gönderici")
    elif unique_senders >= 3:
        score += 6
    if join_request:
        score -= 5
        reasons.append("katılım onayı gerekiyor")
    if write_forbidden:
        score -= 30
        reasons.append("yazma kapalı görünüyor")
    if negatives:
        score -= 100
        reasons.append("uygunsuz: " + ", ".join(negatives[:3]))
    similar = closest_targets(username, title, existing_targets)
    if similar:
        score += min(8, len(similar) * 3)
        reasons.append("benzer: " + ", ".join("@" + item for item in similar))
    score = max(0, min(100, score))
    eligible = bool(product_hits and intent_hits and not negatives and members >= 150 and score >= 45)
    return {"score": score, "reasons": reasons, "similar_to": similar, "eligible": eligible}


def _empty_registry() -> dict:
    return {"version": 1, "updated_at": utc_now(), "candidates": {}, "batches": {}}


class TargetRegistry:
    def __init__(self, local_path: str | os.PathLike | None = None):
        self.local_path = Path(local_path) if local_path else REGISTRY_FILE
        project = os.environ.get("FIREBASE_PROJECT_ID", "bot-2-63772").strip()
        self.api_key = os.environ.get("FIREBASE_API_KEY", "").strip()
        self.base_url = (
            f"https://firestore.googleapis.com/v1/projects/{project}/"
            "databases/(default)/documents"
        )
        self._cached_data = None
        self._cached_at = 0.0

    def _load_local(self) -> dict:
        try:
            data = json.loads(self.local_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else _empty_registry()
        except (OSError, ValueError):
            return _empty_registry()

    def _save_local(self, data: dict) -> None:
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.local_path.with_name(
            f"{self.local_path.name}.{os.getpid()}.tmp"
        )
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.local_path)

    def _load_remote(self) -> dict | None:
        if not self.api_key:
            return None
        try:
            response = requests.get(
                f"{self.base_url}/{REGISTRY_DOCUMENT}?key={self.api_key}", timeout=10
            )
            if response.status_code != 200:
                return None
            raw = response.json().get("fields", {}).get("registry_json", {}).get("stringValue")
            data = json.loads(raw or "{}")
            return data if isinstance(data, dict) and data.get("version") else None
        except (requests.RequestException, ValueError):
            return None

    def load(self, prefer_remote: bool = True) -> dict:
        with _LOCK:
            if (self._cached_data is not None
                    and time.monotonic() - self._cached_at < 60):
                return json.loads(json.dumps(self._cached_data))
            data = self._load_remote() if prefer_remote else None
            if data is None:
                data = self._load_local()
            else:
                self._save_local(data)
            data.setdefault("candidates", {})
            data.setdefault("batches", {})
            self._cached_data = data
            self._cached_at = time.monotonic()
            return json.loads(json.dumps(data))

    def save(self, data: dict) -> bool:
        with _LOCK:
            data["version"] = 1
            data["updated_at"] = utc_now()
            self._save_local(data)
            self._cached_data = json.loads(json.dumps(data))
            self._cached_at = time.monotonic()
            if not self.api_key:
                return True
            payload = {"fields": {"registry_json": {"stringValue": json.dumps(data, ensure_ascii=False)}}}
            url = (
                f"{self.base_url}/{REGISTRY_DOCUMENT}?"
                f"updateMask.fieldPaths=registry_json&key={self.api_key}"
            )
            try:
                response = requests.patch(url, json=payload, timeout=10)
                if response.status_code == 404:
                    response = requests.post(
                        f"{self.base_url}/reklam?documentId=target_registry&key={self.api_key}",
                        json=payload, timeout=10,
                    )
                return response.status_code < 400
            except requests.RequestException:
                return False

    def approved_groups(self) -> set[str]:
        data = self.load()
        return {
            normalize_group(name)
            for name, row in data["candidates"].items()
            if isinstance(row, dict) and row.get("status") == "approved" and row.get("active", True)
        }

    def migrate_approved(self, groups, source: str = "legacy_auto_groups") -> int:
        data = self.load()
        changed = 0
        for value in groups or ():
            username = normalize_group(value)
            if not username:
                continue
            row = data["candidates"].setdefault(username, {})
            if row.get("status") != "approved":
                changed += 1
            row.update({
                "username": username, "status": "approved", "active": True,
                "approved_at": row.get("approved_at") or utc_now(),
                "sources": sorted(set(row.get("sources", [])) | {source}),
            })
        if changed:
            self.save(data)
        return changed

    def register_candidate(self, candidate: dict) -> tuple[dict, bool]:
        data = self.load()
        username = normalize_group(candidate.get("username"))
        if not username:
            raise ValueError("candidate username is required")
        current = data["candidates"].get(username)
        if isinstance(current, dict) and current.get("status") in {"pending", "approved", "rejected"}:
            merged_sources = sorted(
                set(current.get("sources") or []) | set(candidate.get("sources") or [])
            )
            if merged_sources != current.get("sources"):
                current["sources"] = merged_sources
                current["last_seen_at"] = utc_now()
                data["candidates"][username] = current
                self.save(data)
            return current, False
        row = {
            **candidate,
            "username": username,
            "status": "pending",
            "active": True,
            "discovered_at": candidate.get("discovered_at") or utc_now(),
        }
        row["sources"] = sorted(set(row.get("sources") or ["telegram_search"]))
        data["candidates"][username] = row
        self.save(data)
        return row, True

    def create_batch(self, usernames, discovered_by: str) -> tuple[str, list[dict]]:
        data = self.load()
        rows = []
        for username in usernames:
            row = data["candidates"].get(normalize_group(username))
            if isinstance(row, dict) and row.get("status") == "pending":
                rows.append(row)
        batch_id = datetime.now(timezone.utc).strftime("%m%d%H%M") + uuid4().hex[:4]
        data["batches"][batch_id] = {
            "id": batch_id, "created_at": utc_now(), "discovered_by": discovered_by,
            "usernames": [row["username"] for row in rows], "status": "pending",
        }
        self.save(data)
        return batch_id, rows

    def apply_batch_decision(self, batch_id: str, indexes, decision: str,
                             decided_by: object) -> list[dict]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        data = self.load()
        batch = data["batches"].get(str(batch_id))
        if not isinstance(batch, dict):
            raise KeyError(batch_id)
        changed = []
        usernames = batch.get("usernames", [])
        for index in sorted(set(int(item) for item in indexes)):
            if index < 1 or index > len(usernames):
                continue
            row = data["candidates"].get(usernames[index - 1])
            if not isinstance(row, dict) or row.get("status") != "pending":
                continue
            row["status"] = decision
            row["decided_at"] = utc_now()
            row["decided_by"] = str(decided_by)
            changed.append(row)
        remaining = [
            name for name in usernames
            if data["candidates"].get(name, {}).get("status") == "pending"
        ]
        batch["status"] = "pending" if remaining else "completed"
        batch["updated_at"] = utc_now()
        self.save(data)
        return changed


def format_candidate_batch(batch_id: str, rows: list[dict]) -> str:
    lines = [f"🔎 **Yeni Grup Adayları — Batch `{batch_id}`**", ""]
    for index, row in enumerate(rows, 1):
        reasons = "; ".join(row.get("reasons") or []) or "uygun hedef benzerliği"
        lines.append(
            f"**{index}.** @{row['username']} — {int(row.get('members') or 0)} üye — "
            f"{int(row.get('score') or 0)}/100\n_{reasons[:220]}_"
        )
    lines.extend([
        "", "Bu mesaja yanıt verin:",
        "`onay 1,3,5`", "`reddet 2,4`",
        "Onaylananlar Froxy, KeyVadi, LisansArena ve SosyalPazarSMM için ortak hedef olur.",
    ])
    return "\n".join(lines)
