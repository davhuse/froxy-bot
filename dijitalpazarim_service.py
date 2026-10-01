# -*- coding: utf-8 -*-
"""
Dijital Pazarım — Dedicated Independent Service
Runs exclusively for Dijital Pazarım:
- Serves Dijital Pazarım Canlı Servis Paneli on root '/' with Start/Stop and Broadcast controls
- Serves Dijital Pazarım Mini App on '/dp' and '/app' with TR | EN language options
- Telegram Bot (@DijitalPazarimBot) runner with WebApp menu button to '/dp'
- Telethon Ad Sender loop for +18595173039 (@DijitalPazarimm)
- Real-time endpoints: /api/start, /api/stop, /api/broadcast, /api/logs, /api/status
Zero dependency on KeyVadi, LisansArena, or Froxy.
"""

from __future__ import annotations
import os
import sys
import json
import collections
from datetime import datetime, timezone
import threading
import asyncio
import time
import random
import requests
from pathlib import Path
from flask import Flask, send_from_directory, render_template, jsonify, request

sys.stdout.reconfigure(encoding='utf-8')

# Ensure Firebase credentials compatibility
if not os.environ.get("FIREBASE_API_KEY"):
    os.environ["FIREBASE_API_KEY"] = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
import firestore_helper

BASE_DIR = Path(__file__).resolve().parent
MINIAPP_DIR = BASE_DIR / "miniapp_dijitalpazarim"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
MESSAGES_DIR = BASE_DIR / "messages"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)

BOT_TOKEN = os.environ.get("DIJITALPAZARIM_BOT_TOKEN", "8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://dijital-pazarim-service-production.up.railway.app").rstrip("/")
MINIAPP_URL = f"{PUBLIC_BASE_URL}/dp"

# In-memory Live Log Buffer & Operational State
LOG_BUFFER = collections.deque(maxlen=250)
AD_RUNNING = True
AD_INTERVAL_SECONDS = 3600
TELETHON_CLIENT = None
TELETHON_LOOP = None
TOTAL_ADS_SENT = 0
LAST_CYCLE_TIME = None
JOINED_GROUPS_COUNT = 0
LAST_BLAST_HEARTBEAT = time.time()

t_bot: threading.Thread | None = None
t_acc: threading.Thread | None = None

_BOT_WORKER_LOCK = threading.Lock()
_IS_BOT_WORKER_RUNNING = False
BOT_HEALTH_STATE = {"status": "starting", "last_ok": None, "last_conflict": None, "conflict_count": 0}

WATCHDOG_STATS = {
    "status": "active",
    "last_check": None,
    "bot_restarts": 0,
    "telethon_restarts": 0,
    "firestore_connected": False,
    "blast_heartbeat_age": 0
}

# ─────────────────────────────────────────────────────────────
# 0. FIRESTORE PERSISTENT CHECKPOINT & DUPLICATE PROTECTION
# ─────────────────────────────────────────────────────────────

def is_recent_message_from_account(message, account_id, now=None, window_seconds=3000) -> bool:
    """Telegram sohbet geçmişinde bu hesabın son mesajını doğrular (deploy/restart spam koruması)."""
    if not message or getattr(message, "empty", False):
        return False
    if getattr(message, "sender_id", None) != int(account_id or 0):
        return False
    message_date = getattr(message, "date", None)
    if message_date is None:
        return False
    if getattr(message_date, "tzinfo", None) is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    current = datetime.now(timezone.utc) if now is None else now
    if getattr(current, "tzinfo", None) is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current - message_date).total_seconds()
    return 0 <= age <= max(1, int(window_seconds))

CHECKPOINT_DOC_ID = "dijitalpazarim_blast_checkpoint"
LOCAL_CHECKPOINT_FILE = BASE_DIR / "dijitalpazarim_blast_checkpoint.json"

