"""
firebase_companion.py  –  Reklam Botu Firebase Köprüsü
──────────────────────────────────────────────────────
Her 5 saniyede:
  • otomatik_katil.py sürecini başlatır/durdurur (komut gelirse)
  • bot durumunu Firestore'a yazar  (reklam/status)
  • bot_log.txt'yi Firestore'a yazar (reklam/logs)
  • progress.txt & blacklist.txt sayılarını günceller
  • Firestore'daki mesajı message.txt'ye uygular (reklam/message)
  • auto_keep_running: bot kapanırsa otomatik yeniden başlatır

Kurulum:
  pip install requests psutil
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import requests

# ── Ayarlar ──────────────────────────────────────────────────────────────────
API_KEY    = os.environ.get("FIREBASE_API_KEY", "").strip()
PROJECT_ID = "bot-2-63772"
BASE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

BASE_DIR       = Path(__file__).resolve().parent
BOT_SCRIPT     = BASE_DIR / "otomatik_katil.py"
LOG_FILE       = BASE_DIR / "bot_log.txt"
MESSAGE_FILE   = BASE_DIR / "message.txt"
PROGRESS_FILE  = BASE_DIR / "progress.txt"
BLACKLIST_FILE = BASE_DIR / "blacklist.txt"

POLL_INTERVAL = 5
MAX_LOG_LINES = 120
TOTAL_GROUPS  = 110  # gruplar listesinin yaklaşık uzunluğu

_auto_keep: bool = False
_bot_proc: subprocess.Popen | None = None


# ── Firestore yardımcıları ────────────────────────────────────────────────────
def _url(col: str, doc: str) -> str:
    return f"{BASE_URL}/{col}/{doc}?key={API_KEY}"

def fs_get(col: str, doc: str) -> dict | None:
    try:
        r = requests.get(_url(col, doc), timeout=10)
        return r.json().get("fields", {}) if r.status_code == 200 else None
    except Exception:
        return None

def fs_set(col: str, doc: str, fields: dict) -> bool:
    try:
        r = requests.patch(_url(col, doc), json={"fields": fields}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def v_str(v): return {"stringValue": str(v)}
def v_bool(v): return {"booleanValue": bool(v)}
def v_int(v): return {"integerValue": str(int(v))}
def get_str(f, k, d=""): return f.get(k, {}).get("stringValue", d)
def get_bool(f, k, d=False): return f.get(k, {}).get("booleanValue", d)


# ── Süreç yönetimi ───────────────────────────────────────────────────────────
def find_bot_process() -> psutil.Process | None:
    global _bot_proc
    if _bot_proc is not None:
        if _bot_proc.poll() is None:
            try:
                return psutil.Process(_bot_proc.pid)
            except Exception:
                pass
        _bot_proc = None
    return None

def start_bot() -> str:
    global _bot_proc
    if find_bot_process():
        return "Bot zaten çalışıyor."
    if not BOT_SCRIPT.exists():
        return "otomatik_katil.py bulunamadı."
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'='*40}\n🚀 Bot başlatıldı: {datetime.now():%Y-%m-%d %H:%M:%S}\n{'='*40}\n")
    out = LOG_FILE.open("a", encoding="utf-8", buffering=1)
    _bot_proc = subprocess.Popen(
        [sys.executable, str(BOT_SCRIPT)],
        cwd=str(BASE_DIR),
        stdout=out, stderr=subprocess.STDOUT,
        creationflags=flags, env=env
    )
    return f"Bot başlatıldı (PID {_bot_proc.pid})."

def stop_bot() -> str:
    global _bot_proc
    proc = find_bot_process()
    if not proc:
        return "Çalışan bot yok."
    try:
        for child in proc.children(recursive=True):
            try: child.terminate()
            except: pass
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try: proc.kill()
        except: pass
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n🛑 Bot durduruldu: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
    _bot_proc = None
    return "Bot durduruldu."


# ── Yardımcı okuyucular ───────────────────────────────────────────────────────
def read_progress() -> int:
    if not PROGRESS_FILE.exists():
        return 0
    try:
        return len([l for l in PROGRESS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()])
    except Exception:
        return 0

def read_blacklist() -> int:
    if not BLACKLIST_FILE.exists():
        return 0
    try:
        return len([l for l in BLACKLIST_FILE.read_text(encoding="utf-8").splitlines() if l.strip()])
    except Exception:
        return 0

def read_log_tail() -> str:
    if not LOG_FILE.exists():
        return ""
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-MAX_LOG_LINES:])
    except Exception:
        return ""

def sync_message_from_firestore() -> None:
    fields = fs_get("reklam", "message")
    if not fields:
        return
    content = get_str(fields, "content")
    if not content:
        return
    try:
        current = MESSAGE_FILE.read_text(encoding="utf-8") if MESSAGE_FILE.exists() else ""
        if current.strip() != content.strip():
            MESSAGE_FILE.write_text(content, encoding="utf-8")
            print(f"[{datetime.now():%H:%M:%S}] Mesaj güncellendi (Firestore → message.txt)")
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] Mesaj sync hatası: {e}")

def init_message_in_firestore() -> None:
    if not MESSAGE_FILE.exists():
        return
    fields = fs_get("reklam", "message")
    if fields and get_str(fields, "content"):
        return
    try:
        content = MESSAGE_FILE.read_text(encoding="utf-8")
        fs_set("reklam", "message", {"content": v_str(content)})
        print(f"[{datetime.now():%H:%M:%S}] message.txt → Firestore'a yüklendi.")
    except Exception:
        pass


# ── Push fonksiyonları ────────────────────────────────────────────────────────
def push_status() -> None:
    proc = find_bot_process()
    running = proc is not None
    pid_str = str(proc.pid) if running else "-"
    uptime_str = "-"
    started_at = "-"
    if running:
        try:
            dt = datetime.fromtimestamp(proc.create_time())
            started_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - dt
            total = int(delta.total_seconds())
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            pass

    fs_set("reklam", "status", {
        "running":           v_bool(running),
        "pid":               v_str(pid_str),
        "started_at":        v_str(started_at),
        "uptime":            v_str(uptime_str),
        "companion_online":  v_bool(True),
        "last_updated":      v_str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "progress_done":     v_int(read_progress()),
        "progress_total":    v_int(TOTAL_GROUPS),
        "blacklist_count":   v_int(read_blacklist()),
        "auto_keep_running": v_bool(_auto_keep),
    })

def push_logs() -> None:
    fs_set("reklam", "logs", {"content": v_str(read_log_tail())})


# ── Komut işleyici ────────────────────────────────────────────────────────────
def handle_command() -> None:
    global _auto_keep
    fields = fs_get("reklam", "command")
    if not fields:
        return
    if get_bool(fields, "processed", True):
        return
    action = get_str(fields, "action")
    print(f"[{datetime.now():%H:%M:%S}] Komut: {action}")

    if action == "start":
        print("  →", start_bot())
    elif action == "stop":
        print("  →", stop_bot())
    elif action == "restart":
        print("  →", stop_bot())
        time.sleep(1)
        print("  →", start_bot())
    elif action == "auto_on":
        _auto_keep = True
        print("  → Auto-restart AÇILDI")
    elif action == "auto_off":
        _auto_keep = False
        print("  → Auto-restart KAPATILDI")

    fs_set("reklam", "command", {
        "action":    v_str(action),
        "issued_at": fields.get("issued_at", v_str("")),
        "processed": v_bool(True),
    })


# ── Ana döngü ────────────────────────────────────────────────────────────────
def main():
    print("=" * 52)
    print("  Reklam Botu  Firebase Companion")
    print(f"  Proje : {PROJECT_ID}")
    print(f"  Klasör: {BASE_DIR}")
    print("=" * 52)

    init_message_in_firestore()

    tick = 0
    while True:
        try:
            handle_command()

            if _auto_keep and find_bot_process() is None:
                print(f"[{datetime.now():%H:%M:%S}] Auto-restart: bot yeniden başlatılıyor...")
                start_bot()

            sync_message_from_firestore()
            push_status()
            if tick % 2 == 0:
                push_logs()
            tick += 1
        except KeyboardInterrupt:
            print("\nCompanion durduruluyor...")
            try:
                fs_set("reklam", "status", {"companion_online": v_bool(False)})
            except Exception:
                pass
            break
        except Exception as exc:
            print(f"[{datetime.now():%H:%M:%S}] Hata: {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
