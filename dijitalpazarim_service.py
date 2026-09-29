# -*- coding: utf-8 -*-
"""
Dijital Pazarım — Dedicated Independent Service
Runs exclusively for Dijital Pazarım:
- Serves Dijital Pazarım Mini App on root '/'
- Telegram Bot (@DijitalPazarimBot) runner
- Independent status and webhook endpoints
Zero dependency on KeyVadi, LisansArena, or Froxy.
"""

from __future__ import annotations
import os
import sys
import json
import threading
import time
import requests
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
MINIAPP_DIR = BASE_DIR / "miniapp_dijitalpazarim"
STATIC_DIR = BASE_DIR / "static"
MESSAGES_DIR = BASE_DIR / "messages"

app = Flask(__name__, static_folder=str(MINIAPP_DIR), static_url_path="")

BOT_TOKEN = os.environ.get("DIJITALPAZARIM_BOT_TOKEN", "8753762842:AAHH_uLartBSDD7hJ2ikwaDtoCYpWMziv9g").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://dijital-pazarim-service-production.up.railway.app").rstrip("/")

# ─────────────────────────────────────────────────────────────
# 1. WEB / MINI APP ROUTES (Dedicated exclusively to Dijital Pazarım)
# ─────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/dp")
@app.route("/dp/")
def root_index():
    return send_from_directory(str(MINIAPP_DIR), "index.html")

@app.route("/products_db.json")
@app.route("/dp/products_db.json")
def get_products():
    prod_file = MINIAPP_DIR / "products_db.json"
    if prod_file.exists():
        return send_from_directory(str(MINIAPP_DIR), "products_db.json", mimetype="application/json")
    return jsonify([]), 404

@app.route("/assets/<path:filepath>")
@app.route("/dp/assets/<path:filepath>")
def serve_assets(filepath):
    return send_from_directory(str(MINIAPP_DIR / "assets"), filepath)

@app.route("/static/<path:filepath>")
def serve_static(filepath):
    return send_from_directory(str(STATIC_DIR), filepath)

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
        "domain": PUBLIC_BASE_URL,
        "active_products": prod_count,
        "system": "standalone_dijital_pazarim_v1"
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
        print("[DijitalPazarimBot] Token bulunamadı, bot başlatılamıyor.")
        return

    print(f"[DijitalPazarimBot] Bot servisi başlatılıyor... (@DijitalPazarimBot)")
    
    # 1. Update Menu Button to Root Mini App
    try:
        btn = {
            "type": "web_app",
            "text": "Mağazayı Aç",
            "web_app": {
                "url": PUBLIC_BASE_URL
            }
        }
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton",
            json={"menu_button": json.dumps(btn)},
            timeout=10
        )
        print(f"[DijitalPazarimBot] Chat menu button güncellendi -> {PUBLIC_BASE_URL}")
    except Exception as e:
        print(f"[DijitalPazarimBot] Menu button hatası: {e}")

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
                print("[DijitalPazarimBot] 409 Conflict, 5 saniye bekleniyor...")
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
                        [{"text": "Mağazayı Aç", "web_app": {"url": PUBLIC_BASE_URL}}],
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
                        [{"text": "Mağazayı Aç", "web_app": {"url": PUBLIC_BASE_URL}}]
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
                welcome_text = (
                    f"Merhaba {first_name},\n\n"
                    "Dijital Pazarım'a hoş geldiniz.\n"
                    "İndirim kuponları, market & yemek kodları ve premium dijital lisansları "
                    "aşağıdaki butondan mağazamıza giriş yaparak anında ve güvenle temin edebilirsiniz."
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": PUBLIC_BASE_URL}}],
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
                        [{"text": "Mağazayı Aç", "web_app": {"url": PUBLIC_BASE_URL}}]
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
                # General query reply
                reply = (
                    "Mesajınız müşteri ekibimize iletilmiştir. "
                    "Ürünleri incelemek ve anında sipariş vermek için mağazamızı ziyaret edebilirsiniz."
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Mağazayı Aç", "web_app": {"url": PUBLIC_BASE_URL}}]
                    ]
                }
                send_bot_message(chat_id, reply, keyboard)

    except Exception as e:
        print(f"[DijitalPazarimBot] Mesaj işleme hatası: {e}")

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
            json=payload,
            timeout=8
        )
    except Exception as e:
        print(f"[DijitalPazarimBot] sendMessage hatası: {e}")

# ─────────────────────────────────────────────────────────────
# 3. SERVICE RUNNER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Start bot polling in background thread
    t = threading.Thread(target=telegram_bot_worker, daemon=True, name="dp-bot-worker")
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"[DijitalPazarim] Web servisi {port} portunda başlatılıyor (Yalnızca Dijital Pazarım)...")
    app.run(host="0.0.0.0", port=port, debug=False)