class DijitalPazarimCheckpoint:
    """Persist Dijital Pazarim blast state across deploys and container restarts."""

    def __init__(self):
        self._lock = threading.RLock()
        self.state = self.load()

    def _empty_state(self) -> dict:
        return {
            "version": 1,
            "status": "idle",
            "last_blast_completed_at": 0.0,
            "next_blast_due_at": 0.0,
            "last_blast_started_at": 0.0,
            "cycle_count": 0,
            "total_sent": 0,
            "last_group_sends": {},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def load(self) -> dict:
        with self._lock:
            state = None
            # 1. Firestore read
            try:
                if firestore_helper.remote_credentials_configured():
                    doc = firestore_helper.get_document(CHECKPOINT_DOC_ID)
                    if doc:
                        raw = doc.get("payload")
                        if raw:
                            data = json.loads(raw) if isinstance(raw, str) else raw
                            if isinstance(data, dict):
                                state = data
                        elif "next_blast_due_at" in doc:
                            state = {
                                "next_blast_due_at": float(doc.get("next_blast_due_at", 0)),
                                "last_blast_completed_at": float(doc.get("last_blast_completed_at", 0)),
                                "status": str(doc.get("status", "idle")),
                                "updated_at": str(doc.get("updated_at", ""))
                            }
            except Exception as e:
                sys_log(f"[Checkpoint] Firestore okuma uyarısı: {e}")

            # 2. Local JSON read
            if not state and LOCAL_CHECKPOINT_FILE.exists():
                try:
                    data = json.loads(LOCAL_CHECKPOINT_FILE.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        state = data
                except Exception as e:
                    sys_log(f"[Checkpoint] Yerel checkpoint okuma uyarısı: {e}")

            if not state:
                state = self._empty_state()

            empty = self._empty_state()
            for k, v in empty.items():
                state.setdefault(k, v)

            return state

    def save(self):
        with self._lock:
            self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
            # 1. Local disk
            try:
                LOCAL_CHECKPOINT_FILE.write_text(
                    json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception as e:
                sys_log(f"[Checkpoint] Yerel dosya yazma hatası: {e}")

            # 2. Firestore
            try:
                if firestore_helper.remote_credentials_configured():
                    firestore_helper.set_document(CHECKPOINT_DOC_ID, {
                        "payload": json.dumps(self.state, ensure_ascii=False),
                        "next_blast_due_at": float(self.state.get("next_blast_due_at", 0.0) or 0.0),
                        "last_blast_completed_at": float(self.state.get("last_blast_completed_at", 0.0) or 0.0),
                        "status": str(self.state.get("status", "idle")),
                        "updated_at": self.state["updated_at"]
                    })
            except Exception as e:
                sys_log(f"[Checkpoint] Firestore kaydetme hatası: {e}")

    def get_remaining_seconds(self) -> float:
        with self._lock:
            due_at = float(self.state.get("next_blast_due_at", 0.0) or 0.0)
            now = time.time()
            if due_at > now:
                return due_at - now
            return 0.0

    def record_blast_started(self):
        with self._lock:
            self.state["status"] = "blasting"
            self.state["last_blast_started_at"] = time.time()
            self.save()

    def record_group_send(self, group_key: str):
        with self._lock:
            now = time.time()
            if "last_group_sends" not in self.state or not isinstance(self.state["last_group_sends"], dict):
                self.state["last_group_sends"] = {}
            self.state["last_group_sends"][str(group_key).lower()] = now
            self.state["last_group_sends"] = {
                k: v for k, v in self.state["last_group_sends"].items()
                if now - v < 7200
            }
            self.state["total_sent"] = int(self.state.get("total_sent", 0)) + 1
            self.save()

    def was_group_sent_recently(self, group_key: str, window_seconds: int = 3000) -> bool:
        with self._lock:
            sends = self.state.get("last_group_sends", {})
            if not isinstance(sends, dict):
                return False
            last_time = sends.get(str(group_key).lower(), 0.0)
            if not last_time:
                return False
            return (time.time() - float(last_time)) < window_seconds

    def record_blast_completed(self, interval_seconds: int = 3600):
        with self._lock:
            now = time.time()
            self.state["status"] = "waiting"
            self.state["last_blast_completed_at"] = now
            self.state["next_blast_due_at"] = now + interval_seconds
            self.state["cycle_count"] = int(self.state.get("cycle_count", 0)) + 1
            self.save()

CHECKPOINT = DijitalPazarimCheckpoint()

def load_target_groups() -> list[str]:
    """Hedef ticaret ve kupon gruplarini gruplar.txt dosyasindan okur."""
    g_file = BASE_DIR / "gruplar.txt"
    if not g_file.exists():
        return []
    targets = []
    for line in g_file.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("@")
        if line and not line.startswith("#"):
            targets.append(line)
    return targets

def load_blacklist() -> set[str]:
    """Kara listedeki gruplari blacklist.txt dosyasindan okur."""
    b_file = BASE_DIR / "blacklist.txt"
    if not b_file.exists():
        return set()
    b_set = set()
    for line in b_file.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("@").lower()
        if line and not line.startswith("#"):
            b_set.add(line)
    return b_set

def sys_log(message: str):
    """Outputs to stdout and records in log buffer."""
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {message}"
    print(formatted, flush=True)
    LOG_BUFFER.append(formatted)

sys_log("Dijital Pazarım Bağımsız Servisi başlatıldı.")

# ─────────────────────────────────────────────────────────────
# 1. WEB & CANLI SERVİS PANELİ / MINI APP / API ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def live_service_dashboard():
    """Dijital Pazarım Canlı Servis Paneli (Dashboard)."""
    return render_template("dijitalpazarim_dashboard.html")

@app.route("/dp")
@app.route("/dp/")
@app.route("/app")
@app.route("/app/")
def miniapp_store():
    """Dijital Pazarım Mini App Mağazası."""
    return send_from_directory(str(MINIAPP_DIR), "index.html")

@app.route("/products_db.json")
@app.route("/dp/products_db.json")
@app.route("/app/products_db.json")
def get_products():
    prod_file = MINIAPP_DIR / "products_db.json"
    if prod_file.exists():
        return send_from_directory(str(MINIAPP_DIR), "products_db.json", mimetype="application/json")
    return jsonify([]), 404

@app.route("/assets/<path:filepath>")
@app.route("/dp/assets/<path:filepath>")
@app.route("/app/assets/<path:filepath>")
def serve_assets(filepath):
    return send_from_directory(str(MINIAPP_DIR / "assets"), filepath)

@app.route("/api/logs")
def get_live_logs():
    return jsonify({"logs": list(LOG_BUFFER)})

@app.route("/api/status")
@app.route("/health")
def health_status():
    prod_file = MINIAPP_DIR / "products_db.json"
    prod_count = 0
    if prod_file.exists():
        try:
            prod_count = len(json.loads(prod_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    targets = load_target_groups()

    remaining_sec = int(CHECKPOINT.get_remaining_seconds())
    due_ts = float(CHECKPOINT.state.get("next_blast_due_at", 0.0) or 0.0)
    due_str = datetime.fromtimestamp(due_ts).strftime("%H:%M:%S") if due_ts > 0 else "Hazır"
    last_comp_ts = float(CHECKPOINT.state.get("last_blast_completed_at", 0.0) or 0.0)
    last_comp_str = datetime.fromtimestamp(last_comp_ts).strftime("%H:%M:%S") if last_comp_ts > 0 else (LAST_CYCLE_TIME or "Henüz tamamlanmadı")

    return jsonify({
        "status": "online",
        "ad_running": AD_RUNNING,
        "ad_interval_minutes": AD_INTERVAL_SECONDS // 60,
        "total_ads_sent": TOTAL_ADS_SENT or CHECKPOINT.state.get("total_sent", 0),
        "last_cycle": last_comp_str,
        "next_blast_due_at": due_str,
        "remaining_seconds": remaining_sec,
        "blast_status": CHECKPOINT.state.get("status", "idle"),
        "firestore_connected": firestore_helper.remote_credentials_configured(),
        "duplicate_guard": "active",
        "brand": "Dijital Pazarım",
        "bot": "@DijitalPazarimBot",
        "ad_account": "+18595173039 (@DijitalPazarimm)",
        "domain": PUBLIC_BASE_URL,
        "miniapp_url": MINIAPP_URL,
        "active_products": prod_count,
        "target_groups_count": len(targets),
        "joined_groups_count": JOINED_GROUPS_COUNT,
        "watchdog": {
            "status": WATCHDOG_STATS.get("status", "active"),
            "last_check": WATCHDOG_STATS.get("last_check"),
            "bot_alive": BOT_HEALTH_STATE.get("status") == "online",
            "bot_health": BOT_HEALTH_STATE,
            "telethon_alive": t_acc.is_alive() if t_acc else False,
            "telethon_connected": bool(TELETHON_CLIENT and TELETHON_CLIENT.is_connected()),
            "bot_restarts": WATCHDOG_STATS.get("bot_restarts", 0),
            "telethon_restarts": WATCHDOG_STATS.get("telethon_restarts", 0),
            "firestore_connected": WATCHDOG_STATS.get("firestore_connected", False),
            "blast_heartbeat_age": WATCHDOG_STATS.get("blast_heartbeat_age", 0)
        },
        "join_safety": {
            "max_joins_hourly": MAX_JOINS_PER_CYCLE,
            "recent_joins_1h": get_recent_joins_count(3600),
            "join_flood_active": time.time() < JOIN_FLOOD_UNTIL,
            "failed_targets_count": len(FAILED_JOIN_TARGETS)
        },
        "system": "standalone_dijital_pazarim_v3"
    })

@app.route("/api/start", methods=["POST", "GET"])
def api_start_ad():
    global AD_RUNNING
    AD_RUNNING = True
    sys_log("[Panel] Reklam gönderimi panelden BAŞLATILDI.")
    return jsonify({"success": True, "ad_running": AD_RUNNING, "message": "Reklam döngüsü başlatıldı."})

@app.route("/api/stop", methods=["POST", "GET"])
def api_stop_ad():
    global AD_RUNNING
    AD_RUNNING = False
    sys_log("[Panel] Reklam gönderimi panelden DURDURULDU.")
    return jsonify({"success": True, "ad_running": AD_RUNNING, "message": "Reklam döngüsü durduruldu."})

@app.route("/api/broadcast", methods=["POST"])
def api_broadcast():
    data = request.get_json(silent=True) or request.form.to_dict()
    text = (data.get("message") or data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "Duyuru metni boş olamaz."}), 400
    
    if not TELETHON_CLIENT or not TELETHON_LOOP:
        return jsonify({"success": False, "error": "Kullanıcı hesabı bağlı değil veya henüz hazır değil."}), 503

    async def do_broadcast(msg_text):
        count = 0
        dialogs = await TELETHON_CLIENT.get_dialogs(limit=60)
        target_groups = [d for d in dialogs if d.is_group]
        sys_log(f"[TopluDuyuru] {len(target_groups)} gruba duyuru gönderimi başlatılıyor...")
        for group in target_groups:
            try:
                await TELETHON_CLIENT.send_message(group.id, msg_text)
                count += 1
                sys_log(f"[TopluDuyuru] Duyuru iletildi -> {group.name}")
                await asyncio.sleep(2)
            except Exception as e:
                sys_log(f"[TopluDuyuru] Gönderim hatası ({group.name}): {e}")
        sys_log(f"[TopluDuyuru] Tamamlandı! Toplam {count} gruba başarıyla duyuru iletildi.")
        return count

    future = asyncio.run_coroutine_threadsafe(do_broadcast(text), TELETHON_LOOP)
    try:
        sent_count = future.result(timeout=120)
        return jsonify({"success": True, "sent_count": sent_count, "message": f"{sent_count} gruba duyuru iletildi."})
    except Exception as e:
        sys_log(f"[TopluDuyuru] Hata: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# 2. TELEGRAM BOT WORKER (@DijitalPazarimBot)
# ─────────────────────────────────────────────────────────────

ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "7499698483"))

def load_products_catalog() -> list[dict]:
    p_file = MINIAPP_DIR / "products_db.json"
    if p_file.exists():
        try:
            return json.loads(p_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def get_categorized_catalog():
    prods = load_products_catalog()
    cats = {
        "market": {"title": "Market, Yemek & Ulaşım Kuponları", "items": []},
        "dizi": {"title": "Dizi & Film Platformları", "items": []},
        "muzik": {"title": "Müzik & Video Abonelikleri", "items": []},
        "ai": {"title": "Yapay Zeka (Google Gemini Pro)", "items": []}
    }
    for p in prods:
        c = p.get("category", "")
        if c in cats:
            cats[c]["items"].append(p)
        else:
            cats["market"]["items"].append(p)
    return cats

def get_full_price_list_text() -> str:
    cats = get_categorized_catalog()
    lines = [
        "DİJİTAL PAZARIM - GÜNCEL FİYAT LİSTESİ",
        "------------------------------------",
        ""
    ]
    for code, info in cats.items():
        lines.append(f"[{info['title'].upper()}]")
        for item in info["items"]:
            lines.append(f"• {item['title']} — {item['price']}")
        lines.append("")
    lines.append("Tüm ürünlerimiz 7/24 anında otomatik teslim edilmektedir.")
    lines.append("Detaylı incelemek için aşağıdaki butonları veya mağazamızı kullanabilirsiniz.")
    return "\n".join(lines).strip()

def get_category_screen(cat_code: str):
    cats = get_categorized_catalog()
    if cat_code not in cats:
        cat_code = "market"
    info = cats[cat_code]
    lines = [
        f"{info['title'].upper()}",
        "------------------------------------",
        ""
    ]
    buttons = []
    for item in info["items"]:
        lines.append(f"• {item['title']} — {item['price']}")
        if item.get("desc"):
            lines.append(f"  {item['desc']}")
        lines.append("")
        buy_url = item.get("url") or MINIAPP_URL
        buttons.append([{"text": f"{item['title'][:28]}... ({item['price']})", "url": buy_url}])

    buttons.append([{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}])
    buttons.append([
        {"text": "<< Kategoriler", "callback_data": "menu_categories"},
        {"text": "Ana Menü", "callback_data": "menu_main"}
    ])
    return "\n".join(lines).strip(), {"inline_keyboard": buttons}

def get_welcome_screen(first_name: str = "Değerli Müşterimiz"):
    text = (
        f"Merhaba {first_name},\n\n"
        "Dijital Pazarım resmi mağaza ve destek servisine hoş geldiniz.\n\n"
        "En popüler dijital abonelik lisanslarını, indirim kuponlarını, market & yemek kodlarını "
        "en avantajlı fiyatlarla, 7/24 anında teslimat ve garanti güvencesiyle temin edebilirsiniz.\n\n"
        "ÖNE ÇIKAN KATEGORİLER:\n"
        "• Market, Yemek & Ulaşım Kuponları (Trendyol Go, Trendyol Yemek, Shell, Uber)\n"
        "• Dizi & Film Platformları (Netflix 4K Ultra HD, Disney+ Ortak & Özel Profil)\n"
        "• Müzik & Video Abonelikleri (YouTube Premium, Spotify Premium)\n"
        "• Yapay Zeka Çözümleri (Google Gemini Pro Lisans & Davet Paketleri)\n\n"
        "Aşağıdaki menüden dilediğiniz kategoriyi inceleyebilir veya doğrudan mağazamıza giriş yapabilirsiniz."
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
            [
                {"text": "Kategoriler", "callback_data": "menu_categories"},
                {"text": "Fiyat Listesi", "callback_data": "list_prices"}
            ],
            [
                {"text": "Nasıl Sipariş Verilir?", "callback_data": "how_to_order"},
                {"text": "Canlı Destek", "callback_data": "support_info"}
            ]
        ]
    }
    return text, keyboard

def get_categories_menu():
    text = (
        "DİJİTAL PAZARIM - ÜRÜN KATEGORİLERİ\n"
        "------------------------------------\n\n"
        "Lütfen incelemek istediğiniz ürün grubunu seçiniz:\n\n"
        "1. Market, Yemek & Ulaşım: Trendyol Go, Yemek, Uber, Shell kodları\n"
        "2. Dizi & Film: Netflix 4K UHD, Disney+ hesapları\n"
        "3. Müzik & Video: YouTube Premium, Spotify Premium\n"
        "4. Yapay Zeka: Google Gemini Pro 1/12/18 Ay paketleri"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Market, Yemek & Ulaşım", "callback_data": "cat_market"}],
            [{"text": "Dizi & Film Platformları", "callback_data": "cat_dizi"}],
            [{"text": "Müzik & Video Abonelikleri", "callback_data": "cat_muzik"}],
            [{"text": "Yapay Zeka (AI)", "callback_data": "cat_ai"}],
            [
                {"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}},
                {"text": "<< Ana Menü", "callback_data": "menu_main"}
            ]
        ]
    }
    return text, keyboard

def get_how_to_order_screen():
    text = (
        "NASIL SİPARİŞ VERİLİR? & GÜVENCE\n"
        "------------------------------------\n\n"
        "1. ÜRÜN SEÇİMİ:\n"
        "Mağazayı Aç butonuna tıklayarak veya Kategoriler menüsünden dilediğiniz ürünü seçiniz.\n\n"
        "2. GÜVENLİ ÖDEME:\n"
        "Shopier altyapısı ve 3D Secure güvencesiyle kredi veya banka kartınızla güvenle ödemenizi tamamlayınız.\n\n"
        "3. ANINDA OTOMATİK TESLİMAT:\n"
        "Ödemeniz onaylandığı anda dijital kodunuz veya hesap erişim bilgileriniz anında ekranda görüntülenir ve e-postanıza iletilir.\n\n"
        "4. 30 GÜN TELAFİ VE DEĞİŞİM GARANTİSİ:\n"
        "Tüm lisans ve hesaplarımız 30 gün boyunca birebir telafi ve teknik destek garantisi altındadır.\n\n"
        "Sorularınız için Canlı Destek butonundan yetkili ekibimize yazabilirsiniz."
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
            [
                {"text": "Kategoriler", "callback_data": "menu_categories"},
                {"text": "Canlı Destek", "callback_data": "support_info"}
            ],
            [{"text": "<< Ana Menü", "callback_data": "menu_main"}]
        ]
    }
    return text, keyboard

def get_support_screen():
    text = (
        "DİJİTAL PAZARIM MÜŞTERİ DESTEĞİ\n"
        "------------------------------------\n\n"
        "Siparişleriniz, ürün teslimatları veya teknik sorularınız için "
        "mesajınızı doğrudan bu sohbete yazabilirsiniz.\n\n"
        "Yetkili ekibimiz mesajınızı inceleyerek anında bu sohbet üzerinden dönüş yapacaktır.\n\n"
        "• Çalışma Saatleri: 7/24 Kesintisiz Destek\n"
        "• Ortalama Yanıt Süresi: 5 - 15 Dakika\n"
        "• Müşteri Memnuniyeti: Garantili Telafi Güvencesi"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
            [
                {"text": "Kategoriler", "callback_data": "menu_categories"},
                {"text": "<< Ana Menü", "callback_data": "menu_main"}
            ]
        ]
    }
    return text, keyboard

def get_profile_screen(chat_id: int | str):
    text = (
        "HESAP VE SİPARİŞ TAKİBİ\n"
        "------------------------------------\n\n"
        f"Kullanıcı ID: {chat_id}\n\n"
        "Sipariş geçmişinize, aktif lisanslarınıza ve bakiye hareketlerinize "
        "doğrudan mağazamız içerisindeki 'Siparişlerim' ve 'Hesabım' sekmelerinden 7/24 ulaşabilirsiniz."
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Siparişlerimi Görüntüle", "web_app": {"url": MINIAPP_URL}}],
            [{"text": "<< Ana Menü", "callback_data": "menu_main"}]
        ]
    }
    return text, keyboard

