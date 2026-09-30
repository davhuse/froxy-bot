# -*- coding: utf-8 -*-
"""
Dijital Pazarım — Dedicated Independent Service
Runs exclusively for Dijital Pazarım:
- Serves Dijital Pazarım Canlı Servis Paneli on root '/'
- Serves Dijital Pazarım Mini App on '/dp' and '/app'
- Telegram Bot (@DijitalPazarimBot) runner with WebApp menu button to '/dp'
- Telethon Ad Sender loop for +18595173039 (@DijitalPazarimm)
- Independent live logs and status endpoints
Zero dependency on KeyVadi, LisansArena, or Froxy.
"""

from __future__ import annotations
import os
import sys
import json
import collections
from datetime import datetime
import threading
import time
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

# In-memory Live Log Buffer
LOG_BUFFER = collections.deque(maxlen=200)

def sys_log(message: str):
    """Outputs to stdout and records in log buffer."""
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {message}"
    print(formatted, flush=True)
    LOG_BUFFER.append(formatted)

# Initial log
sys_log("Dijital Pazarım Bağımsız Servisi başlatıldı.")

# ─────────────────────────────────────────────────────────────
# 1. WEB & CANLI SERVİS PANELİ / MINI APP ROUTES
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
    return jsonify({
        "status": "online",
        "brand": "Dijital Pazarım",
        "bot": "@DijitalPazarimBot",
        "ad_account": "+18595173039",
        "domain": PUBLIC_BASE_URL,
        "miniapp_url": MINIAPP_URL,
        "active_products": prod_count,
        "system": "standalone_dijital_pazarim_v2"
    })

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
            
            # Answer callback
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
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.errors import FloodWaitError

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
    sys_log(f"[DijitalPazarimAccount] Aktif Hesap: {me.first_name} (@{me.username}) - {me.phone}")

    # Auto DM Reply: Directs private inquiries to @DijitalPazarimBot
    dm_replied_users = set()

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_private_dm(event):
        sender_id = event.sender_id
        if sender_id == me.id or sender_id == 777000 or sender_id in dm_replied_users:
            return
        dm_replied_users.add(sender_id)
        reply_text = (
            "Merhaba,\n\n"
            "İndirim kuponları, market & yemek kodları ve hesap alımları için "
            "doğrudan resmi mağaza botumuz @DijitalPazarimBot üzerinden anında sipariş verebilirsiniz.\n\n"
            "Referanslarımız mevcuttur. Keyifli alışverişler dileriz."
        )
        try:
            await event.reply(reply_text)
            sys_log(f"[DijitalPazarimAccount] DM yönlendirmesi gönderildi -> Kullanıcı ID: {sender_id}")
        except Exception as e:
            sys_log(f"[DijitalPazarimAccount] DM yanıt hatası: {e}")

    # Background Ad Broadcast loop
    async def ad_broadcast_loop():
        await asyncio.sleep(20) # Initial startup buffer
        templates = load_ad_templates()
        template_idx = 0

        while True:
            try:
                if not templates:
                    templates = load_ad_templates()
                
                if templates:
                    current_ad = templates[template_idx % len(templates)]
                    template_idx += 1

                    # Get active trade dialogs
                    dialogs = await client.get_dialogs(limit=50)
                    target_groups = [d for d in dialogs if d.is_group]

                    sys_log(f"[DijitalPazarimAccount] Reklam döngüsü başladı ({len(target_groups)} grup hedefli)...")

                    for group in target_groups:
                        try:
                            await client.send_message(group.id, current_ad)
                            sys_log(f"[DijitalPazarimAccount] Reklam paylaşıldı -> {group.name}")
                            await asyncio.sleep(30) # Delay between groups
                        except FloodWaitError as fwe:
                            sys_log(f"[DijitalPazarimAccount] FloodWait: {fwe.seconds} saniye bekleniyor...")
                            await asyncio.sleep(fwe.seconds + 5)
                        except Exception as e:
                            sys_log(f"[DijitalPazarimAccount] Grup gönderim hatası ({group.name}): {e}")

                sys_log("[DijitalPazarimAccount] Reklam turu tamamlandı. Sonraki döngü 60 dakika sonra.")
                # Interval between broadcast rounds (60 minutes)
                await asyncio.sleep(3600)

            except Exception as e:
                sys_log(f"[DijitalPazarimAccount] Döngü hatası: {e}")
                await asyncio.sleep(60)

    asyncio.create_task(ad_broadcast_loop())
    await client.run_until_disconnected()

def start_telethon_thread():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_telethon_account())
    except Exception as e:
        sys_log(f"[DijitalPazarimAccount] Thread hatası: {e}")

# ─────────────────────────────────────────────────────────────
# 4. SERVICE RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Start Bot Polling Thread (@DijitalPazarimBot)
    t_bot = threading.Thread(target=telegram_bot_worker, daemon=True, name="dp-bot-worker")
    t_bot.start()

    # 2. Start User Account Ad Worker Thread (+18595173039)
    t_acc = threading.Thread(target=start_telethon_thread, daemon=True, name="dp-account-worker")
    t_acc.start()

    port = int(os.environ.get("PORT", 5000))
    sys_log(f"[DijitalPazarim] Web servisi {port} portunda başlatılıyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
