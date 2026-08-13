"""Secure PostgreSQL-backed LisansArena Telegram Mini App store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import parse_qsl
import urllib.parse
import urllib.request

from argon2 import PasswordHasher
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Blueprint, abort, jsonify, render_template, request, send_file, session
import pyotp
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, MetaData,
    String, Table, Text, UniqueConstraint, and_, create_engine, func, insert,
    select, update,
)
from sqlalchemy.exc import IntegrityError


la = Blueprint("lisansarena_store", __name__)
metadata = MetaData()
# Temporary 1 TL package for the real-payment release smoke test.
TOPUP_AMOUNTS = (100, 10000, 20000, 50000, 100000, 200000, 500000)

users = Table(
    "la_users", metadata,
    Column("id", Integer, primary_key=True),
    Column("telegram_id", String(32), unique=True, nullable=False),
    Column("username", String(64)),
    Column("display_name", String(160)),
    Column("status", String(24), nullable=False, default="active"),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
products = Table(
    "la_products", metadata,
    Column("id", Integer, primary_key=True),
    Column("legacy_shopier_id", String(64), unique=True),
    Column("name", String(220), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("category", String(80), nullable=False, default="Diğer"),
    Column("price_cents", Integer, nullable=False),
    Column("cost_cents", Integer),
    Column("delivery_type", String(16), nullable=False, default="manual"),
    Column("published", Boolean, nullable=False, default=False),
    Column("guide", Text, nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
inventory = Table(
    "la_inventory", metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("la_products.id"), nullable=False, index=True),
    Column("ciphertext", LargeBinary, nullable=False),
    Column("nonce", LargeBinary, nullable=False),
    Column("sold_order_id", Integer, ForeignKey("la_orders.id")),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
orders = Table(
    "la_orders", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("la_users.id"), nullable=False, index=True),
    Column("product_id", Integer, ForeignKey("la_products.id"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("total_cents", Integer, nullable=False),
    Column("status", String(32), nullable=False),
    Column("delivery_type", String(16), nullable=False),
    Column("deadline_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)
wallet_ledger = Table(
    "la_wallet_ledger", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("la_users.id"), nullable=False, index=True),
    Column("amount_cents", Integer, nullable=False),
    Column("entry_type", String(32), nullable=False),
    Column("reference_type", String(32), nullable=False),
    Column("reference_id", String(96), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("entry_type", "reference_type", "reference_id", name="uq_la_ledger_reference"),
)
topup_intents = Table(
    "la_topup_intents", metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(16), unique=True, nullable=False),
    Column("user_id", Integer, ForeignKey("la_users.id"), nullable=False),
    Column("amount_cents", Integer, nullable=False),
    Column("shopier_product_id", String(64)),
    Column("status", String(24), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
shopier_orders = Table(
    "la_shopier_orders", metadata,
    Column("id", Integer, primary_key=True),
    Column("order_number", String(96), unique=True, nullable=False),
    Column("webhook_id", String(128), unique=True),
    Column("topup_code", String(16)),
    Column("amount_cents", Integer, nullable=False),
    Column("status", String(32), nullable=False),
    Column("payload", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("processed_at", DateTime(timezone=True)),
)
admins = Table(
    "la_admins", metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(80), unique=True, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("totp_secret", String(64), nullable=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
audit_log = Table(
    "la_audit_log", metadata,
    Column("id", Integer, primary_key=True),
    Column("admin_id", Integer, ForeignKey("la_admins.id")),
    Column("action", String(80), nullable=False),
    Column("target", String(160), nullable=False),
    Column("detail", Text, nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def utcnow():
    return datetime.now(timezone.utc)


def cents(value) -> int:
    try:
        normalized = str(value).replace("TL", "").replace("₺", "").strip().replace(" ", "")
        if "," in normalized and "." in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")
        return int((Decimal(normalized) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Geçersiz tutar")


def money(value: int) -> str:
    return f"{Decimal(value) / 100:.2f} TL".replace(".", ",")


def clean_storefront_text(value):
    """Repair legacy UTF-8 text that was previously decoded as Windows text."""
    text = str(value or "")
    if not any(marker in text for marker in ("Ã", "Ä", "Å", "â", "ð")):
        return text
    for encoding in ("cp1252", "latin1"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
            if repaired.count("Ã") + repaired.count("Ä") + repaired.count("Å") < text.count("Ã") + text.count("Ä") + text.count("Å"):
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text


def storefront_category(name):
    value = clean_storefront_text(name).casefold()
    groups = (
        ("Yapay Zekâ", ("chatgpt", "gemini", "grok", "perplexity", "deepseek", "ai ", "yapay")),
        ("Tasarım", ("canva", "adobe", "freepik", "envato", "figma", "magnific")),
        ("Eğlence", ("netflix", "youtube", "spotify", "exxen", "disney", "hbo", "prime")),
        ("Oyun", ("steam", "xbox", "zula", "fc26", "game pass")),
        ("Yazılım", ("windows", "office", "autocad", "lisans")),
        ("Güvenlik", ("kaspersky", "vpn", "antivir")),
        ("Kupon ve Puan", ("kupon", "shell", "trendyol", "market", "yemek")),
    )
    for category, keywords in groups:
        if any(keyword in value for keyword in keywords):
            return category
    return "Diğer"


def margin_is_allowed(price_cents: int, cost_cents: int, delivery_type: str, fee_rate=None) -> bool:
    if price_cents <= 0 or cost_cents is None:
        return False
    rate = Decimal(str(fee_rate if fee_rate is not None else os.environ.get("SHOPIER_FEE_RATE", "0.0499")))
    net = Decimal(price_cents) * (Decimal(1) - rate) - Decimal(cost_cents)
    minimum = Decimal("0.25") if delivery_type == "automatic" else Decimal("0.35")
    return net / Decimal(price_cents) >= minimum


class StoreUnavailable(RuntimeError):
    pass


class LisansArenaStore:
    def __init__(self, database_url=None, *, encryption_key=None):
        url = database_url or os.environ.get("LISANSARENA_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not url:
            raise StoreUnavailable("LisansArena PostgreSQL yapılandırılmadı")
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        self.engine = create_engine(url, pool_pre_ping=True, future=True)
        raw_key = encryption_key or os.environ.get("LISANSARENA_STOCK_KEY", "")
        if not raw_key:
            raise StoreUnavailable("LisansArena stok şifreleme anahtarı yapılandırılmadı")
        try:
            key = base64.urlsafe_b64decode(raw_key + "=" * (-len(raw_key) % 4))
        except Exception as exc:
            raise StoreUnavailable("Stok anahtarı geçersiz") from exc
        if len(key) not in (16, 24, 32):
            raise StoreUnavailable("Stok anahtarı 128/192/256 bit olmalı")
        self.aes = AESGCM(key)
        metadata.create_all(self.engine)
        self._install_ledger_guards()
        self.import_legacy_drafts()
        self.bootstrap_admin()

    def _install_ledger_guards(self):
        if self.engine.dialect.name != "postgresql":
            return
        statements = (
            """CREATE OR REPLACE FUNCTION la_ledger_immutable() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'wallet ledger is immutable'; END; $$ LANGUAGE plpgsql""",
            "DROP TRIGGER IF EXISTS la_ledger_no_update ON la_wallet_ledger",
            "DROP TRIGGER IF EXISTS la_ledger_no_delete ON la_wallet_ledger",
            "CREATE TRIGGER la_ledger_no_update BEFORE UPDATE ON la_wallet_ledger FOR EACH ROW EXECUTE FUNCTION la_ledger_immutable()",
            "CREATE TRIGGER la_ledger_no_delete BEFORE DELETE ON la_wallet_ledger FOR EACH ROW EXECUTE FUNCTION la_ledger_immutable()",
        )
        from sqlalchemy import text
        with self.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

    def import_legacy_drafts(self):
        path = os.path.join(os.path.dirname(__file__), "lisansarena_shopier_links.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            legacy = json.load(handle)
        now = utcnow()
        with self.engine.begin() as conn:
            existing = {row[0] for row in conn.execute(select(products.c.legacy_shopier_id))}
            for item in legacy:
                legacy_id = str(item.get("id") or "")
                if not legacy_id or legacy_id in existing:
                    continue
                conn.execute(insert(products).values(
                    legacy_shopier_id=legacy_id,
                    name=str(item.get("title") or "İsimsiz ürün")[:220],
                    description=str(item.get("description") or ""),
                    category="Taslak aktarım",
                    price_cents=cents(item.get("price") or item.get("priceData", {}).get("price") or 0),
                    cost_cents=None,
                    delivery_type="manual",
                    published=False,
                    guide="",
                    created_at=now,
                    updated_at=now,
                ))

    def bootstrap_admin(self):
        username = os.environ.get("LISANSARENA_ADMIN_USER", "").strip()
        password_hash = os.environ.get("LISANSARENA_ADMIN_PASSWORD_HASH", "").strip()
        totp_secret = os.environ.get("LISANSARENA_ADMIN_TOTP_SECRET", "").strip()
        if not (username and password_hash and totp_secret):
            return
        with self.engine.begin() as conn:
            if conn.execute(select(admins.c.id).where(admins.c.username == username)).first() is None:
                conn.execute(insert(admins).values(
                    username=username, password_hash=password_hash,
                    totp_secret=totp_secret, active=True, created_at=utcnow(),
                ))

    def encrypt_stock(self, product_id: int, plaintext: str):
        nonce = secrets.token_bytes(12)
        aad = f"la-stock:{product_id}".encode()
        return nonce, self.aes.encrypt(nonce, plaintext.encode("utf-8"), aad)

    def decrypt_stock(self, product_id: int, nonce: bytes, ciphertext: bytes):
        return self.aes.decrypt(nonce, ciphertext, f"la-stock:{product_id}".encode()).decode("utf-8")

    def get_or_create_user(self, telegram_user: dict):
        telegram_id = str(telegram_user["id"])
        now = utcnow()
        with self.engine.begin() as conn:
            row = conn.execute(select(users).where(users.c.telegram_id == telegram_id)).mappings().first()
            values = {
                "username": str(telegram_user.get("username") or "")[:64],
                "display_name": " ".join(filter(None, [telegram_user.get("first_name"), telegram_user.get("last_name")]))[:160],
            }
            if row:
                conn.execute(update(users).where(users.c.id == row["id"]).values(**values))
                return row["id"]
            return conn.execute(insert(users).values(
                telegram_id=telegram_id, status="active", created_at=now, **values
            ).returning(users.c.id)).scalar_one()

    def balance(self, conn, user_id):
        return int(conn.execute(select(func.coalesce(func.sum(wallet_ledger.c.amount_cents), 0)).where(wallet_ledger.c.user_id == user_id)).scalar_one())

    def catalog(self):
        with self.engine.connect() as conn:
            stock_count = select(func.count(inventory.c.id)).where(and_(inventory.c.product_id == products.c.id, inventory.c.sold_order_id.is_(None))).scalar_subquery()
            rows = conn.execute(select(products, stock_count.label("stock")).where(products.c.published.is_(True)).order_by(products.c.category, products.c.name)).mappings()
            return [{**dict(row), "price": money(row["price_cents"]), "stock": int(row["stock"])} for row in rows]

    def storefront_catalog(self):
        """Show the imported range while keeping unapproved drafts unbuyable."""
        with self.engine.connect() as conn:
            stock_count = select(func.count(inventory.c.id)).where(and_(inventory.c.product_id == products.c.id, inventory.c.sold_order_id.is_(None))).scalar_subquery()
            rows = conn.execute(select(products, stock_count.label("stock")).order_by(products.c.name)).mappings()
            result = []
            for row in rows:
                item = dict(row)
                item["name"] = clean_storefront_text(item["name"])
                item["description"] = clean_storefront_text(item.get("description")) or "Ürün ayrıntıları ve teslimat bilgileri hazırlanıyor."
                item["guide"] = clean_storefront_text(item.get("guide"))
                item["category"] = storefront_category(item["name"])
                item["stock"] = int(row["stock"])
                item["price"] = money(row["price_cents"])
                item["available"] = bool(row["published"] and (row["delivery_type"] == "manual" or item["stock"] > 0))
                result.append(item)
            return result

    def quote(self, product_id, quantity):
        quantity = max(1, min(int(quantity), 10))
        with self.engine.connect() as conn:
            product = conn.execute(select(products).where(and_(products.c.id == int(product_id), products.c.published.is_(True)))).mappings().first()
            if not product:
                raise ValueError("Ürün bulunamadı")
            return {"product_id": product["id"], "quantity": quantity, "total_cents": product["price_cents"] * quantity, "total": money(product["price_cents"] * quantity)}

    def purchase(self, user_id, product_id, quantity):
        quantity = max(1, min(int(quantity), 10))
        now = utcnow()
        with self.engine.begin() as conn:
            # Serializes purchases for this wallet and inventory product.
            customer = conn.execute(select(users).where(users.c.id == user_id).with_for_update()).mappings().one()
            if customer["status"] != "active":
                raise ValueError("Hesap incelemede; destek ekibiyle iletişime geçin")
            product = conn.execute(select(products).where(products.c.id == int(product_id)).with_for_update()).mappings().first()
            if not product or not product["published"]:
                raise ValueError("Ürün satışta değil")
            total = int(product["price_cents"]) * quantity
            if self.balance(conn, user_id) < total:
                raise ValueError("Yetersiz bakiye")
            delivery = product["delivery_type"]
            if delivery == "automatic":
                units = conn.execute(select(inventory).where(and_(inventory.c.product_id == product["id"], inventory.c.sold_order_id.is_(None))).limit(quantity).with_for_update(skip_locked=True)).mappings().all()
                if len(units) != quantity:
                    raise ValueError("Stok tükendi")
            else:
                units = []
            order_id = conn.execute(insert(orders).values(
                user_id=user_id, product_id=product["id"], quantity=quantity,
                total_cents=total, status="delivered" if delivery == "automatic" else "manual_pending",
                delivery_type=delivery,
                deadline_at=None if delivery == "automatic" else now + timedelta(hours=24),
                created_at=now, completed_at=now if delivery == "automatic" else None,
            ).returning(orders.c.id)).scalar_one()
            conn.execute(insert(wallet_ledger).values(
                user_id=user_id, amount_cents=-total, entry_type="purchase",
                reference_type="order", reference_id=str(order_id), created_at=now,
            ))
            delivered = []
            for unit in units:
                conn.execute(update(inventory).where(inventory.c.id == unit["id"]).values(sold_order_id=order_id))
                delivered.append(self.decrypt_stock(product["id"], unit["nonce"], unit["ciphertext"]))
            return {"order_id": order_id, "status": "delivered" if delivered else "manual_pending", "delivery": delivered, "deadline": (now + timedelta(hours=24)).isoformat() if delivery != "automatic" else None}

    def create_topup(self, user_id, amount_cents):
        amount_cents = int(amount_cents)
        if amount_cents not in TOPUP_AMOUNTS:
            raise ValueError("Geçersiz bakiye paketi")
        package_map = json.loads(os.environ.get("LISANSARENA_SHOPIER_TOPUP_PRODUCTS", "{}") or "{}")
        mapping_path = os.path.join(os.path.dirname(__file__), "lisansarena_topup_products.json")
        if not package_map and os.path.exists(mapping_path):
            with open(mapping_path, "r", encoding="utf-8") as handle:
                package_map = json.load(handle)
        product_id = str(package_map.get(str(amount_cents // 100)) or "")
        code = f"LA-{secrets.token_hex(3).upper()}"
        now = utcnow()
        with self.engine.begin() as conn:
            conn.execute(insert(topup_intents).values(
                code=code, user_id=user_id, amount_cents=amount_cents,
                shopier_product_id=product_id or None, status="pending",
                expires_at=now + timedelta(hours=24), created_at=now,
            ))
        return {
            "code": code, "amount": money(amount_cents),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "shopier_url": f"https://www.shopier.com/lisansarena/{product_id}" if product_id else None,
        }

    def ingest_webhook(self, payload: dict, webhook_id: str | None):
        order_number = str(payload.get("orderNumber") or payload.get("order_number") or payload.get("id") or "").strip()
        if not order_number:
            raise ValueError("Sipariş numarası eksik")
        note = str(payload.get("note") or payload.get("orderNote") or payload.get("buyerNote") or "")
        match = re.search(r"\bLA-[A-F0-9]{6}\b", note.upper())
        amount_value = payload.get("total") or payload.get("amount") or (payload.get("totals") or {}).get("total")
        amount_cents = cents(amount_value)
        payment_status = str(payload.get("paymentStatus") or payload.get("status") or "").casefold()
        incoming_status = "refund_pending" if payment_status in {"refunded", "refund", "cancelled", "canceled"} else "pending"
        with self.engine.begin() as conn:
            existing = conn.execute(select(shopier_orders).where(shopier_orders.c.order_number == order_number).with_for_update()).mappings().first()
            if existing:
                if incoming_status == "refund_pending" and existing["status"] not in {"refunded", "refund_pending"}:
                    conn.execute(update(shopier_orders).where(shopier_orders.c.id == existing["id"]).values(
                        webhook_id=webhook_id or existing["webhook_id"], status="refund_pending",
                        payload=json.dumps(payload, ensure_ascii=False), processed_at=None,
                    ))
                return order_number
            conn.execute(insert(shopier_orders).values(
                order_number=order_number, webhook_id=webhook_id or None,
                topup_code=match.group(0) if match else None, amount_cents=amount_cents,
                status=incoming_status, payload=json.dumps(payload, ensure_ascii=False), created_at=utcnow(),
            ))
        return order_number

    def reconcile_shopier_orders(self, token: str | None = None, days: int = 2):
        """Fetch recent Shopier orders and enqueue paid/refunded ones idempotently."""
        token = (token or os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN", "")).strip()
        if not token:
            return 0
        date_start = (utcnow() - timedelta(days=max(1, days))).strftime("%Y-%m-%dT%H:%M:%S%z")
        query = urllib.parse.urlencode({"limit": 100, "dateStart": date_start})
        api_request = urllib.request.Request(
            f"https://api.shopier.com/v1/orders?{query}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "LisansArena-Store/1.0",
            },
        )
        with urllib.request.urlopen(api_request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("data") or payload.get("orders") or []
        accepted = 0
        for order in rows:
            if not isinstance(order, dict):
                continue
            status = str(order.get("paymentStatus") or order.get("status") or "").casefold()
            if status not in {"paid", "refunded", "refund", "cancelled", "canceled"}:
                continue
            order_number = str(order.get("orderNumber") or order.get("order_number") or order.get("id") or "").strip()
            if not order_number:
                continue
            self.ingest_webhook(order, f"api:{order_number}")
            accepted += 1
        return accepted

    def process_webhooks(self, limit=20):
        processed = 0
        with self.engine.begin() as conn:
            events = conn.execute(select(shopier_orders).where(shopier_orders.c.status.in_(("pending", "refund_pending"))).limit(limit).with_for_update(skip_locked=True)).mappings().all()
            for event in events:
                if event["status"] == "refund_pending":
                    credit = conn.execute(select(wallet_ledger).where(and_(
                        wallet_ledger.c.entry_type == "topup",
                        wallet_ledger.c.reference_type == "shopier_order",
                        wallet_ledger.c.reference_id == event["order_number"],
                    ))).mappings().first()
                    if credit:
                        try:
                            with conn.begin_nested():
                                conn.execute(insert(wallet_ledger).values(
                                    user_id=credit["user_id"], amount_cents=-abs(credit["amount_cents"]),
                                    entry_type="shopier_refund", reference_type="shopier_order",
                                    reference_id=f"refund:{event['order_number']}", created_at=utcnow(),
                                ))
                        except IntegrityError:
                            pass
                        if self.balance(conn, credit["user_id"]) < 0:
                            conn.execute(update(users).where(users.c.id == credit["user_id"]).values(status="review"))
                        status = "refunded"
                    else:
                        status = "manual_review"
                    conn.execute(update(shopier_orders).where(shopier_orders.c.id == event["id"]).values(status=status, processed_at=utcnow()))
                    processed += 1
                    continue
                intent = None
                if event["topup_code"]:
                    intent = conn.execute(select(topup_intents).where(topup_intents.c.code == event["topup_code"]).with_for_update()).mappings().first()
                status = "manual_review"
                payload = json.loads(event["payload"])
                line_items = payload.get("lineItems") or payload.get("line_items") or payload.get("items") or []
                first_item = line_items[0] if isinstance(line_items, list) and line_items else {}
                received_product_id = str(first_item.get("productId") or first_item.get("product_id") or first_item.get("id") or "")
                try:
                    received_quantity = int(first_item.get("quantity", 1))
                except (TypeError, ValueError):
                    received_quantity = 0
                expires_at = intent["expires_at"] if intent else None
                if expires_at is not None and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                product_matches = bool(
                    intent and intent["shopier_product_id"] and
                    received_product_id == str(intent["shopier_product_id"]) and
                    received_quantity == 1
                )
                if intent and intent["status"] == "pending" and expires_at > utcnow() and intent["amount_cents"] == event["amount_cents"] and product_matches:
                    try:
                        with conn.begin_nested():
                            conn.execute(insert(wallet_ledger).values(
                                user_id=intent["user_id"], amount_cents=event["amount_cents"],
                                entry_type="topup", reference_type="shopier_order",
                                reference_id=event["order_number"], created_at=utcnow(),
                            ))
                        conn.execute(update(topup_intents).where(topup_intents.c.id == intent["id"]).values(status="completed"))
                        status = "credited"
                    except IntegrityError:
                        status = "duplicate"
                conn.execute(update(shopier_orders).where(shopier_orders.c.id == event["id"]).values(status=status, processed_at=utcnow()))
                processed += 1
        return processed

    def expire_manual_orders(self):
        with self.engine.begin() as conn:
            pending = conn.execute(select(orders).where(and_(orders.c.status == "manual_pending", orders.c.deadline_at <= utcnow())).with_for_update(skip_locked=True)).mappings().all()
            for order in pending:
                conn.execute(insert(wallet_ledger).values(
                    user_id=order["user_id"], amount_cents=order["total_cents"],
                    entry_type="manual_timeout_refund", reference_type="order",
                    reference_id=f"refund:{order['id']}", created_at=utcnow(),
                ))
                conn.execute(update(orders).where(orders.c.id == order["id"]).values(status="refunded", completed_at=utcnow()))
            return len(pending)


_store = None
_store_error = None
_worker_started = False


def get_store():
    global _store, _store_error
    if _store is None and _store_error is None:
        try:
            _store = LisansArenaStore()
        except Exception as exc:
            _store_error = str(exc)
    if _store is None:
        raise StoreUnavailable(_store_error or "Mağaza kullanılamıyor")
    return _store


def verify_telegram_init_data(init_data: str, bot_token: str, max_age=24 * 60 * 60):
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    supplied_hash = pairs.pop("hash", "")
    if not supplied_hash or not bot_token:
        return None
    check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied_hash):
        return None
    try:
        auth_date = int(pairs.get("auth_date", 0))
        if abs(int(time.time()) - auth_date) > max_age:
            return None
        user = json.loads(pairs["user"])
        return user if isinstance(user, dict) and user.get("id") else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def _csrf():
    token = session.get("la_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["la_csrf"] = token
    return token


def _require_csrf():
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    if not supplied or not hmac.compare_digest(str(supplied), str(session.get("la_csrf", ""))):
        abort(403)


def customer_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("la_user_id"):
            return jsonify({"error": "Telegram doğrulaması gerekli"}), 401
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            _require_csrf()
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("la_admin_id"):
            return jsonify({"error": "Yönetici girişi gerekli"}), 401
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            _require_csrf()
        return fn(*args, **kwargs)
    return wrapped


def _json_error(exc, status=400):
    return jsonify({"error": str(exc)}), status


@la.get("/la/app")
def mini_app():
    return render_template("lisansarena_app.html")


@la.get("/la/assets/brand")
def brand_asset():
    return send_file(os.path.join(os.path.dirname(__file__), "lisansarena_banner.jpeg"), mimetype="image/jpeg", max_age=86400)


@la.post("/api/la/auth/telegram")
def telegram_auth():
    payload = request.get_json(silent=True) or {}
    user = verify_telegram_init_data(str(payload.get("initData") or ""), os.environ.get("LISANSARENA_BOT_TOKEN", ""))
    if not user:
        return _json_error("Telegram doğrulaması başarısız", 401)
    try:
        user_id = get_store().get_or_create_user(user)
    except StoreUnavailable as exc:
        return _json_error(exc, 503)
    session.clear()
    session["la_user_id"] = user_id
    session["la_csrf"] = secrets.token_urlsafe(32)
    session.permanent = True
    referral_secret = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("LISANSARENA_BOT_TOKEN", "")
    referral_code = "LA-" + hmac.new(referral_secret.encode(), str(user["id"]).encode(), hashlib.sha256).hexdigest()[:8].upper()
    return jsonify({
        "ok": True,
        "csrf": session["la_csrf"],
        "user": {
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "username": user.get("username", ""),
            "photo_url": user.get("photo_url", ""),
            "referral_code": referral_code,
            "referrals_enabled": False,
        },
    })


@la.get("/api/la/catalog")
@customer_required
def api_catalog():
    try:
        return jsonify({"products": get_store().storefront_catalog()})
    except StoreUnavailable as exc:
        return _json_error(exc, 503)


@la.post("/api/la/cart/quote")
@customer_required
def api_quote():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().quote(data.get("product_id"), data.get("quantity", 1)))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.post("/api/la/purchases")
@customer_required
def api_purchase():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().purchase(session["la_user_id"], data.get("product_id"), data.get("quantity", 1)))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.get("/api/la/wallet")
@customer_required
def api_wallet():
    store = get_store()
    with store.engine.connect() as conn:
        balance = store.balance(conn, session["la_user_id"])
        entries = conn.execute(select(wallet_ledger).where(wallet_ledger.c.user_id == session["la_user_id"]).order_by(wallet_ledger.c.id.desc()).limit(50)).mappings().all()
    return jsonify({"balance_cents": balance, "balance": money(balance), "entries": [{**dict(row), "amount": money(row["amount_cents"])} for row in entries]})


@la.post("/api/la/topups")
@customer_required
def api_topups():
    try:
        return jsonify(get_store().create_topup(session["la_user_id"], (request.get_json(silent=True) or {}).get("amount_cents")))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.get("/api/la/orders")
@customer_required
def api_orders():
    store = get_store()
    with store.engine.connect() as conn:
        rows = conn.execute(select(orders, products.c.name.label("product_name")).join(products, products.c.id == orders.c.product_id).where(orders.c.user_id == session["la_user_id"]).order_by(orders.c.id.desc()).limit(100)).mappings().all()
    return jsonify({"orders": [{**dict(row), "total": money(row["total_cents"])} for row in rows]})


def _valid_shopier_signature(raw: bytes, supplied: str):
    secret = os.environ.get("LISANSARENA_SHOPIER_WEBHOOK_SECRET", "")
    if not secret or not supplied:
        return False
    digest = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    candidates = (digest.hex(), base64.b64encode(digest).decode(), base64.urlsafe_b64encode(digest).decode().rstrip("="))
    return any(hmac.compare_digest(supplied, item) for item in candidates)


@la.post("/api/shopier/lisansarena/webhook")
def shopier_webhook():
    raw = request.get_data(cache=True)
    signature = request.headers.get("Shopier-Signature", "")
    if not _valid_shopier_signature(raw, signature):
        return _json_error("Yetkisiz webhook", 401)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error("Geçersiz JSON")
    try:
        order_number = get_store().ingest_webhook(payload, request.headers.get("Shopier-Webhook-Id"))
        return jsonify({"accepted": True, "order_number": order_number}), 202
    except IntegrityError:
        return jsonify({"accepted": True, "duplicate": True}), 200
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.route("/la/admin", methods=["GET", "POST"])
def admin_page():
    error = ""
    if request.method == "POST":
        _require_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        otp = request.form.get("otp", "")
        try:
            store = get_store()
            with store.engine.connect() as conn:
                row = conn.execute(select(admins).where(and_(admins.c.username == username, admins.c.active.is_(True)))).mappings().first()
            if not row:
                raise ValueError("Giriş reddedildi")
            PasswordHasher().verify(row["password_hash"], password)
            if not pyotp.TOTP(row["totp_secret"]).verify(otp, valid_window=1):
                raise ValueError("Giriş reddedildi")
            session.clear()
            session["la_admin_id"] = row["id"]
            session["la_csrf"] = secrets.token_urlsafe(32)
            session.permanent = True
        except Exception:
            time.sleep(0.3)
            error = "Giriş reddedildi"
    return render_template("lisansarena_admin.html", logged_in=bool(session.get("la_admin_id")), csrf=_csrf(), error=error)


@la.get("/api/la/admin/overview")
@admin_required
def admin_overview():
    store = get_store()
    with store.engine.connect() as conn:
        product_rows = conn.execute(select(products).order_by(products.id)).mappings().all()
        pending = conn.execute(select(orders, products.c.name.label("product_name")).join(products).where(orders.c.status == "manual_pending").order_by(orders.c.deadline_at)).mappings().all()
        review = conn.execute(select(shopier_orders).where(shopier_orders.c.status == "manual_review").order_by(shopier_orders.c.id.desc())).mappings().all()
    return jsonify({"products": [dict(row) for row in product_rows], "manual_orders": [dict(row) for row in pending], "topup_review": [dict(row) for row in review]})


@la.post("/api/la/admin/products/<int:product_id>")
@admin_required
def admin_product(product_id):
    data = request.get_json(silent=True) or {}
    allowed = {key: data[key] for key in ("name", "description", "category", "price_cents", "cost_cents", "delivery_type", "guide", "published") if key in data}
    if allowed.get("delivery_type") not in (None, "automatic", "manual"):
        return _json_error("Teslim tipi geçersiz")
    store = get_store()
    with store.engine.begin() as conn:
        current = conn.execute(select(products).where(products.c.id == product_id).with_for_update()).mappings().first()
        if not current:
            abort(404)
        merged = {**dict(current), **allowed}
        if merged.get("published"):
            if merged.get("cost_cents") is None or not merged.get("description") or not merged.get("delivery_type"):
                return _json_error("Maliyet, açıklama ve teslim tipi onaylanmadan yayımlanamaz")
            minimum = Decimal("0.25") if merged["delivery_type"] == "automatic" else Decimal("0.35")
            if not margin_is_allowed(merged["price_cents"], merged["cost_cents"], merged["delivery_type"]):
                return _json_error(f"Net marj en az %{int(minimum * 100)} olmalı")
        conn.execute(update(products).where(products.c.id == product_id).values(**allowed, updated_at=utcnow()))
        conn.execute(insert(audit_log).values(admin_id=session["la_admin_id"], action="product_update", target=str(product_id), detail=json.dumps(allowed, ensure_ascii=False), created_at=utcnow()))
    return jsonify({"ok": True})


@la.post("/api/la/admin/products/<int:product_id>/stock")
@admin_required
def admin_stock(product_id):
    values = (request.get_json(silent=True) or {}).get("items") or []
    if not isinstance(values, list) or not values or len(values) > 500:
        return _json_error("1-500 stok kaydı gerekli")
    store = get_store()
    now = utcnow()
    with store.engine.begin() as conn:
        if not conn.execute(select(products.c.id).where(products.c.id == product_id)).first():
            abort(404)
        for value in values:
            nonce, encrypted = store.encrypt_stock(product_id, str(value))
            conn.execute(insert(inventory).values(product_id=product_id, nonce=nonce, ciphertext=encrypted, sold_order_id=None, created_at=now))
        conn.execute(insert(audit_log).values(admin_id=session["la_admin_id"], action="stock_add", target=str(product_id), detail=f"count={len(values)}", created_at=now))
    return jsonify({"ok": True, "count": len(values)})


@la.post("/api/la/admin/orders/<int:order_id>/fulfill")
@admin_required
def admin_fulfill(order_id):
    store = get_store()
    with store.engine.begin() as conn:
        row = conn.execute(select(orders).where(orders.c.id == order_id).with_for_update()).mappings().first()
        if not row or row["status"] != "manual_pending":
            return _json_error("Sipariş beklemede değil")
        conn.execute(update(orders).where(orders.c.id == order_id).values(status="delivered", completed_at=utcnow()))
        conn.execute(insert(audit_log).values(admin_id=session["la_admin_id"], action="manual_fulfill", target=str(order_id), detail="", created_at=utcnow()))
    return jsonify({"ok": True})


def start_store_worker():
    global _worker_started
    if _worker_started or os.environ.get("LISANSARENA_STORE_WORKER", "1") != "1":
        return
    _worker_started = True

    def loop():
        next_reconciliation = 0.0
        while True:
            try:
                store = get_store()
                now = time.monotonic()
                if now >= next_reconciliation:
                    store.reconcile_shopier_orders()
                    interval = max(60, int(os.environ.get("LISANSARENA_RECONCILE_SECONDS", "300")))
                    next_reconciliation = now + interval
                store.process_webhooks()
                store.expire_manual_orders()
            except Exception as exc:
                print(f"[LisansArena Store] worker: {type(exc).__name__}: {exc}")
            time.sleep(30)

    threading.Thread(target=loop, name="lisansarena-store-worker", daemon=True).start()