def get_persistent_reply_keyboard():
    return {
        "keyboard": [
            [
                {"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}},
                {"text": "Fiyat Listesi"}
            ],
            [
                {"text": "Kategoriler"},
                {"text": "Nasıl Sipariş Verilir?"}
            ],
            [
                {"text": "Canlı Destek"},
                {"text": "Hesabım & Siparişler"}
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

PRODUCT_TRIGGERS = {
    "netflix": ["netflix"],
    "disney": ["disney"],
    "trendyol": ["trendyol", "go"],
    "yemek": ["yemek"],
    "uber": ["uber"],
    "shell": ["shell", "akaryakıt", "yakıt"],
    "spotify": ["spotify"],
    "youtube": ["youtube"],
    "gemini": ["gemini", "yapay zeka"]
}

def match_product_by_text(query: str):
    q = query.lower().strip()
    prods = load_products_catalog()
    matched_keys = set()
    for brand, triggers in PRODUCT_TRIGGERS.items():
        if any(tr in q for tr in triggers):
            matched_keys.add(brand)
    
    if not matched_keys:
        return []

    results = []
    for p in prods:
        k = p.get("key", "").lower()
        t = p.get("title", "").lower()
        if any(mk in k or mk in t for mk in matched_keys):
            results.append(p)
    return results

@app.route("/api/telegram-webhook", methods=["POST"])
def api_telegram_webhook():
    """Telegram Bot API Webhook receiver for @DijitalPazarimBot."""
    try:
        update = request.get_json(force=True, silent=True)
        if update:
            BOT_HEALTH_STATE["last_ok"] = datetime.now().strftime("%H:%M:%S")
            BOT_HEALTH_STATE["status"] = "online"
            threading.Thread(target=handle_telegram_update, args=(update,), daemon=True).start()
        return jsonify({"ok": True}), 200
    except Exception as e:
        sys_log(f"[DijitalPazarimBot] Webhook işleme hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

def setup_telegram_bot():
    """Configures menu button and webhook for @DijitalPazarimBot, locking out external conflicting pollers."""
    global BOT_HEALTH_STATE
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN":
        sys_log("[DijitalPazarimBot] Token bulunamadı, bot yapılandırılamıyor.")
        return

    sys_log(f"[DijitalPazarimBot] Bot servisi webhook modunda yapılandırılıyor (@DijitalPazarimBot)...")

    # 1. Update Menu Button to Mini App (/dp)
    try:
        btn = {
            "type": "web_app",
            "text": "Mağazayı Aç",
            "web_app": {
                "url": MINIAPP_URL
            }
        }
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton",
            headers={"Content-Type": "application/json; charset=utf-8"},
            data=json.dumps({"menu_button": btn}, ensure_ascii=False).encode('utf-8'),
            timeout=10
        )
        sys_log(f"[DijitalPazarimBot] Chat menu button güncellendi -> {MINIAPP_URL} ({res.status_code})")
    except Exception as e:
        sys_log(f"[DijitalPazarimBot] Menu button hatası: {e}")

    # 2. Configure Telegram Webhook
    webhook_url = f"{PUBLIC_BASE_URL}/api/telegram-webhook"
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={
                "url": webhook_url,
                "drop_pending_updates": True,
                "allowed_updates": ["message", "callback_query"]
            },
            timeout=15
        )
        data = res.json()
        if data.get("ok"):
            BOT_HEALTH_STATE["status"] = "online"
            BOT_HEALTH_STATE["mode"] = "webhook"
            BOT_HEALTH_STATE["webhook_url"] = webhook_url
            BOT_HEALTH_STATE["last_ok"] = datetime.now().strftime("%H:%M:%S")
            sys_log(f"[DijitalPazarimBot] ✅ Webhook aktif -> {webhook_url}. Dış getUpdates çakışmaları engellendi.")
        else:
            BOT_HEALTH_STATE["status"] = "warning"
            sys_log(f"[DijitalPazarimBot] ⚠️ Webhook uyarısı: {data}")
    except Exception as e:
        BOT_HEALTH_STATE["status"] = "error"
        sys_log(f"[DijitalPazarimBot] Webhook kurulum hatası: {e}")

def check_webhook_health():
    """Periodically verifies that webhook remains active."""
    global BOT_HEALTH_STATE
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN":
        return
    expected_url = f"{PUBLIC_BASE_URL}/api/telegram-webhook"
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=10)
        if r.status_code == 200:
            data = r.json().get("result", {})
            curr_url = data.get("url", "")
            if curr_url != expected_url:
                sys_log(f"[DijitalPazarimBot] Webhook adresi güncelleniyor: {curr_url} -> {expected_url}")
                setup_telegram_bot()
            else:
                BOT_HEALTH_STATE["status"] = "online"
                BOT_HEALTH_STATE["mode"] = "webhook"
                BOT_HEALTH_STATE["pending_updates"] = data.get("pending_update_count", 0)
    except Exception:
        pass

def send_bot_message(chat_id: int | str, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            headers={"Content-Type": "application/json; charset=utf-8"},
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            timeout=8
        )
    except Exception as e:
        sys_log(f"[DijitalPazarimBot] sendMessage hatası: {e}")

def edit_bot_message(chat_id: int | str, message_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
            headers={"Content-Type": "application/json; charset=utf-8"},
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            timeout=8
        )
        if not r.json().get("ok"):
            send_bot_message(chat_id, text, reply_markup)
    except Exception:
        send_bot_message(chat_id, text, reply_markup)

def handle_telegram_update(update: dict):
    try:
        # 1. Callback query
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            message_id = cb.get("message", {}).get("message_id")
            cb_id = cb.get("id")
            cb_data = cb.get("data", "")
            first_name = cb.get("from", {}).get("first_name", "Değerli Müşterimiz")
            
            try:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
            except Exception:
                pass
            
            if cb_data == "menu_main":
                text, kb = get_welcome_screen(first_name)
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data == "menu_categories":
                text, kb = get_categories_menu()
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data in ("cat_market", "cat_dizi", "cat_muzik", "cat_ai"):
                cat_code = cb_data.replace("cat_", "")
                text, kb = get_category_screen(cat_code)
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data == "list_prices":
                text = get_full_price_list_text()
                kb = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
                        [
                            {"text": "Kategoriler", "callback_data": "menu_categories"},
                            {"text": "Canlı Destek", "callback_data": "support_info"}
                        ],
                        [{"text": "<< Ana Menü", "callback_data": "menu_main"}]
                    ]
                }
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data == "how_to_order":
                text, kb = get_how_to_order_screen()
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data == "support_info":
                text, kb = get_support_screen()
                edit_bot_message(chat_id, message_id, text, kb)
            elif cb_data == "menu_profile":
                text, kb = get_profile_screen(chat_id)
                edit_bot_message(chat_id, message_id, text, kb)
            return

        # 2. Text message
        if "message" in update and "text" in update["message"]:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            raw_text = msg["text"].strip()
            lower_text = raw_text.lower()
            first_name = msg.get("from", {}).get("first_name", "Değerli Müşterimiz")
            username = msg.get("from", {}).get("username", "")

            # Start & Store
            if lower_text.startswith("/start") or lower_text.startswith("/magaza") or lower_text in ("mağaza", "mağazayı aç", "başla"):
                sys_log(f"[DijitalPazarimBot] /start komutu alındı -> Chat ID: {chat_id} ({first_name})")
                text, inline_kb = get_welcome_screen(first_name)
                send_bot_message(chat_id, text, inline_kb)
                reply_kb = get_persistent_reply_keyboard()
                send_bot_message(chat_id, "Hızlı erişim alt menüsü aktif edildi. Dilediğiniz zaman aşağıdaki menüden işlem yapabilirsiniz:", reply_kb)
                return

            # Kategoriler
            if lower_text in ("/kategoriler", "kategoriler", "kategori", "ürünler"):
                text, kb = get_categories_menu()
                send_bot_message(chat_id, text, kb)
                return

            # Fiyat Listesi
            if lower_text in ("/fiyatlar", "/fiyat", "fiyat listesi", "fiyatlar", "fiyat", "ücret"):
                text = get_full_price_list_text()
                kb = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
                        [
                            {"text": "Kategoriler", "callback_data": "menu_categories"},
                            {"text": "Canlı Destek", "callback_data": "support_info"}
                        ]
                    ]
                }
                send_bot_message(chat_id, text, kb)
                return

            # Nasıl Sipariş Verilir?
            if any(k in lower_text for k in ("nasıl sipariş verilir", "nasıl çalışır", "nasıl alırım", "ödeme", "güvence")):
                text, kb = get_how_to_order_screen()
                send_bot_message(chat_id, text, kb)
                return

            # Canlı Destek
            if lower_text in ("canlı destek", "destek", "/destek", "yardım", "iletişim", "admin"):
                text, kb = get_support_screen()
                send_bot_message(chat_id, text, kb)
                return

            # Hesabım / Siparişlerim / Bilgilerim
            if any(k in lower_text for k in ("hesabım & siparişler", "hesabım", "siparişlerim", "bilgilerim", "bakiye")):
                text, kb = get_profile_screen(chat_id)
                send_bot_message(chat_id, text, kb)
                return

            # Özel Ürün Eşleştirme (Keyword Matcher)
            matched = match_product_by_text(lower_text)
            if matched:
                item = matched[0]
                lines = [
                    f"ARANAN ÜRÜN BULUNDU: {item['title'].upper()}",
                    "------------------------------------",
                    f"Fiyat: {item['price']}",
                    f"Özellik: {item.get('badge', 'Orijinal Lisans')}",
                    ""
                ]
                if item.get("desc"):
                    lines.append(item["desc"])
                    lines.append("")
                lines.append("Anında satın almak veya detayları görmek için aşağıdaki butona tıklayabilirsiniz.")
                
                buy_url = item.get("url") or MINIAPP_URL
                kb = {
                    "inline_keyboard": [
                        [{"text": f"Satın Al ({item['price']})", "url": buy_url}],
                        [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
                        [{"text": "Kategoriler", "callback_data": "menu_categories"}]
                    ]
                }
                send_bot_message(chat_id, "\n".join(lines).strip(), kb)
                sys_log(f"[DijitalPazarimBot] Anahtar kelime eşleşti ({lower_text[:20]}) -> {item['title']}")
                return

            # Genel Müşteri Sorusu / Mesajı
            sys_log(f"[DijitalPazarimBot] Müşteri mesajı: {raw_text[:40]}... -> Chat ID: {chat_id} ({first_name})")
            
            # 1. Admin ID'ye Bildir
            try:
                import html
                admin_alert = (
                    "<b>[DİJİTAL PAZARIM MÜŞTERİ MESAJI]</b>\n\n"
                    f"Müşteri: <b>{html.escape(first_name)}</b> (@{html.escape(username) if username else 'Kullanıcı adı yok'})\n"
                    f"Kullanıcı ID: <code>{chat_id}</code>\n\n"
                    f"Gelen Mesaj:\n<code>{html.escape(raw_text)}</code>"
                )
                send_bot_message(ADMIN_TELEGRAM_ID, admin_alert)
            except Exception as ae:
                sys_log(f"[DijitalPazarimBot] Admin bildirim hatası: {ae}")

            # 2. Müşteriye Kurumsal Yanıt
            reply_text = (
                "Mesajınız canlı destek ekibimize iletilmiştir.\n"
                "Yetkili temsilcimiz en kısa sürede doğrudan bu sohbete dönüş sağlayacaktır.\n\n"
                "Ürünlerimizi incelemek veya anında sipariş vermek için aşağıdaki butonları kullanabilirsiniz."
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Mağazayı Aç (Mini App)", "web_app": {"url": MINIAPP_URL}}],
                    [
                        {"text": "Kategoriler", "callback_data": "menu_categories"},
                        {"text": "Fiyat Listesi", "callback_data": "list_prices"}
                    ]
                ]
            }
            send_bot_message(chat_id, reply_text, keyboard)

    except Exception as e:
        sys_log(f"[DijitalPazarimBot] Mesaj işleme hatası: {e}")

