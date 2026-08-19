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
import urllib.error
from urllib.parse import parse_qsl
import urllib.parse
import urllib.request

try:
    from argon2 import PasswordHasher
except ImportError:  # Wasmer web build keeps Argon2-only admin login on Render.
    PasswordHasher = None
from werkzeug.security import check_password_hash
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Blueprint, abort, jsonify, render_template, request, send_file, session
import pyotp
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, MetaData,
    String, Table, Text, UniqueConstraint, and_, create_engine, func, insert,
    inspect, select, text, update,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, IntegrityError


la = Blueprint("lisansarena_store", __name__)
metadata = MetaData()
# Temporary 1 TL package for the real-payment release smoke test.
TOPUP_AMOUNTS = (100, 10000, 20000, 50000, 100000, 200000, 500000)
CUSTOM_TOPUP_MIN_CENTS = 1000
CUSTOM_TOPUP_MAX_CENTS = 5_000_000
SHOPIER_API = "https://api.shopier.com/v1"

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
    Column("topup_mode", String(16), nullable=False, default="package"),
    Column("listing_state", String(24), nullable=False, default="not_applicable"),
    Column("closed_at", DateTime(timezone=True)),
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

product_display = Table(
    "la_product_display", metadata,
    Column("product_id", Integer, ForeignKey("la_products.id"), primary_key=True),
    Column("image_key", String(180), nullable=False, default="lisansarena_logo_v2.png"),
    Column("featured", Boolean, nullable=False, default=False),
    Column("display_order", Integer, nullable=False, default=999),
    Column("request_enabled", Boolean, nullable=False, default=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

tickets = Table(
    "la_tickets", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("la_users.id"), nullable=False, index=True),
    Column("ticket_type", String(24), nullable=False),
    Column("product_id", Integer, ForeignKey("la_products.id")),
    Column("order_id", Integer, ForeignKey("la_orders.id")),
    Column("subject", String(220), nullable=False),
    Column("message", Text, nullable=False),
    Column("status", String(24), nullable=False, default="open"),
    Column("admin_reply", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

referrals = Table(
    "la_referrals", metadata,
    Column("id", Integer, primary_key=True),
    Column("referrer_user_id", Integer, ForeignKey("la_users.id"), nullable=False),
    Column("referred_user_id", Integer, ForeignKey("la_users.id"), nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

draws = Table(
    "la_draws", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(220), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("status", String(24), nullable=False, default="draft"),
    Column("ends_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

draw_entries = Table(
    "la_draw_entries", metadata,
    Column("id", Integer, primary_key=True),
    Column("draw_id", Integer, ForeignKey("la_draws.id"), nullable=False),
    Column("user_id", Integer, ForeignKey("la_users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("draw_id", "user_id", name="uq_la_draw_entry"),
)

user_preferences = Table(
    "la_user_preferences", metadata,
    Column("user_id", Integer, ForeignKey("la_users.id"), primary_key=True),
    Column("language", String(8), nullable=False, default="tr"),
    Column("updated_at", DateTime(timezone=True), nullable=False),
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


def product_image_key(name, catalog_id=None):
    """Return the new product-specific generated cover filename."""
    identity = str(catalog_id or clean_storefront_text(name)).casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", identity).strip("-")[:96]
    if not slug:
        slug = hashlib.sha256(str(name).encode("utf-8")).hexdigest()[:16]
    return f"la-cover-{slug}.webp"


def product_is_featured(name):
    value = clean_storefront_text(name).casefold()
    return any(term in value for term in (
        "canva pro öğretmen", "gemini pro davet", "perplexity pro",
        "adobe creative cloud (1 haftalık)", "windows 10/11", "office 365",
        "netflix", "youtube premium", "spotify premium", "trendyol go",
        "exxen", "hbo max", "prime video",
    ))


def referral_code_for_telegram_id(telegram_id):
    secret = (
        os.environ.get("FLASK_SECRET_KEY")
        or os.environ.get("LISANSARENA_BOT_TOKEN")
        or "lisansarena-local-referral"
    )
    digest = hmac.new(
        secret.encode(), str(telegram_id).encode(), hashlib.sha256
    ).hexdigest()[:8].upper()
    return f"LA-{digest}"


def margin_is_allowed(price_cents: int, cost_cents: int, delivery_type: str, fee_rate=None) -> bool:
    if price_cents <= 0 or cost_cents is None:
        return False
    rate = Decimal(str(fee_rate if fee_rate is not None else os.environ.get("SHOPIER_FEE_RATE", "0.0499")))
    net = Decimal(price_cents) * (Decimal(1) - rate) - Decimal(cost_cents)
    minimum = Decimal("0.25") if delivery_type == "automatic" else Decimal("0.35")
    return net / Decimal(price_cents) >= minimum


class StoreUnavailable(RuntimeError):
    pass


def normalize_database_url(value):
    """Normalize Render/Postgres URLs and reject malformed values safely."""
    url = str(value or "").strip()
    if len(url) >= 2 and url[0] == url[-1] and url[0] in {"'", '"'}:
        url = url[1:-1].strip()
    if not url:
        raise StoreUnavailable("LisansArena veritabanı bağlantısı yapılandırılmadı")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    try:
        parsed = make_url(url)
    except ArgumentError as exc:
        raise StoreUnavailable("LisansArena veritabanı bağlantısı geçersiz") from exc
    if parsed.get_backend_name() not in {"postgresql", "sqlite"}:
        raise StoreUnavailable("LisansArena veritabanı türü desteklenmiyor")
    return url


class LisansArenaStore:
    def __init__(self, database_url=None, *, encryption_key=None):
        url = normalize_database_url(
            database_url or os.environ.get("LISANSARENA_DATABASE_URL") or os.environ.get("DATABASE_URL")
        )
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
        self._migrate_topup_intents_schema()
        self._install_ledger_guards()
        self.import_legacy_drafts()
        self.backfill_product_display()
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

    def _migrate_topup_intents_schema(self):
        """Apply the small additive migration required by custom top-ups.

        The project intentionally has no migration runner.  These columns are
        nullable/defaulted so an existing production database can be upgraded
        safely during boot, while freshly-created databases get them from the
        table definition above.
        """
        existing = {
            column["name"]
            for column in inspect(self.engine).get_columns("la_topup_intents")
        }
        additions = (
            ("topup_mode", "VARCHAR(16) NOT NULL DEFAULT 'package'"),
            ("listing_state", "VARCHAR(24) NOT NULL DEFAULT 'not_applicable'"),
            ("closed_at", "TIMESTAMP"),
        )
        with self.engine.begin() as conn:
            for name, definition in additions:
                if name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE la_topup_intents ADD COLUMN {name} {definition}"
                    ))

    def import_legacy_drafts(self):
        """Synchronize the full Mini App catalogue independently of Shopier.

        Shopier remains only the wallet top-up rail. The archived 34 entries,
        the 10 products named in Shopier's removal notice and the six approved
        advert products are sold as manual-delivery products inside Telegram.
        """
        seed = []
        for filename in (
            "lisansarena_shopier_links.json",
            "lisansarena_catalog_additions.json",
        ):
            path = os.path.join(os.path.dirname(__file__), filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    seed.extend(json.load(handle))
        if not seed:
            return
        now = utcnow()
        with self.engine.begin() as conn:
            activation_done = conn.execute(select(audit_log.c.id).where(
                audit_log.c.action == "catalog_seed_v2_activated"
            ).limit(1)).first() is not None
            price_alignment_done = conn.execute(select(audit_log.c.id).where(
                audit_log.c.action == "catalog_prices_v3_aligned"
            ).limit(1)).first() is not None
            existing = {
                row.legacy_shopier_id: row.id
                for row in conn.execute(select(
                    products.c.id, products.c.legacy_shopier_id
                ))
                if row.legacy_shopier_id
            }
            for item in seed:
                legacy_id = str(item.get("id") or "")
                if not legacy_id:
                    continue
                values = dict(
                    legacy_shopier_id=legacy_id,
                    name=str(item.get("title") or "İsimsiz ürün")[:220],
                    description=str(item.get("description") or ""),
                    category=storefront_category(item.get("title") or ""),
                    price_cents=cents(item.get("price") or item.get("priceData", {}).get("price") or 0),
                    delivery_type="manual",
                    published=True,
                    guide="Teslimat en geç 24 saat içinde sipariş kaydına eklenir.",
                    updated_at=now,
                )
                if legacy_id in existing:
                    if not activation_done:
                        conn.execute(update(products).where(
                            products.c.id == existing[legacy_id]
                        ).values(
                            price_cents=values["price_cents"],
                            delivery_type="manual",
                            published=True,
                            guide="Teslimat en geç 24 saat içinde sipariş kaydına eklenir.",
                            updated_at=now,
                        ))
                    elif not price_alignment_done:
                        conn.execute(update(products).where(
                            products.c.id == existing[legacy_id]
                        ).values(
                            price_cents=values["price_cents"],
                            updated_at=now,
                        ))
                else:
                    conn.execute(insert(products).values(
                        **values, cost_cents=None, created_at=now
                    ))
            if not activation_done:
                conn.execute(insert(audit_log).values(
                    admin_id=None,
                    action="catalog_seed_v2_activated",
                    target="lisansarena_catalog",
                    detail="Archived 34 + Shopier notice 10 + approved advert 6 activated for Mini App",
                    created_at=now,
                ))
            if not price_alignment_done:
                conn.execute(insert(audit_log).values(
                    admin_id=None,
                    action="catalog_prices_v3_aligned",
                    target="lisansarena_catalog",
                    detail="Approved LisansArena advert prices aligned once",
                    created_at=now,
                ))

    def backfill_product_display(self):
        """Attach real covers and merchandising metadata to every product."""
        now = utcnow()
        with self.engine.begin() as conn:
            cover_migration_done = conn.execute(select(audit_log.c.id).where(
                audit_log.c.action == "catalog_covers_v2_generated"
            ).limit(1)).first() is not None
            existing = {
                row[0] for row in conn.execute(select(product_display.c.product_id))
            }
            rows = conn.execute(select(
                products.c.id, products.c.name, products.c.legacy_shopier_id
            )).all()
            for position, row in enumerate(rows, 1):
                values = dict(
                    image_key=product_image_key(row.name, row.legacy_shopier_id),
                    featured=product_is_featured(row.name),
                    display_order=position,
                    request_enabled=False,
                    updated_at=now,
                )
                if row.id in existing:
                    if not cover_migration_done:
                        conn.execute(update(product_display).where(
                            product_display.c.product_id == row.id
                        ).values(**values))
                else:
                    conn.execute(insert(product_display).values(
                        product_id=row.id, **values
                    ))
            if not cover_migration_done:
                conn.execute(insert(audit_log).values(
                    admin_id=None,
                    action="catalog_covers_v2_generated",
                    target="lisansarena_catalog",
                    detail="Product-specific generated covers and storefront order applied",
                    created_at=now,
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

    def wallet_history(self, user_id, limit=50):
        with self.engine.connect() as conn:
            balance_value = self.balance(conn, int(user_id))
            rows = conn.execute(select(wallet_ledger).where(
                wallet_ledger.c.user_id == int(user_id)
            ).order_by(wallet_ledger.c.id.desc()).limit(
                max(1, min(int(limit), 100))
            )).mappings().all()
        return {
            "balance_cents": balance_value,
            "balance": money(balance_value),
            "entries": [{**dict(row), "amount": money(row["amount_cents"])} for row in rows],
        }

    def catalog(self):
        with self.engine.connect() as conn:
            stock_count = select(func.count(inventory.c.id)).where(and_(inventory.c.product_id == products.c.id, inventory.c.sold_order_id.is_(None))).scalar_subquery()
            rows = conn.execute(select(products, stock_count.label("stock")).where(products.c.published.is_(True)).order_by(products.c.category, products.c.name)).mappings()
            return [{**dict(row), "price": money(row["price_cents"]), "stock": int(row["stock"])} for row in rows]

    def storefront_catalog(self):
        """Show every product; drafts remain requestable but not purchasable."""
        with self.engine.connect() as conn:
            stock_count = select(func.count(inventory.c.id)).where(and_(inventory.c.product_id == products.c.id, inventory.c.sold_order_id.is_(None))).scalar_subquery()
            rows = conn.execute(
                select(products, product_display, stock_count.label("stock"))
                .select_from(products.outerjoin(
                    product_display, product_display.c.product_id == products.c.id
                ))
                .order_by(
                    product_display.c.featured.desc(),
                    product_display.c.display_order,
                    products.c.name,
                )
            ).mappings()
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
                item["image_key"] = item.get("image_key") or product_image_key(
                    item["name"], item.get("legacy_shopier_id")
                )
                item["image_url"] = f"/static/{item['image_key']}"
                item["featured"] = bool(item.get("featured"))
                item["request_enabled"] = bool(
                    item.get("request_enabled", True) and not item["available"]
                )
                item["action"] = "buy" if item["available"] else (
                    "request" if item["request_enabled"] else "unavailable"
                )
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
        result = self.checkout(user_id, [{
            "product_id": product_id,
            "quantity": quantity,
        }])
        return result["orders"][0]

    def checkout(self, user_id, items):
        """Atomically buy a cart; one failure rolls the whole cart back."""
        if not isinstance(items, list) or not items or len(items) > 20:
            raise ValueError("Sepette 1-20 ürün olmalı")
        combined = {}
        for item in items:
            try:
                product_id = int(item.get("product_id"))
                quantity = int(item.get("quantity", 1))
            except (AttributeError, TypeError, ValueError):
                raise ValueError("Sepet ürünü geçersiz")
            if quantity < 1 or quantity > 10:
                raise ValueError("Ürün adedi 1-10 arasında olmalı")
            combined[product_id] = combined.get(product_id, 0) + quantity
            if combined[product_id] > 10:
                raise ValueError("Bir üründen en fazla 10 adet alınabilir")

        now = utcnow()
        with self.engine.begin() as conn:
            customer = conn.execute(
                select(users).where(users.c.id == user_id).with_for_update()
            ).mappings().one()
            if customer["status"] != "active":
                raise ValueError("Hesap incelemede; destek ekibiyle iletişime geçin")

            prepared = []
            cart_total = 0
            for product_id in sorted(combined):
                quantity = combined[product_id]
                product = conn.execute(
                    select(products).where(products.c.id == product_id).with_for_update()
                ).mappings().first()
                if not product or not product["published"]:
                    raise ValueError("Sepette satışta olmayan ürün var")
                total = int(product["price_cents"]) * quantity
                delivery = product["delivery_type"]
                if delivery == "automatic":
                    units = conn.execute(
                        select(inventory).where(and_(
                            inventory.c.product_id == product_id,
                            inventory.c.sold_order_id.is_(None),
                        )).limit(quantity).with_for_update(skip_locked=True)
                    ).mappings().all()
                    if len(units) != quantity:
                        raise ValueError(
                            f"Stok tükendi: {clean_storefront_text(product['name'])}"
                        )
                else:
                    units = []
                prepared.append((product, quantity, total, units))
                cart_total += total

            if self.balance(conn, user_id) < cart_total:
                raise ValueError("Yetersiz bakiye")

            created_orders = []
            for product, quantity, total, units in prepared:
                delivery = product["delivery_type"]
                deadline = None if delivery == "automatic" else now + timedelta(hours=24)
                order_id = conn.execute(insert(orders).values(
                    user_id=user_id,
                    product_id=product["id"],
                    quantity=quantity,
                    total_cents=total,
                    status="delivered" if delivery == "automatic" else "manual_pending",
                    delivery_type=delivery,
                    deadline_at=deadline,
                    created_at=now,
                    completed_at=now if delivery == "automatic" else None,
                ).returning(orders.c.id)).scalar_one()
                conn.execute(insert(wallet_ledger).values(
                    user_id=user_id,
                    amount_cents=-total,
                    entry_type="purchase",
                    reference_type="order",
                    reference_id=str(order_id),
                    created_at=now,
                ))
                delivered = []
                for unit in units:
                    conn.execute(update(inventory).where(
                        inventory.c.id == unit["id"]
                    ).values(sold_order_id=order_id))
                    delivered.append(self.decrypt_stock(
                        product["id"], unit["nonce"], unit["ciphertext"]
                    ))
                created_orders.append({
                    "order_id": order_id,
                    "product_id": product["id"],
                    "product_name": clean_storefront_text(product["name"]),
                    "quantity": quantity,
                    "total_cents": total,
                    "total": money(total),
                    "status": "delivered" if delivery == "automatic" else "manual_pending",
                    "delivery": delivered,
                    "deadline": deadline.isoformat() if deadline else None,
                })
            return {
                "orders": created_orders,
                "total_cents": cart_total,
                "total": money(cart_total),
            }

    def user_summary(self, user_id):
        with self.engine.connect() as conn:
            user = conn.execute(select(users).where(users.c.id == int(user_id))).mappings().first()
            if not user:
                raise ValueError("Kullanıcı bulunamadı")
            return {
                **dict(user),
                "balance_cents": self.balance(conn, user["id"]),
                "balance": money(self.balance(conn, user["id"])),
                "referral_code": referral_code_for_telegram_id(user["telegram_id"]),
            }

    def order_history(self, user_id, limit=100):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    orders,
                    products.c.name.label("product_name"),
                    products.c.guide.label("product_guide"),
                ).join(products, products.c.id == orders.c.product_id)
                .where(orders.c.user_id == int(user_id))
                .order_by(orders.c.id.desc())
                .limit(max(1, min(int(limit), 100)))
            ).mappings().all()
            result = []
            for row in rows:
                item = dict(row)
                item["product_name"] = clean_storefront_text(item["product_name"])
                item["product_guide"] = clean_storefront_text(item.get("product_guide"))
                item["total"] = money(item["total_cents"])
                item["delivery"] = []
                if item["status"] == "delivered" and item["delivery_type"] == "automatic":
                    units = conn.execute(select(inventory).where(
                        inventory.c.sold_order_id == item["id"]
                    )).mappings().all()
                    item["delivery"] = [
                        self.decrypt_stock(item["product_id"], unit["nonce"], unit["ciphertext"])
                        for unit in units
                    ]
                result.append(item)
            return result

    def create_ticket(self, user_id, ticket_type, message, *, product_id=None,
                      order_id=None, subject=None):
        ticket_type = str(ticket_type or "support").strip().lower()
        if ticket_type not in {"support", "request", "refund"}:
            raise ValueError("Talep tipi geçersiz")
        message = str(message or "").strip()
        if len(message) < 3 or len(message) > 2000:
            raise ValueError("Mesaj 3-2000 karakter olmalı")
        now = utcnow()
        subject = str(subject or {
            "support": "Destek talebi",
            "request": "Ürün talebi",
            "refund": "İade talebi",
        }[ticket_type])[:220]
        with self.engine.begin() as conn:
            if product_id and not conn.execute(select(products.c.id).where(
                products.c.id == int(product_id)
            )).first():
                raise ValueError("Ürün bulunamadı")
            if order_id:
                order = conn.execute(select(orders).where(and_(
                    orders.c.id == int(order_id), orders.c.user_id == int(user_id)
                ))).first()
                if not order:
                    raise ValueError("Sipariş bulunamadı")
            ticket_id = conn.execute(insert(tickets).values(
                user_id=int(user_id),
                ticket_type=ticket_type,
                product_id=int(product_id) if product_id else None,
                order_id=int(order_id) if order_id else None,
                subject=subject,
                message=message,
                status="open",
                admin_reply=None,
                created_at=now,
                updated_at=now,
            ).returning(tickets.c.id)).scalar_one()
        return {"id": ticket_id, "status": "open", "subject": subject}

    def list_tickets(self, user_id=None, limit=100):
        query = select(
            tickets,
            users.c.telegram_id,
            users.c.username,
            users.c.display_name,
            products.c.name.label("product_name"),
        ).select_from(
            tickets.join(users, users.c.id == tickets.c.user_id).outerjoin(
                products, products.c.id == tickets.c.product_id
            )
        )
        if user_id is not None:
            query = query.where(tickets.c.user_id == int(user_id))
        query = query.order_by(tickets.c.id.desc()).limit(max(1, min(int(limit), 500)))
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query).mappings().all()]

    def update_ticket(self, ticket_id, *, status=None, admin_reply=None, admin_id=None):
        values = {"updated_at": utcnow()}
        if status is not None:
            if status not in {"open", "waiting_customer", "resolved", "rejected"}:
                raise ValueError("Talep durumu geçersiz")
            values["status"] = status
        if admin_reply is not None:
            values["admin_reply"] = str(admin_reply).strip()[:4000]
        with self.engine.begin() as conn:
            if not conn.execute(select(tickets.c.id).where(
                tickets.c.id == int(ticket_id)
            )).first():
                raise ValueError("Talep bulunamadı")
            conn.execute(update(tickets).where(tickets.c.id == int(ticket_id)).values(**values))
            conn.execute(insert(audit_log).values(
                admin_id=admin_id,
                action="ticket_update",
                target=str(ticket_id),
                detail=json.dumps(values, ensure_ascii=False, default=str),
                created_at=utcnow(),
            ))
        return {"ok": True}

    def referral_profile(self, user_id):
        with self.engine.connect() as conn:
            user = conn.execute(select(users).where(users.c.id == int(user_id))).mappings().first()
            if not user:
                raise ValueError("Kullanıcı bulunamadı")
            count = conn.execute(select(func.count()).select_from(referrals).where(
                referrals.c.referrer_user_id == int(user_id)
            )).scalar_one()
        return {
            "code": referral_code_for_telegram_id(user["telegram_id"]),
            "count": int(count),
            "rewards_enabled": False,
        }

    def apply_referral_code(self, referred_user_id, code):
        code = str(code or "").strip().upper()
        if not code:
            return False
        with self.engine.begin() as conn:
            referred = conn.execute(select(users).where(
                users.c.id == int(referred_user_id)
            )).mappings().first()
            if not referred:
                return False
            candidates = conn.execute(select(users.c.id, users.c.telegram_id)).all()
            referrer_id = next((row.id for row in candidates
                                if referral_code_for_telegram_id(row.telegram_id) == code), None)
            if not referrer_id or referrer_id == int(referred_user_id):
                return False
            try:
                with conn.begin_nested():
                    conn.execute(insert(referrals).values(
                        referrer_user_id=referrer_id,
                        referred_user_id=int(referred_user_id),
                        created_at=utcnow(),
                    ))
            except IntegrityError:
                return False
        return True

    def active_draws(self, user_id=None):
        now = utcnow()
        with self.engine.connect() as conn:
            rows = conn.execute(select(draws).where(and_(
                draws.c.status == "active",
                (draws.c.ends_at.is_(None) | (draws.c.ends_at > now)),
            )).order_by(draws.c.id.desc())).mappings().all()
            entered = set()
            if user_id is not None:
                entered = {row[0] for row in conn.execute(select(
                    draw_entries.c.draw_id
                ).where(draw_entries.c.user_id == int(user_id)))}
        return [{**dict(row), "entered": row["id"] in entered} for row in rows]

    def enter_draw(self, user_id, draw_id):
        with self.engine.begin() as conn:
            draw = conn.execute(select(draws).where(draws.c.id == int(draw_id)).with_for_update()).mappings().first()
            ends_at = draw["ends_at"] if draw else None
            if ends_at is not None and ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            if not draw or draw["status"] != "active" or (ends_at and ends_at <= utcnow()):
                raise ValueError("Çekiliş aktif değil")
            try:
                with conn.begin_nested():
                    conn.execute(insert(draw_entries).values(
                        draw_id=int(draw_id), user_id=int(user_id), created_at=utcnow()
                    ))
            except IntegrityError:
                return {"ok": True, "already_entered": True}
        return {"ok": True, "already_entered": False}

    def get_language(self, user_id):
        with self.engine.connect() as conn:
            return conn.execute(select(user_preferences.c.language).where(
                user_preferences.c.user_id == int(user_id)
            )).scalar_one_or_none() or "tr"

    def set_language(self, user_id, language):
        language = str(language or "tr").lower()
        if language not in {"tr", "en"}:
            raise ValueError("Dil desteklenmiyor")
        with self.engine.begin() as conn:
            current = conn.execute(select(user_preferences.c.user_id).where(
                user_preferences.c.user_id == int(user_id)
            )).first()
            if current:
                conn.execute(update(user_preferences).where(
                    user_preferences.c.user_id == int(user_id)
                ).values(language=language, updated_at=utcnow()))
            else:
                conn.execute(insert(user_preferences).values(
                    user_id=int(user_id), language=language, updated_at=utcnow()
                ))
        return language

    def _shopier_api(self, path, method="GET", payload=None):
        """Call Shopier without ever returning credential/provider internals to users."""
        token = os.environ.get("SHOPIER_LISANSARENA_ACCESS_TOKEN", "").strip()
        if not token:
            raise StoreUnavailable("Shopier ödeme bağlantısı yapılandırılmadı")
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        api_request = urllib.request.Request(
            f"{SHOPIER_API}{path}", data=data, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "LisansArena-Store/1.0",
            },
        )
        try:
            with urllib.request.urlopen(api_request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"Shopier API {exc.code}: {detail}") from exc
        return json.loads(raw.decode("utf-8")) if raw else {}

    @staticmethod
    def _shopier_rows(payload):
        if isinstance(payload, list):
            return payload
        return payload.get("data") or payload.get("products") or []

    def _recover_custom_listing(self, code):
        """Find a listing after an ambiguous create timeout; never POST again."""
        try:
            rows = self._shopier_rows(self._shopier_api(
                "/products?limit=50&customListing=true"
            ))
        except Exception:
            return None
        for product in rows:
            title = str(product.get("title") or "")
            product_id = str(product.get("id") or "")
            if product_id and code in title:
                return product_id
        return None

    def _close_shopier_listing(self, product_id):
        self._shopier_api(f"/products/{urllib.parse.quote(str(product_id), safe='')}", "PUT", {
            "stockQuantity": 0,
        })

    @staticmethod
    def _customer_first_name(display_name):
        first_name = re.sub(r"[\r\n\t]+", " ", str(display_name or "")).strip().split(" ", 1)[0]
        return first_name[:40] or "Telegram müşterisi"

    def _insert_custom_topup_intent(self, user_id, amount_cents):
        now = utcnow()
        expires_at = now + timedelta(hours=1)
        with self.engine.begin() as conn:
            customer = conn.execute(select(users).where(users.c.id == int(user_id))).mappings().first()
            if not customer:
                raise ValueError("Kullanıcı bulunamadı")
            for _ in range(5):
                code = f"LA-{secrets.token_hex(3).upper()}"
                try:
                    conn.execute(insert(topup_intents).values(
                        code=code, user_id=int(user_id), amount_cents=amount_cents,
                        status="creating", topup_mode="custom", listing_state="creating",
                        expires_at=expires_at, created_at=now,
                    ))
                    return code, self._customer_first_name(customer["display_name"]), now, expires_at
                except IntegrityError:
                    continue
        raise StoreUnavailable("Özel ödeme kodu oluşturulamadı")

    def _create_custom_topup(self, user_id, amount_cents):
        if not CUSTOM_TOPUP_MIN_CENTS <= amount_cents <= CUSTOM_TOPUP_MAX_CENTS or amount_cents % 100:
            raise ValueError("Özel tutar 10 TL ile 50.000 TL arasında tam TL olmalı")
        code, first_name, now, expires_at = self._insert_custom_topup_intent(user_id, amount_cents)
        title = f"LisansArena Özel Bakiye — {first_name} — {code}"
        payload = {
            "title": title,
            "description": (
                f"{first_name} için {money(amount_cents)} LisansArena bakiye yüklemesi.\n"
                f"Destek kodu: {code}\n"
                "Bu ilan tek kullanımlıktır ve 1 saat geçerlidir. Sipariş notuna kod yazmak zorunlu değildir."
            ),
            "type": "digital",
            # Shopier's schema requires the field, but an empty list keeps
            # the customer-specific listing intentionally coverless.
            "media": [],
            "priceData": {
                "currency": "TRY", "price": f"{Decimal(amount_cents) / 100:.2f}",
                "discount": False, "discountedPrice": f"{Decimal(amount_cents) / 100:.2f}",
                "shippingPrice": "0.00",
            },
            "stockQuantity": 1,
            "shippingPayer": "sellerPays",
            "customListing": True,
            "customNote": f"İsteğe bağlı destek kodu: {code}",
        }
        product_id = ""
        try:
            response = self._shopier_api("/products", "POST", payload)
            product_id = str(response.get("id") or "")
            if not product_id:
                raise RuntimeError("Shopier ürün kimliği döndürmedi")
        except Exception as exc:
            product_id = self._recover_custom_listing(code) or ""
            if not product_id:
                with self.engine.begin() as conn:
                    conn.execute(update(topup_intents).where(topup_intents.c.code == code).values(
                        status="creation_failed", listing_state="unknown",
                    ))
                raise StoreUnavailable("Özel ödeme ilanı şu an oluşturulamadı; lütfen tekrar deneyin") from exc

        try:
            with self.engine.begin() as conn:
                conn.execute(update(topup_intents).where(topup_intents.c.code == code).values(
                    shopier_product_id=product_id, status="pending", listing_state="open",
                ))
        except Exception as exc:
            try:
                self._close_shopier_listing(product_id)
            except Exception:
                pass
            raise StoreUnavailable("Özel ödeme ilanı güvenle kaydedilemedi; lütfen tekrar deneyin") from exc
        return {
            "code": code, "amount": money(amount_cents),
            "expires_at": expires_at.isoformat(), "payment_ready": True,
            "shopier_product_id": product_id,
            "shopier_url": f"https://www.shopier.com/lisansarena/{product_id}",
            "mode": "custom", "note_required": False,
        }

    def create_topup(self, user_id, amount_cents, mode="package"):
        try:
            amount_cents = int(amount_cents)
        except (TypeError, ValueError) as exc:
            raise ValueError("Geçersiz bakiye tutarı") from exc
        mode = str(mode or "package").strip().lower()
        if mode == "custom":
            return self._create_custom_topup(user_id, amount_cents)
        if mode != "package" or amount_cents not in TOPUP_AMOUNTS:
            raise ValueError("Geçersiz bakiye paketi")
        package_map = json.loads(os.environ.get("LISANSARENA_SHOPIER_TOPUP_PRODUCTS", "{}") or "{}")
        mapping_path = os.path.join(os.path.dirname(__file__), "lisansarena_topup_products.json")
        if not package_map and os.path.exists(mapping_path):
            with open(mapping_path, "r", encoding="utf-8") as handle:
                package_map = json.load(handle)
        product_id = str(package_map.get(str(amount_cents // 100)) or "")
        if not product_id:
            raise ValueError("Seçilen bakiye paketi ödeme ilanına bağlı değil")
        code = f"LA-{secrets.token_hex(3).upper()}"
        now = utcnow()
        with self.engine.begin() as conn:
            conn.execute(insert(topup_intents).values(
                code=code, user_id=user_id, amount_cents=amount_cents,
                shopier_product_id=product_id or None, status="pending",
                topup_mode="package", listing_state="not_applicable",
                expires_at=now + timedelta(hours=24), created_at=now,
            ))
        return {
            "code": code, "amount": money(amount_cents),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "payment_ready": True,
            "shopier_product_id": product_id,
            "shopier_url": f"https://www.shopier.com/lisansarena/{product_id}",
            "mode": "package", "note_required": True,
        }

    def inspect_topup_code(self, code):
        """Return a read-only reconciliation snapshot for one LA top-up code."""
        code = str(code or "").strip().upper()
        if not re.fullmatch(r"LA-[A-F0-9]{6}", code):
            raise ValueError("Geçersiz bakiye kodu")
        with self.engine.connect() as conn:
            intent = conn.execute(select(topup_intents).where(
                topup_intents.c.code == code
            )).mappings().first()
            if not intent:
                return {"code": code, "found": False}

            user = conn.execute(select(users).where(
                users.c.id == intent["user_id"]
            )).mappings().first()
            ledger = conn.execute(select(wallet_ledger).where(
                wallet_ledger.c.user_id == intent["user_id"]
            ).order_by(wallet_ledger.c.id.asc())).mappings().all()
            order_rows = conn.execute(select(
                orders,
                products.c.name.label("product_name"),
            ).select_from(orders.join(products, products.c.id == orders.c.product_id)).where(
                orders.c.user_id == intent["user_id"]
            ).order_by(orders.c.id.asc())).mappings().all()
            shopier_rows = conn.execute(select(shopier_orders).where(
                shopier_orders.c.topup_code == code
            ).order_by(shopier_orders.c.id.asc())).mappings().all()
            review_rows = conn.execute(select(shopier_orders).where(
                shopier_orders.c.status == "manual_review"
            ).order_by(shopier_orders.c.id.asc())).mappings().all()

        def serialise_ledger(row):
            return {
                "id": row["id"],
                "amount_cents": row["amount_cents"],
                "entry_type": row["entry_type"],
                "reference_type": row["reference_type"],
                "reference_id": row["reference_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }

        def decode_shopier(row):
            payload = {}
            try:
                payload = json.loads(row["payload"] or "{}")
            except (TypeError, ValueError):
                pass
            note = str(payload.get("note") or payload.get("orderNote") or payload.get("buyerNote") or "")
            line_items = payload.get("lineItems") or payload.get("line_items") or payload.get("items") or []
            return {
                "order_number": row["order_number"],
                "status": row["status"],
                "amount_cents": row["amount_cents"],
                "note": note,
                "code_in_note": code in note.upper(),
                "line_items": line_items,
            }

        shopier = [decode_shopier(row) for row in shopier_rows]
        candidates = []
        for row in review_rows:
            item = decode_shopier(row)
            product_ids = {
                str(entry.get("productId") or entry.get("product_id") or entry.get("id") or "")
                for entry in item["line_items"] if isinstance(entry, dict)
            }
            if item["amount_cents"] == intent["amount_cents"] and str(intent["shopier_product_id"] or "") in product_ids:
                candidates.append(item)

        return {
            "code": code,
            "found": True,
            "intent": {
                "user_id": intent["user_id"],
                "telegram_id": user["telegram_id"] if user else None,
                "amount_cents": intent["amount_cents"],
                "shopier_product_id": intent["shopier_product_id"],
                "status": intent["status"],
                "topup_mode": intent["topup_mode"],
                "listing_state": intent["listing_state"],
                "closed_at": intent["closed_at"].isoformat() if intent["closed_at"] else None,
                "expires_at": intent["expires_at"].isoformat() if intent["expires_at"] else None,
            },
            "balance_cents": sum(int(row["amount_cents"] or 0) for row in ledger),
            "ledger": [serialise_ledger(row) for row in ledger],
            "orders": [dict(row) for row in order_rows],
            "shopier_orders": shopier,
            "manual_review_candidates": candidates,
        }

    def apply_manual_credit_once(self, user_id, amount_cents, reference_id, reason, admin_id):
        """Append one auditable manual credit; never updates/deletes the ledger."""
        amount_cents = int(amount_cents)
        if amount_cents <= 0:
            raise ValueError("Manuel kredi tutarı pozitif olmalı")
        reference_id = str(reference_id or "").strip()
        reason = str(reason or "").strip()
        if not reference_id or not reason:
            raise ValueError("Manuel kredi referansı ve gerekçesi zorunlu")
        now = utcnow()
        with self.engine.begin() as conn:
            user = conn.execute(select(users.c.id).where(users.c.id == int(user_id))).first()
            if not user:
                raise ValueError("Kullanıcı bulunamadı")
            existing = conn.execute(select(wallet_ledger).where(and_(
                wallet_ledger.c.entry_type == "manual_credit",
                wallet_ledger.c.reference_type == "admin_adjustment",
                wallet_ledger.c.reference_id == reference_id,
            ))).mappings().first()
            if existing:
                return {"applied": False, "duplicate": True, "ledger_id": existing["id"]}
            row_id = conn.execute(insert(wallet_ledger).values(
                user_id=int(user_id), amount_cents=amount_cents,
                entry_type="manual_credit", reference_type="admin_adjustment",
                reference_id=reference_id, created_at=now,
            ).returning(wallet_ledger.c.id)).scalar_one()
            conn.execute(insert(audit_log).values(
                admin_id=int(admin_id) if admin_id else None,
                action="manual_wallet_credit", target=str(user_id),
                detail=json.dumps({
                    "amount_cents": amount_cents,
                    "reference_id": reference_id,
                    "reason": reason,
                }, ensure_ascii=False), created_at=now,
            ))
        return {"applied": True, "duplicate": False, "ledger_id": row_id}

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
        custom_listings_to_close = []
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
                status = "manual_review"
                payload = json.loads(event["payload"])
                line_items = payload.get("lineItems") or payload.get("line_items") or payload.get("items") or []
                first_item = line_items[0] if isinstance(line_items, list) and line_items else {}
                received_product_id = str(first_item.get("productId") or first_item.get("product_id") or first_item.get("id") or "")
                try:
                    received_quantity = int(first_item.get("quantity", 1))
                except (TypeError, ValueError):
                    received_quantity = 0
                code_intent = None
                if event["topup_code"]:
                    code_intent = conn.execute(select(topup_intents).where(
                        topup_intents.c.code == event["topup_code"]
                    ).with_for_update()).mappings().first()
                product_intent = None
                if received_product_id:
                    product_intent = conn.execute(select(topup_intents).where(and_(
                        topup_intents.c.shopier_product_id == received_product_id,
                        topup_intents.c.topup_mode == "custom",
                    )).with_for_update()).mappings().first()
                # A custom listing is unique to one customer, so its product ID
                # is authoritative. A supplied but different LA code is a
                # deliberate mismatch and must go to review instead of credit.
                note_conflicts = bool(product_intent and code_intent and product_intent["id"] != code_intent["id"])
                intent = product_intent or code_intent
                expires_at = intent["expires_at"] if intent else None
                if expires_at is not None and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                product_matches = bool(
                    intent and intent["shopier_product_id"] and
                    received_product_id == str(intent["shopier_product_id"]) and
                    received_quantity == 1
                )
                code_required = bool(intent and intent["topup_mode"] != "custom")
                code_matches = bool(intent and event["topup_code"] == intent["code"])
                if (
                    intent and intent["status"] == "pending" and expires_at > utcnow() and
                    intent["amount_cents"] == event["amount_cents"] and product_matches and
                    not note_conflicts and (not code_required or code_matches)
                ):
                    try:
                        with conn.begin_nested():
                            conn.execute(insert(wallet_ledger).values(
                                user_id=intent["user_id"], amount_cents=event["amount_cents"],
                                entry_type="topup", reference_type="shopier_order",
                                reference_id=event["order_number"], created_at=utcnow(),
                            ))
                        intent_values = {"status": "completed"}
                        if intent["topup_mode"] == "custom":
                            intent_values["listing_state"] = "closing"
                            custom_listings_to_close.append(str(intent["shopier_product_id"]))
                        conn.execute(update(topup_intents).where(topup_intents.c.id == intent["id"]).values(**intent_values))
                        status = "credited"
                    except IntegrityError:
                        status = "duplicate"
                conn.execute(update(shopier_orders).where(shopier_orders.c.id == event["id"]).values(status=status, processed_at=utcnow()))
                processed += 1
        for product_id in custom_listings_to_close:
            self.close_due_custom_topups(product_ids={product_id})
        return processed

    def close_due_custom_topups(self, product_ids=None):
        """Close paid or expired one-use custom listings without deleting audit data."""
        now = utcnow()
        requested = {str(product_id) for product_id in (product_ids or set()) if product_id}
        with self.engine.begin() as conn:
            conditions = [topup_intents.c.topup_mode == "custom"]
            if requested:
                conditions.append(topup_intents.c.shopier_product_id.in_(requested))
                conditions.append(topup_intents.c.status.in_(("completed", "expired")))
                conditions.append(topup_intents.c.listing_state != "closed")
            else:
                conditions.append(
                    ((topup_intents.c.status == "pending") & (topup_intents.c.expires_at <= now)) |
                    ((topup_intents.c.status.in_(("completed", "expired"))) & (topup_intents.c.listing_state != "closed"))
                )
            rows = conn.execute(select(topup_intents).where(and_(*conditions)).with_for_update(skip_locked=True)).mappings().all()
            close_rows = []
            for row in rows:
                expires_at = row["expires_at"]
                if expires_at is not None and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if row["status"] == "pending" and expires_at <= now:
                    conn.execute(update(topup_intents).where(topup_intents.c.id == row["id"]).values(
                        status="expired", listing_state="closing", closed_at=now,
                    ))
                elif row["listing_state"] != "closed":
                    conn.execute(update(topup_intents).where(topup_intents.c.id == row["id"]).values(
                        listing_state="closing", closed_at=row["closed_at"] or now,
                    ))
                if row["shopier_product_id"]:
                    close_rows.append((row["id"], str(row["shopier_product_id"])))

        closed = 0
        for intent_id, product_id in close_rows:
            try:
                self._close_shopier_listing(product_id)
            except Exception:
                with self.engine.begin() as conn:
                    conn.execute(update(topup_intents).where(topup_intents.c.id == intent_id).values(
                        listing_state="close_failed"
                    ))
                continue
            with self.engine.begin() as conn:
                conn.execute(update(topup_intents).where(topup_intents.c.id == intent_id).values(
                    listing_state="closed", closed_at=now,
                ))
            closed += 1
        return closed

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


@la.get("/la/assets/logo")
def logo_asset():
    path = os.path.join(os.path.dirname(__file__), "static", "lisansarena_logo_v2.png")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "lisansarena_banner.jpeg")
    return send_file(path, max_age=86400)


@la.get("/api/la/health")
def store_health():
    try:
        store = get_store()
        with store.engine.connect() as conn:
            product_count = conn.execute(select(func.count()).select_from(products)).scalar_one()
        return jsonify({"ok": True, "database": "ready", "product_count": product_count})
    except StoreUnavailable:
        return jsonify({"ok": False, "database": "unavailable", "error": "Mağaza veritabanı hazır değil"}), 503
    except Exception:
        return jsonify({"ok": False, "database": "unavailable", "error": "Mağaza veritabanına ulaşılamıyor"}), 503


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
    start_param = str(payload.get("startParam") or "")
    if start_param.lower().startswith("ref_"):
        get_store().apply_referral_code(user_id, start_param[4:])
    referral_profile = get_store().referral_profile(user_id)
    return jsonify({
        "ok": True,
        "csrf": session["la_csrf"],
        "user": {
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "username": user.get("username", ""),
            "photo_url": user.get("photo_url", ""),
            "referral_code": referral_profile["code"],
            "referral_count": referral_profile["count"],
            "referrals_enabled": referral_profile["rewards_enabled"],
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


@la.post("/api/la/cart/checkout")
@customer_required
def api_cart_checkout():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().checkout(session["la_user_id"], data.get("items")))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.get("/api/la/wallet")
@customer_required
def api_wallet():
    return jsonify(get_store().wallet_history(session["la_user_id"]))


@la.post("/api/la/topups")
@customer_required
def api_topups():
    try:
        data = request.get_json(silent=True) or {}
        return jsonify(get_store().create_topup(
            session["la_user_id"], data.get("amount_cents"), data.get("mode", "package")
        ))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.get("/api/la/orders")
@customer_required
def api_orders():
    return jsonify({"orders": get_store().order_history(session["la_user_id"])})


@la.route("/api/la/tickets", methods=["GET", "POST"])
@customer_required
def api_tickets():
    store = get_store()
    if request.method == "GET":
        return jsonify({"tickets": store.list_tickets(session["la_user_id"])})
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(store.create_ticket(
            session["la_user_id"],
            data.get("ticket_type"),
            data.get("message"),
            product_id=data.get("product_id"),
            order_id=data.get("order_id"),
            subject=data.get("subject"),
        )), 201
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.get("/api/la/referral")
@customer_required
def api_referral():
    return jsonify(get_store().referral_profile(session["la_user_id"]))


@la.get("/api/la/draws")
@customer_required
def api_draws():
    return jsonify({"draws": get_store().active_draws(session["la_user_id"])})


@la.post("/api/la/draws/<int:draw_id>/enter")
@customer_required
def api_draw_enter(draw_id):
    try:
        return jsonify(get_store().enter_draw(session["la_user_id"], draw_id))
    except ValueError as exc:
        return _json_error(exc)


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
        store = get_store()
        order_number = store.ingest_webhook(payload, request.headers.get("Shopier-Webhook-Id"))
        processed = store.process_webhooks()
        return jsonify({"accepted": True, "order_number": order_number, "processed": processed}), 202
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
            if PasswordHasher is not None:
                PasswordHasher().verify(row["password_hash"], password)
            elif not check_password_hash(row["password_hash"], password):
                raise ValueError("Giriş reddedildi")
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
        product_rows = conn.execute(
            select(products, product_display).select_from(products.outerjoin(
                product_display, product_display.c.product_id == products.c.id
            )).order_by(product_display.c.display_order, products.id)
        ).mappings().all()
        pending = conn.execute(select(orders, products.c.name.label("product_name")).join(products).where(orders.c.status == "manual_pending").order_by(orders.c.deadline_at)).mappings().all()
        review = conn.execute(select(shopier_orders).where(shopier_orders.c.status == "manual_review").order_by(shopier_orders.c.id.desc())).mappings().all()
    return jsonify({
        "products": [dict(row) for row in product_rows],
        "manual_orders": [dict(row) for row in pending],
        "topup_review": [dict(row) for row in review],
        "tickets": store.list_tickets(),
        "draws": store.active_draws(),
    })


@la.get("/api/la/admin/reconcile/<code>")
@admin_required
def admin_reconcile_topup(code):
    try:
        return jsonify(get_store().inspect_topup_code(code))
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.post("/api/la/admin/reconcile/<code>/manual-credit-50")
@admin_required
def admin_manual_credit_50(code):
    """Apply the requested 50 TL correction once, after code verification."""
    store = get_store()
    try:
        snapshot = store.inspect_topup_code(code)
        if not snapshot.get("found"):
            return _json_error("Bakiye kodu bulunamadı", 404)
        normalized = snapshot["code"]
        result = store.apply_manual_credit_once(
            snapshot["intent"]["user_id"], 5000,
            f"{normalized}:manual-50tl",
            "LA kodu için doğrulama sonrası eksik 50 TL manuel bakiye düzeltmesi",
            session.get("la_admin_id"),
        )
        return jsonify({"code": normalized, "result": result, "snapshot": store.inspect_topup_code(normalized)})
    except (ValueError, StoreUnavailable) as exc:
        return _json_error(exc, 503 if isinstance(exc, StoreUnavailable) else 400)


@la.post("/api/la/admin/products/<int:product_id>")
@admin_required
def admin_product(product_id):
    data = request.get_json(silent=True) or {}
    allowed = {key: data[key] for key in ("name", "description", "category", "price_cents", "cost_cents", "delivery_type", "guide", "published") if key in data}
    display_allowed = {key: data[key] for key in (
        "image_key", "featured", "display_order", "request_enabled"
    ) if key in data}
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
        if display_allowed:
            display_allowed["image_key"] = os.path.basename(str(
                display_allowed.get("image_key") or product_image_key(merged["name"])
            ))
            display_allowed["updated_at"] = utcnow()
            current_display = conn.execute(select(product_display.c.product_id).where(
                product_display.c.product_id == product_id
            )).first()
            if current_display:
                conn.execute(update(product_display).where(
                    product_display.c.product_id == product_id
                ).values(**display_allowed))
            else:
                defaults = {
                    "product_id": product_id,
                    "image_key": product_image_key(merged["name"]),
                    "featured": False,
                    "display_order": 999,
                    "request_enabled": True,
                    "updated_at": utcnow(),
                }
                defaults.update(display_allowed)
                conn.execute(insert(product_display).values(**defaults))
        conn.execute(insert(audit_log).values(admin_id=session["la_admin_id"], action="product_update", target=str(product_id), detail=json.dumps({**allowed, **display_allowed}, ensure_ascii=False, default=str), created_at=utcnow()))
    return jsonify({"ok": True})


@la.post("/api/la/admin/tickets/<int:ticket_id>")
@admin_required
def admin_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().update_ticket(
            ticket_id,
            status=data.get("status"),
            admin_reply=data.get("admin_reply"),
            admin_id=session["la_admin_id"],
        ))
    except ValueError as exc:
        return _json_error(exc)


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
                store.close_due_custom_topups()
                store.expire_manual_orders()
            except Exception as exc:
                print(f"[LisansArena Store] worker: {type(exc).__name__}: {exc}")
            time.sleep(30)

    threading.Thread(target=loop, name="lisansarena-store-worker", daemon=True).start()
