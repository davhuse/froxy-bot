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
from datetime import datetime
import threading
import asyncio
import time
import random
import requests
from pathlib import Path
from flask import Flask, send_from_directory, render_template, jsonify, request

sys.stdout.reconfigure(encoding='utf-8')

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

t_bot: threading.Thread | None = None
t_acc: threading.Thread | None = None

WATCHDOG_STATS = {
    "status": "active",
    "last_check": None,
    "bot_restarts": 0,
    "telethon_restarts": 0
}

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
    return jsonify({
        "status": "online",
        "ad_running": AD_RUNNING,
        "ad_interval_minutes": AD_INTERVAL_SECONDS // 60,
        "total_ads_sent": TOTAL_ADS_SENT,
        "last_cycle": LAST_CYCLE_TIME or "Henüz tamamlanmadı",
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
            "bot_alive": t_bot.is_alive() if t_bot else False,
            "telethon_alive": t_acc.is_alive() if t_acc else False,
            "bot_restarts": WATCHDOG_STATS.get("bot_restarts", 0),
            "telethon_restarts": WATCHDOG_STATS.get("telethon_restarts", 0)
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

def get_product_summary() -> str:
    prod_file = MINIAPP_DIR / "products_db.json"
    if not prod_file.exists():
        return "Güncel stoklar mağazamızda listelenmektedir."
    try:
        data = json.loads(prod_file.read_text(encoding="utf-8"))
        lines = ["DİJİTAL PAZARIM GÜNCEL FİYAT LİSTESİ:"]
        for p in data:
            lines.append(f"• {p['title']}: {p['price']}")
        return "\n".join(lines)
    except Exception:
        return "Güncel ürünleri mağazadan inceleyebilirsiniz."

def telegram_bot_worker():
    """Background polling loop for @DijitalPazarimBot."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN":
        sys_log("[DijitalPazarimBot] Token bulunamadı, bot başlatılamıyor.")
        return

    sys_log(f"[DijitalPazarimBot] Bot servisi başlatılıyor (@DijitalPazarimBot)...")
    
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

    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 20},
                timeout=25
            )
            if r.status_code == 200:
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    handle_telegram_update(update)
            elif r.status_code == 409:
                sys_log("[DijitalPazarimBot] 409 Conflict, 5 saniye bekleniyor...")
                time.sleep(5)
            else:
                time.sleep(2)
        except Exception as e:
            time.sleep(3)

def handle_telegram_update(update: dict):
    try:
        # 1. Callback query
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            cb_id = cb.get("id")
            cb_data = cb.get("data", "")
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
            
            if cb_data == "list_prices":
                text = get_product_summary()
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}}],
                        [{"text": "Canlı Destek", "callback_data": "support_info"}]
                    ]
                }
                send_bot_message(chat_id, text, keyboard)
            elif cb_data == "support_info":
                text = (
                    "DİJİTAL PAZARIM MÜŞTERİ DESTEĞİ\n\n"
                    "Siparişleriniz, teslimat veya kupon kodları ile ilgili sorularınızı doğrudan bu sohbete yazabilirsiniz.\n"
                    "Yetkili ekibimiz mesajınızı inceleyip anında dönüş sağlayacaktır.\n\n"
                    "Referanslarımız mevcuttur. Güvenli alışverişler dileriz."
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}}]
                    ]
                }
                send_bot_message(chat_id, text, keyboard)
            return

        # 2. Text message
        if "message" in update and "text" in update["message"]:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg["text"].strip()
            first_name = msg.get("from", {}).get("first_name", "Değerli Müşterimiz")

            if text.startswith("/start") or text.startswith("/magaza"):
                sys_log(f"[DijitalPazarimBot] /start komutu alındı -> Chat ID: {chat_id} ({first_name})")
                welcome_text = (
                    f"Merhaba {first_name},\n\n"
                    "Dijital Pazarım'a hoş geldiniz.\n"
                    "İndirim kuponları, market & yemek kodları ve premium dijital lisansları "
                    "aşağıdaki butondan mağazamıza giriş yaparak anında ve güvenle temin edebilirsiniz."
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}}],
                        [
                            {"text": "Fiyat Listesi", "callback_data": "list_prices"},
                            {"text": "Canlı Destek", "callback_data": "support_info"}
                        ]
                    ]
                }
                send_bot_message(chat_id, welcome_text, keyboard)
            elif text.startswith("/fiyatlar"):
                summary = get_product_summary()
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}}]
                    ]
                }
                send_bot_message(chat_id, summary, keyboard)
            elif text.startswith("/destek"):
                destek_text = (
                    "Müşteri Hizmetleri:\n"
                    "Mesajınızı bu sohbet üzerinden iletebilirsiniz. Ekibimiz en kısa sürede yanıt verecektir."
                )
                send_bot_message(chat_id, destek_text)
            else:
                sys_log(f"[DijitalPazarimBot] Müşteri mesajı: {text[:40]}... -> Chat ID: {chat_id}")
                reply = (
                    "Mesajınız müşteri ekibimize iletilmiştir. "
                    "Ürünleri incelemek ve anında sipariş vermek için mağazamızı ziyaret edebilirsiniz."
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": MINIAPP_URL}}]
                    ]
                }
                send_bot_message(chat_id, reply, keyboard)

    except Exception as e:
        sys_log(f"[DijitalPazarimBot] Mesaj işleme hatası: {e}")

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
JOIN_FLOOD_UNTIL: float = 0.0

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

    # 1. Telegram Resmi Güvenlik / Giriş Kodu Yakalayıcı (777000)
    @client.on(events.NewMessage(incoming=True, chats=777000))
    async def handle_official_telegram_code(event):
        msg_text = event.raw_text or ""
        sys_log(f"🚨 [GİRİŞ KODU YAKALANDI] Dijital Pazarım hesabına resmi kod geldi:\n{msg_text}")
        try:
            alert = (
                f"🚨 <b>[DİJİTAL PAZARIM GİRİŞ KODU]</b>\n\n"
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

    # 3. Background Ad Broadcast & Auto-Join loop (Ana projedeki tam mantık ve akıl)
    async def ad_broadcast_loop():
        global TOTAL_ADS_SENT, LAST_CYCLE_TIME, JOINED_GROUPS_COUNT, JOIN_FLOOD_UNTIL
        await asyncio.sleep(20) # Initial startup buffer
        templates = load_ad_templates()
        template_idx = 0

        while True:
            try:
                if not AD_RUNNING:
                    await asyncio.sleep(5)
                    continue

                if not templates:
                    templates = load_ad_templates()
                
                if templates:
                    current_ad = templates[template_idx % len(templates)]
                    template_idx += 1

                    # 1. Mevcut diyalogları ve üye olunan grupları tara
                    dialogs = await client.get_dialogs(limit=100)
                    joined_groups = {}
                    joined_usernames = set()
                    for d in dialogs:
                        if d.is_group:
                            joined_groups[d.id] = d
                            uname = getattr(d.entity, 'username', None)
                            if uname:
                                joined_usernames.add(uname.lower())
                    
                    JOINED_GROUPS_COUNT = len(joined_groups)

                    # 2. gruplar.txt listesinden güvenli grup katılımı (Ana projedeki saatlik limit ve 3-6 dk bekleme)
                    now_ts = time.time()
                    if now_ts < JOIN_FLOOD_UNTIL:
                        wait_sec = int(JOIN_FLOOD_UNTIL - now_ts)
                        sys_log(f"[DijitalPazarimAccount] ⏳ Join FloodWait aktif ({wait_sec} sn kaldı), katılım adımı atlandı.")
                    else:
                        current_recent = get_recent_joins_count(3600)
                        if current_recent >= MAX_JOINS_PER_CYCLE:
                            sys_log(f"[DijitalPazarimAccount] 🔒 Saatlik katılım limiti ({MAX_JOINS_PER_CYCLE}/saat) doldu. Katılım adımı güvenle atlandı.")
                        else:
                            targets = load_target_groups()
                            blacklist = load_blacklist()
                            
                            not_joined = []
                            for target_name in targets:
                                t_clean = target_name.lower().lstrip('@')
                                if t_clean and t_clean not in blacklist and t_clean not in joined_usernames and t_clean not in FAILED_JOIN_TARGETS:
                                    not_joined.append(t_clean)
                            
                            if not_joined:
                                sys_log(f"[DijitalPazarimAccount] 🔍 {len(not_joined)} hedefe henüz üye değiliz (Kalan saatlik hak: {MAX_JOINS_PER_CYCLE - current_recent}). Güvenli katılım deneniyor...")
                                for t_clean in not_joined:
                                    if not AD_RUNNING:
                                        break
                                    try:
                                        sys_log(f"[DijitalPazarimAccount] Hedef gruba katılınıyor: @{t_clean}")
                                        entity = await client.get_entity(t_clean)
                                        await client(JoinChannelRequest(entity))
                                        joined_usernames.add(t_clean)
                                        joined_groups[entity.id] = entity
                                        JOINED_GROUPS_COUNT = len(joined_groups)
                                        RECENT_JOIN_TIMESTAMPS.append(time.time())
                                        sys_log(f"[DijitalPazarimAccount] ✅ Gruba başarıyla katıldı: @{t_clean}")
                                        
                                        # Ana projedeki gibi 3-6 dakika güvenli bekleme (ard arda katılımı engeller)
                                        join_delay = random.randint(JOIN_DELAY_MIN_SECONDS, JOIN_DELAY_MAX_SECONDS)
                                        sys_log(f"[DijitalPazarimAccount] 🛡️ Anti-flood koruması: Sonraki işlem öncesi {join_delay} sn bekleniyor...")
                                        await asyncio.sleep(join_delay)
                                        break # Bir döngüde en fazla 1 gruba katıl
                                    except FloodWaitError as fwe:
                                        JOIN_FLOOD_UNTIL = time.time() + fwe.seconds + 60
                                        sys_log(f"[DijitalPazarimAccount] ⚠️ Join FloodWait: {fwe.seconds} sn. Katılım duraklatıldı.")
                                        break
                                    except (UserBannedInChannelError, ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError) as e:
                                        FAILED_JOIN_TARGETS.add(t_clean)
                                        sys_log(f"[DijitalPazarimAccount] ⛔ Grup kalıcı olarak atlandı (@{t_clean}): {type(e).__name__}")
                                    except Exception as e:
                                        err_msg = str(e).lower()
                                        if any(k in err_msg for k in ("private", "banned", "forbidden", "admin", "request")):
                                            FAILED_JOIN_TARGETS.add(t_clean)
                                        sys_log(f"[DijitalPazarimAccount] ⚠️ Gruba katılma hatası (@{t_clean}): {e}")

                    # 3. Reklam gönderim döngüsü (30-45 saniye grup aralığı)
                    sys_log(f"[DijitalPazarimAccount] Reklam döngüsü başladı ({len(joined_groups)} aktif grup)...")

                    for gid, group in list(joined_groups.items()):
                        if not AD_RUNNING:
                            sys_log("[DijitalPazarimAccount] Gönderim döngü esnasında durduruldu.")
                            break

                        g_title = getattr(group, 'name', str(gid))
                        g_uname = getattr(getattr(group, 'entity', None), 'username', '') or ''
                        if g_uname.lower() in blacklist:
                            continue

                        try:
                            target_dest = group.id if hasattr(group, 'id') else gid
                            await client.send_message(target_dest, current_ad)
                            TOTAL_ADS_SENT += 1
                            sys_log(f"[DijitalPazarimAccount] Reklam paylaşıldı -> {g_title}")
                            await asyncio.sleep(random.randint(GROUP_DELAY_MIN_SECONDS, GROUP_DELAY_MAX_SECONDS))
                        except FloodWaitError as fwe:
                            sys_log(f"[DijitalPazarimAccount] FloodWait: {fwe.seconds} saniye bekleniyor...")
                            await asyncio.sleep(fwe.seconds + 5)
                        except SlowModeWaitError as sm:
                            sys_log(f"[DijitalPazarimAccount] SlowMode ({g_title}): {sm.seconds} saniye.")
                            await asyncio.sleep(5)
                        except ChatWriteForbiddenError:
                            sys_log(f"[DijitalPazarimAccount] Yazma izni yok, atlandı -> {g_title}")
                        except Exception as e:
                            sys_log(f"[DijitalPazarimAccount] Grup gönderim hatası ({g_title}): {e}")

                LAST_CYCLE_TIME = datetime.now().strftime("%H:%M:%S")
                sys_log("[DijitalPazarimAccount] Reklam turu tamamlandı. Sonraki döngü bekleniyor...")
                
                # Bekleme döngüsü (panelden durdurulduğunda hemen yanıt verir)
                elapsed = 0
                while elapsed < AD_INTERVAL_SECONDS and AD_RUNNING:
                    await asyncio.sleep(2)
                    elapsed += 2

            except Exception as e:
                sys_log(f"[DijitalPazarimAccount] Döngü hatası: {e}")
                await asyncio.sleep(30)

    asyncio.create_task(ad_broadcast_loop())
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
    """Background watchdog thread monitoring bot and telethon workers."""
    global t_bot, t_acc
    time.sleep(15)
    sys_log("[Watchdog] Sürekli gözetim ve otomatik kurtarma mekanizması aktif.")
    while True:
        try:
            WATCHDOG_STATS["last_check"] = datetime.now().strftime("%H:%M:%S")
            # 1. Check Bot Thread
            if t_bot is None or not t_bot.is_alive():
                sys_log("⚠️ [Watchdog] @DijitalPazarimBot iş parçacığı durmuş! Yeniden başlatılıyor...")
                t_bot = threading.Thread(target=telegram_bot_worker, daemon=True, name="dp-bot-worker")
                t_bot.start()
                WATCHDOG_STATS["bot_restarts"] += 1
            
            # 2. Check Telethon Thread
            if t_acc is None or not t_acc.is_alive():
                sys_log("⚠️ [Watchdog] Telethon reklam hesabı iş parçacığı durmuş! Yeniden başlatılıyor...")
                t_acc = threading.Thread(target=start_telethon_thread, daemon=True, name="dp-account-worker")
                t_acc.start()
                WATCHDOG_STATS["telethon_restarts"] += 1

            time.sleep(15)
        except Exception as e:
            sys_log(f"[Watchdog] Hata: {e}")
            time.sleep(15)

# ─────────────────────────────────────────────────────────────
# 5. SERVICE RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Start Bot Polling Thread (@DijitalPazarimBot)
    t_bot = threading.Thread(target=telegram_bot_worker, daemon=True, name="dp-bot-worker")
    t_bot.start()

    # 2. Start User Account Ad Worker Thread (+18595173039)
    t_acc = threading.Thread(target=start_telethon_thread, daemon=True, name="dp-account-worker")
    t_acc.start()

    # 3. Start Watchdog Supervisor Thread
    t_watchdog = threading.Thread(target=watchdog_supervisor, daemon=True, name="dp-watchdog")
    t_watchdog.start()

    port = int(os.environ.get("PORT", 5000))
    sys_log(f"[DijitalPazarim] Web servisi {port} portunda başlatılıyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
