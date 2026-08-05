"""Render'da calisan, SMM hesabi icin bagimsiz Telegram reklam yayincisi.

Bu servis 3 ana reklam botundan tamamen bagimsizdir.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

from flask import Flask, jsonify
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("smm-reklam")

STATE_FILE = Path("smm_delivery_state.json")
MIN_INTERVAL_SECONDS = 60 * 15  # En az 15 dakika
app = Flask(__name__)
status = {"state": "starting", "last_cycle": None, "last_error": None, "sent": 0}


def groups_from_env():
    raw = os.environ.get("SMM_TARGET_GROUPS", "")
    return list(dict.fromkeys(item.strip().lstrip("@") for item in raw.split(",") if item.strip()))


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(value):
    try:
        temporary = STATE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(STATE_FILE)
    except Exception as e:
        log.warning("State kaydetme hatasi: %s", e)


async def run_publisher():
    api_id = os.environ.get("TELEGRAM_API_ID", "31076280").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8").strip()

    while True:
        session = os.environ.get("SMM_STRING_SESSION", "").strip()
        message = os.environ.get("SMM_MESSAGE", "").strip()
        groups = groups_from_env()

        if not session:
            status.update(state="configuration_error", last_error="SMM_STRING_SESSION degiskeni eksik")
            log.warning("SMM_STRING_SESSION bekleniyor...")
            await asyncio.sleep(30)
            continue

        if not message or not groups:
            status.update(state="waiting_for_config", last_error="SMM_MESSAGE veya SMM_TARGET_GROUPS eksik")
            log.info("SMM_MESSAGE ve SMM_TARGET_GROUPS bekleniyor...")
            await asyncio.sleep(30)
            continue

        try:
            client = TelegramClient(StringSession(session), int(api_id), api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                status.update(state="configuration_error", last_error="Telegram oturumu yetkili degil (StringSession gecersiz)")
                await client.disconnect()
                await asyncio.sleep(60)
                continue

            requested_minutes = int(os.environ.get("SMM_INTERVAL_MINUTES", "60"))
            interval = max(MIN_INTERVAL_SECONDS, requested_minutes * 60)

            status.update(state="running", last_error=None)
            log.info("SMM yayincisi basladi. Hedef grup sayisi: %d, Aralik: %d sn", len(groups), interval)

            while True:
                current_groups = groups_from_env() or groups
                current_message = os.environ.get("SMM_MESSAGE", "").strip() or message

                delivery_state = load_state()
                now = time.time()
                for group in current_groups:
                    previous = float(delivery_state.get(group, 0))
                    if now - previous < interval:
                        continue
                    try:
                        entity = await client.get_entity(group)
                        await client.send_message(entity, current_message, link_preview=False)
                        delivery_state[group] = time.time()
                        save_state(delivery_state)
                        status["sent"] += 1
                        log.info("SMM Mesaj gonderildi -> @%s", group)
                        await asyncio.sleep(15)
                    except FloodWaitError as exc:
                        status["last_error"] = f"FloodWait: {exc.seconds}s"
                        log.warning("Flood wait @%s: %ss", group, exc.seconds)
                        await asyncio.sleep(exc.seconds + 5)
                    except RPCError as exc:
                        status["last_error"] = f"@{group}: {type(exc).__name__}"
                        log.warning("@%s gonderilemedi: %s", group, type(exc).__name__)
                    except Exception as exc:
                        status["last_error"] = f"@{group}: {type(exc).__name__}"
                        log.exception("Gonderim hatasi @%s", group)
                status["last_cycle"] = datetime.now(timezone.utc).isoformat()
                await asyncio.sleep(60)

        except Exception as exc:
            status.update(state="error", last_error=f"{type(exc).__name__}: {exc}")
            log.exception("SMM yayin hatasi, 30sn sonra tekrar denenecek")
            await asyncio.sleep(30)


def background_runner():
    try:
        asyncio.run(run_publisher())
    except Exception as exc:
        status.update(state="crashed", last_error=f"{type(exc).__name__}: {exc}")
        log.exception("SMM background runner durdu")


@app.get("/")
@app.get("/health")
def health():
    return jsonify(status)


if __name__ == "__main__":
    Thread(target=background_runner, daemon=True).start()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
