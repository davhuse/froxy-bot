"""Durable product and stock announcement delivery shared by all sales bots.

The queue is mirrored to Firestore when configured and kept in a local JSON
fallback.  Messages are sent only to users who have interacted with the
corresponding bot; group blast delivery is deliberately out of scope here.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
from typing import Awaitable, Callable

import firestore_helper


ROOT = Path(__file__).resolve().parent
BRANDS = ("keyvadi", "froxy", "lisansarena")
BRAND_CONFIG = {
    "keyvadi": {
        "token_vars": ("KEYVADI_SUPPORT_BOT_TOKEN", "KEYVADI_BOT_TOKEN"),
        "user_doc": "keyvadi_users_data",
        "local_users": ROOT / "miniapp" / "users_data.json",
    },
    "froxy": {
        "token_vars": ("FROXY_SUPPORT_BOT_TOKEN", "FROXY_BOT_TOKEN"),
        "user_doc": "froxy_users_data",
        "local_users": ROOT / "miniapp_froxy" / "users_data.json",
    },
    "lisansarena": {
        "token_vars": ("LISANSARENA_SUPPORT_BOT_TOKEN", "LISANSARENA_BOT_TOKEN"),
        "user_doc": "lisansarena_users_data",
        "local_users": ROOT / "miniapp_lisansarena" / "users_data.json",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_brand(brand: str) -> str:
    value = str(brand or "").strip().casefold()
    if value not in BRANDS:
        raise ValueError(f"Bilinmeyen bot markası: {brand}")
    return value


def load_subscribers(brand: str) -> list[int]:
    """Merge local and Firestore users, returning valid Telegram IDs only."""
    brand = normalize_brand(brand)
    cfg = BRAND_CONFIG[brand]
    ids: set[int] = set()
    path = cfg["local_users"]
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if isinstance(data, dict):
            for uid in data.keys():
                if str(uid).isdigit():
                    ids.add(int(uid))
    except Exception:
        pass
    try:
        doc = firestore_helper.get_document(cfg["user_doc"]) or {}
        users = doc.get("users", {}) if isinstance(doc, dict) else {}
        if isinstance(users, dict):
            for uid in users.keys():
                if str(uid).isdigit():
                    ids.add(int(uid))
    except Exception:
        pass
    return sorted(ids)


def bot_token(brand: str) -> str:
    brand = normalize_brand(brand)
    for key in BRAND_CONFIG[brand]["token_vars"]:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        config = json.loads((ROOT / "bot_config.json").read_text(encoding="utf-8"))
    except Exception:
        config = {}
    fallback_keys = {
        "keyvadi": ("keyvadi_bot_token", "support_bot_token"),
        "froxy": ("froxy_bot_token",),
        "lisansarena": ("lisansarena_bot_token",),
    }[brand]
    for key in fallback_keys:
        value = str(config.get(key, "")).strip()
        if value and value != "YOUR_TELEGRAM_BOT_TOKEN":
            return value
    return ""


def _safe_key(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:24]


class AnnouncementQueue:
    """A small per-brand durable queue with idempotency keys."""

    def __init__(self, brand: str, kind: str):
        self.brand = normalize_brand(brand)
        self.kind = str(kind or "general").strip().lower()
        self.doc_id = f"announcement_queue_{self.kind}_{self.brand}"
        self.path = ROOT / f"{self.doc_id}.json"
        self._lock = threading.RLock()

    def _read(self) -> dict:
        try:
            doc = firestore_helper.get_document(self.doc_id) or {}
            if isinstance(doc, dict) and isinstance(doc.get("items"), list):
                return {"items": deepcopy(doc["items"])}
        except Exception:
            pass
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("items"), list):
                return value
        except Exception:
            pass
        return {"items": []}

    def _write(self, state: dict) -> None:
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            firestore_helper.set_document(self.doc_id, state)
        except Exception:
            pass

    def items(self) -> list[dict]:
        with self._lock:
            return deepcopy(self._read().get("items", []))

    def enqueue(self, item: dict) -> tuple[dict, bool]:
        with self._lock:
            state = self._read()
            key = str(item.get("idempotency_key") or "").strip()
            if not key:
                raise ValueError("announcement idempotency_key is required")
            for existing in state["items"]:
                if existing.get("idempotency_key") == key:
                    return deepcopy(existing), False
            normalized = {
                **item,
                "id": item.get("id") or _safe_key(key),
                "status": "pending",
                "next_index": 0,
                "sent_ids": [],
                "failed_ids": [],
                "created_at": item.get("created_at") or utc_now(),
                "updated_at": utc_now(),
            }
            state["items"].append(normalized)
            self._write(state)
            return deepcopy(normalized), True

    def update(self, item_id: str, **changes) -> dict | None:
        with self._lock:
            state = self._read()
            for item in state["items"]:
                if str(item.get("id")) != str(item_id):
                    continue
                item.update(changes)
                item["updated_at"] = utc_now()
                self._write(state)
                return deepcopy(item)
        return None

    def pending(self) -> list[dict]:
        now = time.time()
        result = []
        for item in self.items():
            status = item.get("status")
            stale = status == "sending" and now - _epoch(item.get("updated_at")) > 600
            if status == "pending" or stale:
                result.append(item)
        return result


def _epoch(value) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def parse_stock_command(text: str) -> tuple[str, int, str | None] | None:
    """Parse `/stok product name COUNT [PRICE]` without breaking numeric titles."""
    raw = str(text or "").strip()
    raw = raw.split(maxsplit=1)[1].strip() if raw.lower().startswith("/stok") and len(raw.split()) > 1 else ""
    if not raw:
        return None
    tokens = raw.split()
    if not tokens:
        return None

    def number(value: str) -> bool:
        cleaned = value.replace(",", ".").replace("₺", "").strip()
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    price = None
    if len(tokens) >= 3 and number(tokens[-1]) and tokens[-2].isdigit():
        price = tokens[-1]
        count_token = tokens[-2]
        query_tokens = tokens[:-2]
    elif tokens[-1].isdigit():
        count_token = tokens[-1]
        query_tokens = tokens[:-1]
    else:
        return None
    if not query_tokens:
        return None
    count = int(count_token)
    if count < 0:
        return None
    return " ".join(query_tokens).strip(), count, price


def match_stock_product(brand: str, query: str) -> tuple[dict | None, list[dict]]:
    from sales_conversion import load_sales_catalog, match_sales_products

    products = load_sales_catalog(normalize_brand(brand))
    matches = match_sales_products(query, products, limit=4)
    return (matches[0] if matches else None), matches


def stock_card_text(title: str, count: int, price: str | None) -> str:
    shown_price = str(price or "Fiyat mağazada güncel").strip()
    if count == 0:
        return (
            "⛔ **Stok Tükendi**\n"
            "━━━━━━━━━━━━━━━━━\n"
            f"📦 **{title}**\n"
            f"💵 Güncel fiyat: **{shown_price}**\n\n"
            "Bu ürünün mevcut stoğu sona erdi. Yeni stok geldiğinde tekrar duyuracağız.\n"
            "━━━━━━━━━━━━━━━━━"
        )
    return (
        "⚡ **Son Stok Fırsatı**\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"📦 **{title}**\n"
        f"🎁 Kalan stok: **{count} adet**\n"
        f"💵 Fiyat: **{shown_price}**\n\n"
        "Stok tükenmeden satın alabilirsiniz.\n"
        "━━━━━━━━━━━━━━━━━"
    )


def build_announcement_item(brand: str, product: dict, *, text: str, kind: str, marker: str, recipients: list[int]) -> dict:
    brand = normalize_brand(brand)
    product_id = str(product.get("id") or product.get("title") or "product")
    key = f"{kind}:{brand}:{product_id}:{marker}"
    return {
        "idempotency_key": key,
        "brand": brand,
        "kind": kind,
        "product_id": product_id,
        "title": str(product.get("title") or "Ürün"),
        "text": text,
        "button_url": str(product.get("url") or product.get("shopier_url") or ""),
        "button_text": "🛒 Satın Al",
        "image_url": str(
            product.get("image_url") or product.get("image") or product.get("cover_url") or ""
        ),
        "recipients": [int(uid) for uid in recipients],
    }


async def drain_queue(
    queue: AnnouncementQueue,
    send_one: Callable[[int, dict], Awaitable[bool]],
) -> dict:
    """Resume pending items and return aggregate delivery counts."""
    total = {"success": 0, "failed": 0, "items": 0}
    for initial in queue.pending():
        item = queue.update(initial["id"], status="sending") or initial
        sent = set(str(uid) for uid in item.get("sent_ids", []))
        failed = set(str(uid) for uid in item.get("failed_ids", []))
        recipients = [int(uid) for uid in item.get("recipients", []) if str(uid).isdigit()]
        for uid in recipients:
            if str(uid) in sent:
                continue
            try:
                ok = bool(await send_one(uid, item))
            except Exception:
                ok = False
            if ok:
                sent.add(str(uid))
                total["success"] += 1
            else:
                failed.add(str(uid))
                total["failed"] += 1
            queue.update(
                item["id"],
                sent_ids=sorted(sent),
                failed_ids=sorted(failed),
                next_index=len(sent) + len(failed),
            )
            await asyncio.sleep(0.05)
        queue.update(
            item["id"],
            status="completed",
            sent_ids=sorted(sent),
            failed_ids=sorted(failed),
            next_index=len(recipients),
            completed_at=utc_now(),
        )
        total["items"] += 1
    return total


async def send_telethon_item(client, button_factory, user_id: int, item: dict) -> bool:
    """Send a queued item through a running Telethon bot client."""
    buttons = []
    if item.get("button_url"):
        buttons = [[button_factory(item.get("button_text", "🛒 Satın Al"), item["button_url"])]]
    image_url = str(item.get("image_url") or "").strip()
    if image_url.startswith("https://"):
        await client.send_file(
            user_id,
            image_url,
            caption=item["text"],
            buttons=buttons or None,
            parse_mode="md",
        )
    else:
        await client.send_message(
            user_id,
            item["text"],
            buttons=buttons or None,
            parse_mode="md",
        )
    return True


def drain_queue_sync(queue: AnnouncementQueue, send_one: Callable[[int, dict], bool]) -> dict:
    """Synchronous equivalent used by the Flask catalog worker."""
    total = {"success": 0, "failed": 0, "items": 0}
    for initial in queue.pending():
        item = queue.update(initial["id"], status="sending") or initial
        sent = set(str(uid) for uid in item.get("sent_ids", []))
        failed = set(str(uid) for uid in item.get("failed_ids", []))
        recipients = [int(uid) for uid in item.get("recipients", []) if str(uid).isdigit()]
        for uid in recipients:
            if str(uid) in sent:
                continue
            try:
                ok = bool(send_one(uid, item))
            except Exception:
                ok = False
            if ok:
                sent.add(str(uid))
                total["success"] += 1
            else:
                failed.add(str(uid))
                total["failed"] += 1
            queue.update(
                item["id"],
                sent_ids=sorted(sent),
                failed_ids=sorted(failed),
                next_index=len(sent) + len(failed),
            )
            time.sleep(0.05)
        queue.update(
            item["id"],
            status="completed",
            sent_ids=sorted(sent),
            failed_ids=sorted(failed),
            next_index=len(recipients),
            completed_at=utc_now(),
        )
        total["items"] += 1
    return total


def send_bot_api_message(brand: str, user_id: int, item: dict) -> bool:
    token = bot_token(brand)
    if not token:
        return False
    text = str(item.get("text") or "").strip()
    if not text:
        return False
    button_url = str(item.get("button_url") or "").strip()
    payload = {"chat_id": int(user_id), "text": text, "parse_mode": "Markdown"}
    if button_url.startswith("https://"):
        payload["reply_markup"] = {
            "inline_keyboard": [[{
                "text": str(item.get("button_text") or "🛒 Satın Al"),
                "url": button_url,
            }]]
        }
    image_url = str(item.get("image_url") or "").strip()
    method = "sendPhoto" if image_url.startswith("https://") else "sendMessage"
    if method == "sendPhoto":
        payload = {
            "chat_id": int(user_id),
            "photo": image_url,
            "caption": text,
            "parse_mode": "Markdown",
            **({"reply_markup": payload["reply_markup"]} if "reply_markup" in payload else {}),
        }
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        return bool(result.get("ok"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return False


def enqueue_new_product(brand: str, product: dict) -> tuple[dict, bool]:
    title = str(product.get("title") or "Yeni ürün").strip()
    price = str(product.get("price") or "Fiyat mağazada güncel").strip()
    url = str(product.get("url") or product.get("shopier_url") or "").strip()
    text = (
        "🆕 **Yeni Ürün Geldi**\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"📦 **{title}**\n"
        f"💵 Fiyat: **{price}**\n\n"
        "Mağazada şimdi satışta.\n"
        "━━━━━━━━━━━━━━━━━"
    )
    queue = AnnouncementQueue(brand, "new_product")
    return queue.enqueue(build_announcement_item(
        brand, product, text=text, kind="new_product", marker="catalog_v1",
        recipients=load_subscribers(brand),
    ))


def dispatch_pending_new_product_announcements() -> dict:
    totals = {"success": 0, "failed": 0, "items": 0}
    for brand in BRANDS:
        result = drain_queue_sync(
            AnnouncementQueue(brand, "new_product"),
            lambda uid, item, current=brand: send_bot_api_message(current, uid, item),
        )
        for key in totals:
            totals[key] += int(result.get(key, 0) or 0)
    return totals