# ─────────────────────────────────────────────────────────────
# 3. USER ACCOUNT RUNNER (+18595173039 / @DijitalPazarimm)
# ─────────────────────────────────────────────────────────────

API_ID = int(os.environ.get("TELEGRAM_API_ID", "31076280"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8")
ACCOUNT_SESSION = os.environ.get("AD_STRING_SESSION_DIJITALPAZARIM", "").strip()

ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "7499698483"))

# Join and Broadcast safety thresholds - exactly matched to main project (otomatik_katil.py)
JOIN_DELAY_MIN_SECONDS = 180  # 3 minutes
JOIN_DELAY_MAX_SECONDS = 360  # 6 minutes
MAX_JOINS_PER_CYCLE = 3       # Max 3 joins per 1-hour window
GROUP_DELAY_MIN_SECONDS = 30  # 30 seconds
GROUP_DELAY_MAX_SECONDS = 45  # 45 seconds

RECENT_JOIN_TIMESTAMPS: list[float] = []
FAILED_JOIN_TARGETS: set[str] = set()
PENDING_INVITES: set[str] = set()
JOIN_FLOOD_UNTIL: float = 0.0

def load_persistent_join_state():
    global RECENT_JOIN_TIMESTAMPS, FAILED_JOIN_TARGETS, PENDING_INVITES
    p_file = BASE_DIR / "dijitalpazarim_pending_invites.json"
    if p_file.exists():
        try:
            PENDING_INVITES = set(json.loads(p_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    f_file = BASE_DIR / "dijitalpazarim_failed_targets.json"
    if f_file.exists():
        try:
            FAILED_JOIN_TARGETS = set(json.loads(f_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    h_file = BASE_DIR / "dijitalpazarim_join_history.json"
    if h_file.exists():
        try:
            RECENT_JOIN_TIMESTAMPS = [t for t in json.loads(h_file.read_text(encoding="utf-8")) if time.time() - t < 3600]
        except Exception:
            pass

def save_persistent_join_state():
    try:
        (BASE_DIR / "dijitalpazarim_pending_invites.json").write_text(
            json.dumps(list(PENDING_INVITES), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (BASE_DIR / "dijitalpazarim_failed_targets.json").write_text(
            json.dumps(list(FAILED_JOIN_TARGETS), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (BASE_DIR / "dijitalpazarim_join_history.json").write_text(
            json.dumps(RECENT_JOIN_TIMESTAMPS, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass

load_persistent_join_state()

def get_recent_joins_count(window_seconds: int = 3600) -> int:
    global RECENT_JOIN_TIMESTAMPS
    now = time.time()
    RECENT_JOIN_TIMESTAMPS = [t for t in RECENT_JOIN_TIMESTAMPS if now - t < window_seconds]
    return len(RECENT_JOIN_TIMESTAMPS)

def load_ad_templates() -> list[str]:
    templates = []
    for i in range(1, 5):
        tpl_path = MESSAGES_DIR / f"dijitalpazarim_{i}.txt"
        if tpl_path.exists():
            content = tpl_path.read_text(encoding="utf-8").strip()
            if content:
                templates.append(content)
    return templates

async def run_telethon_account():
    global TELETHON_CLIENT, JOINED_GROUPS_COUNT
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.errors import (
        FloodWaitError, SlowModeWaitError, ChatWriteForbiddenError,
        UserBannedInChannelError, ChannelPrivateError, UsernameNotOccupiedError,
        UsernameInvalidError
    )

    session_to_use = ACCOUNT_SESSION
    if not session_to_use:
        session_file = BASE_DIR / "dijitalpazarim_session_string.txt"
        if session_file.exists():
            session_to_use = session_file.read_text(encoding="utf-8").strip()

    if not session_to_use:
        sys_log("[DijitalPazarimAccount] Oturum anahtarı bulunamadı, kullanıcı hesabı başlatılamadı.")
        return

    sys_log("[DijitalPazarimAccount] Telethon kullanıcı hesabı başlatılıyor (+18595173039)...")
    client = TelegramClient(StringSession(session_to_use), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        sys_log("[DijitalPazarimAccount] Oturum yetkisiz, iptal edildi.")
        await client.disconnect()
        return

    me = await client.get_me()
    TELETHON_CLIENT = client
    sys_log(f"[DijitalPazarimAccount] Aktif Hesap: {me.first_name} (@{me.username}) - {me.phone}")

    try:
        init_dialogs = await client.get_dialogs(limit=200)
        init_groups = [d for d in init_dialogs if d.is_group]
        JOINED_GROUPS_COUNT = len(init_groups)
        sys_log(f"[DijitalPazarimAccount] Başlangıç taraması: Toplam {JOINED_GROUPS_COUNT} gruba üye olunduğu tespit edildi.")
    except Exception as ie:
        sys_log(f"[DijitalPazarimAccount] Başlangıç diyalog tarama uyarısı: {ie}")

    # 1. Telegram Resmi Güvenlik / Giriş Kodu Yakalayıcı (777000)
    @client.on(events.NewMessage(incoming=True, chats=777000))
    async def handle_official_telegram_code(event):
        msg_text = event.raw_text or ""
        sys_log(f"[GİRİŞ KODU YAKALANDI] Dijital Pazarım hesabına resmi kod geldi:\n{msg_text}")
        try:
            alert = (
                f"<b>[DİJİTAL PAZARIM GİRİŞ KODU]</b>\n\n"
                f"Hesap: <b>+18595173039 (@DijitalPazarimm)</b>\n"
                f"Mesaj:\n<code>{msg_text}</code>"
            )
            send_bot_message(ADMIN_TELEGRAM_ID, alert)
        except Exception as ex:
            sys_log(f"[GirişKodu] Bildirim iletme hatası: {ex}")

    # 2. Auto DM Reply: Directs private inquiries to @DijitalPazarimBot
    dm_replied_users = set()

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_private_dm(event):
        sender_id = event.sender_id
        if sender_id == me.id or sender_id == 777000 or sender_id in dm_replied_users:
            return

        sender = await event.get_sender()
        if getattr(sender, 'bot', False):
            return

        dm_replied_users.add(sender_id)
        reply_text = (
            "Merhaba,\n\n"
            "İndirim kuponları, market & yemek kodları ve premium dijital lisanslar için "
            "doğrudan resmi mağaza botumuz @DijitalPazarimBot üzerinden anında ve güvenle sipariş verebilirsiniz.\n\n"
            "Referanslarımız mevcuttur, otomatik teslimat sağlanmaktadır."
        )
        try:
            await event.reply(reply_text)
            sys_log(f"[DijitalPazarimAccount] DM yönlendirmesi gönderildi -> Kullanıcı ID: {sender_id}")
        except Exception as e:
            sys_log(f"[DijitalPazarimAccount] DM yanıt hatası: {e}")

    # 3. Akıllı Hedef Grup Katılım Motoru (Anti-Flood ve Saatlik Limit Korumalı)
    async def try_join_target_groups(max_joins: int = 3) -> int:
        global TOTAL_ADS_SENT, JOINED_GROUPS_COUNT, JOIN_FLOOD_UNTIL
        now_ts = time.time()
        if now_ts < JOIN_FLOOD_UNTIL:
            wait_sec = int(JOIN_FLOOD_UNTIL - now_ts)
            sys_log(f"[DijitalPazarimAccount] Join FloodWait aktif ({wait_sec} sn kaldı), katılım adımı atlandı.")
            return 0

        current_recent = get_recent_joins_count(3600)
        allowed_joins = min(max_joins, MAX_JOINS_PER_CYCLE - current_recent)
        if allowed_joins <= 0:
            return 0

        try:
            dialogs = await client.get_dialogs(limit=200)
        except Exception as de:
            sys_log(f"[DijitalPazarimAccount] Diyalog tarama hatası: {de}")
            return 0

        joined_groups = {}
        joined_usernames = set()
        for d in dialogs:
            if d.is_group:
                joined_groups[d.id] = d
                uname = getattr(d.entity, "username", None)
                if uname:
                    joined_usernames.add(uname.lower())

        JOINED_GROUPS_COUNT = len(joined_groups)
        targets = load_target_groups()
        blacklist = load_blacklist()

        not_joined = []
        for target_name in targets:
            t_clean = target_name.lower().lstrip("@")
            if (
                t_clean
                and t_clean not in blacklist
                and t_clean not in joined_usernames
                and t_clean not in FAILED_JOIN_TARGETS
                and t_clean not in PENDING_INVITES
            ):
                not_joined.append(t_clean)

        if not not_joined:
            return 0

        sys_log(f"[DijitalPazarimAccount] Katılınabilecek {len(not_joined)} hedef grup mevcut (Saatlik hak: {allowed_joins}).")
        joined_count = 0
        attempts = 0

        for target_to_try in not_joined:
            if joined_count >= allowed_joins or attempts >= allowed_joins:
                break

            if get_recent_joins_count(3600) >= MAX_JOINS_PER_CYCLE:
                sys_log(f"[DijitalPazarimAccount] Saatlik katılım limiti ({MAX_JOINS_PER_CYCLE}/saat) doldu.")
                break

            attempts += 1
            sys_log(f"[DijitalPazarimAccount] Hedef grup kontrol ediliyor ({attempts}/{allowed_joins}): @{target_to_try}")
            try:
                entity = await client.get_entity(target_to_try)
                await client(JoinChannelRequest(entity))
                joined_usernames.add(target_to_try)
                joined_groups[entity.id] = entity
                JOINED_GROUPS_COUNT = len(joined_groups)
                RECENT_JOIN_TIMESTAMPS.append(time.time())
                if target_to_try in PENDING_INVITES:
                    PENDING_INVITES.remove(target_to_try)
                save_persistent_join_state()
                sys_log(f"[DijitalPazarimAccount] Gruba başarıyla katıldı: @{target_to_try}")
                joined_count += 1

                if joined_count < allowed_joins:
                    join_delay = random.randint(JOIN_DELAY_MIN_SECONDS, JOIN_DELAY_MAX_SECONDS)
                    sys_log(f"[DijitalPazarimAccount] Güvenli aralık: Sonraki katılım öncesi {join_delay} sn bekleniyor...")
                    await asyncio.sleep(join_delay)
                else:
                    await asyncio.sleep(5)

            except FloodWaitError as fwe:
                JOIN_FLOOD_UNTIL = time.time() + fwe.seconds + 60
                sys_log(f"[DijitalPazarimAccount] Join FloodWait: {fwe.seconds} sn. Katılım duraklatıldı.")
                break
            except Exception as e:
                err_msg = str(e).lower()
                err_type = type(e).__name__
                if "already" in err_msg or "useralreadyparticipant" in err_type.lower():
                    joined_usernames.add(target_to_try)
                    sys_log(f"[DijitalPazarimAccount] Zaten üye olunan grup: @{target_to_try}")
                    if target_to_try in PENDING_INVITES:
                        PENDING_INVITES.remove(target_to_try)
                    save_persistent_join_state()
                    await asyncio.sleep(2)
                elif "requested to join" in err_msg or "inviterequestsent" in err_type.lower():
                    PENDING_INVITES.add(target_to_try)
                    RECENT_JOIN_TIMESTAMPS.append(time.time())
                    save_persistent_join_state()
                    sys_log(f"[DijitalPazarimAccount] @{target_to_try} katılım isteği iletildi (yönetici onayı bekleniyor).")
                    await asyncio.sleep(3)
                elif any(k in err_msg for k in ("private", "banned", "forbidden", "admin", "channel_private", "user_banned")) or isinstance(e, (UserBannedInChannelError, ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError)):
                    FAILED_JOIN_TARGETS.add(target_to_try)
                    save_persistent_join_state()
                    sys_log(f"[DijitalPazarimAccount] @{target_to_try} açık katılım kapalı ({err_type}), listeden elendi.")
                    await asyncio.sleep(2)
                else:
                    sys_log(f"[DijitalPazarimAccount] Gruba katılım atlandı (@{target_to_try}): {e}")
                    await asyncio.sleep(3)

        return joined_count

    # 4. Background Ad Broadcast & Auto-Join loop
    async def ad_broadcast_loop():
        global TOTAL_ADS_SENT, LAST_CYCLE_TIME, JOINED_GROUPS_COUNT, JOIN_FLOOD_UNTIL, LAST_BLAST_HEARTBEAT
        await asyncio.sleep(5)  # Hızlı başlangıç hazırlığı
        templates = load_ad_templates()
        template_idx = 0

        while True:
            try:
                LAST_BLAST_HEARTBEAT = time.time()
                if not AD_RUNNING:
                    await asyncio.sleep(5)
                    continue

                # KORUMA A: Firestore / Yerel Checkpoint Koruması (Deploy / Restart sonrasında süreyi bekler)
                remaining = CHECKPOINT.get_remaining_seconds()
                if remaining > 0:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    sys_log(
                        f"[DijitalPazarimAccount] Önceki reklam turu aktif: Firestore checkpoint doğrulandı. "
                        f"Kalan bekleme süresi: {mins} dk {secs} sn. Erken gönderim engellendi."
                    )
                    while remaining > 0 and AD_RUNNING:
                        sleep_chunk = min(5, remaining)
                        await asyncio.sleep(sleep_chunk)
                        remaining = CHECKPOINT.get_remaining_seconds()
                        LAST_BLAST_HEARTBEAT = time.time()
                    if not AD_RUNNING:
                        continue

                if not templates:
                    templates = load_ad_templates()
                
                if templates:
                    current_ad = templates[template_idx % len(templates)]
                    template_idx += 1

                    # 1. Mevcut üye olunan grupları tara
                    dialogs = await client.get_dialogs(limit=200)
                    joined_groups = {}
                    for d in dialogs:
                        if d.is_group:
                            joined_groups[d.id] = d
                    JOINED_GROUPS_COUNT = len(joined_groups)

                    # 2. Reklam gönderim döngüsü (30-45 saniye grup aralığı)
                    sys_log(f"[DijitalPazarimAccount] Reklam döngüsü başladı ({len(joined_groups)} aktif grup)...")
                    CHECKPOINT.record_blast_started()
                    blacklist = load_blacklist()

                    for gid, group in list(joined_groups.items()):
                        LAST_BLAST_HEARTBEAT = time.time()
                        if not AD_RUNNING:
                            sys_log("[DijitalPazarimAccount] Gönderim döngü esnasında durduruldu.")
                            break

                        g_title = getattr(group, 'name', str(gid))
                        g_uname = getattr(getattr(group, 'entity', None), 'username', '') or ''
                        if g_uname.lower() in blacklist:
                            continue

                        group_key = g_uname.lower() if g_uname else str(gid)

                        # KORUMA B: Checkpoint kayıtlarında son 50 dakika kontrolü
                        if CHECKPOINT.was_group_sent_recently(group_key, window_seconds=3000):
                            sys_log(f"[DijitalPazarimAccount] {g_title} son 50 dakikada mesaj almış (checkpoint kaydı); tekrar atlanıyor.")
                            continue

                        dest = getattr(group, 'entity', None) or getattr(group, 'input_entity', None) or group

                        # KORUMA C: Canlı Telegram Sohbet Geçmişi Koruması (Telethon get_messages limit=15)
                        try:
                            recent_messages = await client.get_messages(dest, limit=15)
                            if any(is_recent_message_from_account(m, me.id, window_seconds=3000) for m in recent_messages or []):
                                sys_log(f"[DijitalPazarimAccount] {g_title} Telegram sohbet geçmişinde son 50 dakikada bu hesaptan mesaj tespit edildi; duplicate koruması ile atlandı.")
                                CHECKPOINT.record_group_send(group_key)
                                continue
                        except Exception as guard_err:
                            sys_log(f"[DijitalPazarimAccount] {g_title} geçmiş mesaj koruma kontrolü uyarısı: {type(guard_err).__name__}")

                        try:
                            await client.send_message(dest, current_ad, link_preview=False)
                            TOTAL_ADS_SENT += 1
                            CHECKPOINT.record_group_send(group_key)
                            sys_log(f"[DijitalPazarimAccount] Reklam paylaşıldı -> {g_title}")
                            await asyncio.sleep(random.randint(GROUP_DELAY_MIN_SECONDS, GROUP_DELAY_MAX_SECONDS))
                        except FloodWaitError as fwe:
                            sys_log(f"[DijitalPazarimAccount] FloodWait: {fwe.seconds} saniye bekleniyor...")
                            await asyncio.sleep(fwe.seconds + 5)
                        except SlowModeWaitError as sm:
                            if sm.seconds > 45:
                                sys_log(f"[DijitalPazarimAccount] SlowMode aktif ({g_title}): {sm.seconds} sn beklemede; grup bu tur atlanıp sonraki gruba devam ediliyor.")
                            else:
                                wait_s = sm.seconds + 2
                                sys_log(f"[DijitalPazarimAccount] SlowMode ({g_title}): {sm.seconds} sn, {wait_s} sn bekleniyor...")
                                await asyncio.sleep(wait_s)
                        except (ChatWriteForbiddenError, UserBannedInChannelError) as cwf:
                            sys_log(f"[DijitalPazarimAccount] Yazma izni yok/banlı, bu tur atlandı -> {g_title}")
                        except Exception as e:
                            sys_log(f"[DijitalPazarimAccount] Grup gönderim hatası ({g_title}): {e}")

                CHECKPOINT.record_blast_completed(interval_seconds=AD_INTERVAL_SECONDS)
                LAST_CYCLE_TIME = datetime.now().strftime("%H:%M:%S")
                next_due_dt = datetime.fromtimestamp(CHECKPOINT.state.get("next_blast_due_at", time.time() + AD_INTERVAL_SECONDS)).strftime("%H:%M:%S")
                sys_log(f"[DijitalPazarimAccount] Reklam turu tamamlandı. Sonraki tur için 60 dakika bekleniyor (Hedef saat: {next_due_dt}).")

                # 3. Tur bittiğinde de kalan saatlik hak varsa arka planda 1 yeni grup katılımı dene
                try:
                    if get_recent_joins_count(3600) < MAX_JOINS_PER_CYCLE and time.time() > JOIN_FLOOD_UNTIL:
                        await try_join_target_groups(max_joins=1)
                except Exception as je:
                    sys_log(f"[DijitalPazarimAccount] Tur sonu katılım deneme hatası: {je}")

                # 4. Bekleme döngüsü (60 dakika): Her 10 dakikada bir saatlik hak açıldıkça 1 yeni gruba katılmayı dener
                last_join_check = 0
                while AD_RUNNING:
                    rem = CHECKPOINT.get_remaining_seconds()
                    if rem <= 0:
                        break
                    LAST_BLAST_HEARTBEAT = time.time()
                    await asyncio.sleep(min(5, rem))
                    last_join_check += 5
                    if last_join_check >= 600:
                        last_join_check = 0
                        if get_recent_joins_count(3600) < MAX_JOINS_PER_CYCLE and time.time() > JOIN_FLOOD_UNTIL:
                            sys_log("[DijitalPazarimAccount] Bekleme arası periyodik grup kontrolü...")
                            try:
                                await try_join_target_groups(max_joins=1)
                            except Exception as pe:
                                sys_log(f"[DijitalPazarimAccount] Periyodik katılım hatası: {pe}")

            except Exception as e:
                sys_log(f"[DijitalPazarimAccount] Döngü hatası: {e}")
                await asyncio.sleep(30)

    async def supervised_ad_loop():
        while True:
            try:
                await ad_broadcast_loop()
            except Exception as loop_err:
                sys_log(f"[DijitalPazarimAccount] Süpervizör döngü kurtarma hatası: {loop_err}")
                await asyncio.sleep(15)

    asyncio.create_task(supervised_ad_loop())
    await client.run_until_disconnected()

def start_telethon_thread():
    global TELETHON_LOOP
    TELETHON_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(TELETHON_LOOP)
    try:
        TELETHON_LOOP.run_until_complete(run_telethon_account())
    except Exception as e:
        sys_log(f"[DijitalPazarimAccount] Thread hatası: {e}")

# ─────────────────────────────────────────────────────────────
# 4. WATCHDOG SUPERVISOR
# ─────────────────────────────────────────────────────────────

def watchdog_supervisor():
    """Background watchdog thread monitoring bot, telethon, and firestore coordination."""
    global t_bot, t_acc, WATCHDOG_STATS
    time.sleep(15)
    sys_log("[Watchdog] Sürekli gözetim, Firestore koordinasyonu ve otomatik kurtarma mekanizması aktif.")
    while True:
        try:
            now_str = datetime.now().strftime("%H:%M:%S")
            WATCHDOG_STATS["last_check"] = now_str

            # 1. Firestore Connection Check
            try:
                fs_ok = firestore_helper.remote_credentials_configured()
                WATCHDOG_STATS["firestore_connected"] = fs_ok
            except Exception:
                WATCHDOG_STATS["firestore_connected"] = False

            # 2. Check Bot Webhook Health
            check_webhook_health()

            # 3. Check Telethon Thread & Client Health
            telethon_thread_alive = (t_acc is not None and t_acc.is_alive())
            telethon_client_connected = bool(TELETHON_CLIENT and TELETHON_CLIENT.is_connected())
            WATCHDOG_STATS["telethon_alive"] = telethon_thread_alive
            WATCHDOG_STATS["telethon_connected"] = telethon_client_connected

            if not telethon_thread_alive:
                sys_log("[Watchdog] Telethon reklam hesabı iş parçacığı durmuş! Yeniden başlatılıyor...")
                t_acc = threading.Thread(target=start_telethon_thread, daemon=True, name="dp-account-worker")
                t_acc.start()
                WATCHDOG_STATS["telethon_restarts"] += 1

            # 4. Check Blast Heartbeat Age
            heartbeat_age = int(time.time() - LAST_BLAST_HEARTBEAT)
            WATCHDOG_STATS["blast_heartbeat_age"] = heartbeat_age
            if AD_RUNNING and heartbeat_age > 1200:
                sys_log(f"[Watchdog] Reklam döngüsü kalp atışı {heartbeat_age} saniyedir alınamadı! Döngü kilitlenmiş olabilir.")

            # 5. Checkpoint Status Sync
            WATCHDOG_STATS["next_blast_in_seconds"] = int(CHECKPOINT.get_remaining_seconds())

            time.sleep(20)
        except Exception as e:
            sys_log(f"[Watchdog] Hata: {e}")
            time.sleep(20)

# ─────────────────────────────────────────────────────────────
# 5. SERVICE RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Setup Telegram Bot Webhook & Menu Button (@DijitalPazarimBot)
    setup_telegram_bot()

    # 2. Start User Account Ad Worker Thread (+18595173039)
    t_acc = threading.Thread(target=start_telethon_thread, daemon=True, name="dp-account-worker")
    t_acc.start()

    # 3. Start Watchdog Supervisor Thread
    t_watchdog = threading.Thread(target=watchdog_supervisor, daemon=True, name="dp-watchdog")
    t_watchdog.start()

    port = int(os.environ.get("PORT", 5000))
    sys_log(f"[DijitalPazarim] Web servisi {port} portunda başlatılıyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
