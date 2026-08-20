from flask import Flask, render_template, request, jsonify, redirect, abort
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import subprocess
import os
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
import json
import re
import threading
import time
import asyncio
try:
    import psutil
except ImportError:  # Wasmer Edge/WASIX does not provide a psutil wheel.
    psutil = None
import socket
import hmac
import base64
import hashlib
import atexit
import signal
from sales_metrics import record_event, summarize as summarize_sales
from sales_conversion import catalog_refresh_status, cta_experiment_status, parse_purchase_token, product_by_id, purchase_target_url, refresh_configured_catalogs
from blast_scheduler import load_blast_snapshot
from shopier_orders import ingest_shopier_order, reconcile_configured_orders
from group_policy import load_policies, moderation_snapshot
from lisansarena_store import la as lisansarena_store_blueprint, start_store_worker

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
app.register_blueprint(lisansarena_store_blueprint)

SHOPIER_CALLBACK_SECRET = os.environ.get('SHOPIER_CALLBACK_SECRET', '').strip()
FROXY_ENABLED = True

is_render = os.environ.get('RENDER', '').lower() == 'true'

app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY'),
    SESSION_COOKIE_SECURE=is_render,
    SESSION_COOKIE_HTTPONLY=True,
    # Telegram Web opens Mini Apps inside a cross-site iframe. Lax cookies are
    # accepted by auth but omitted from the following API calls.
    SESSION_COOKIE_SAMESITE='None' if is_render else 'Lax',
    SESSION_COOKIE_PARTITIONED=is_render,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    MAX_CONTENT_LENGTH=1024 * 1024,
    MAX_FORM_MEMORY_SIZE=256 * 1024,
    MAX_FORM_PARTS=100,
)

@app.before_request
def protect_shopier_callback():
    """Keep the external Shopier callback secret while the local panel stays keyless."""
    if request.path != '/api/shopier/callback':
        return None
    if not SHOPIER_CALLBACK_SECRET:
        print('[Security] Shopier callback is disabled: secret is missing.')
        return jsonify({'error': 'Callback is not configured'}), 503
    signature = request.headers.get('Shopier-Signature', '').strip()
    supplied = request.args.get('secret') or request.headers.get('X-Shopier-Secret', '')
    valid = False
    if signature:
        digest = hmac.new(
            SHOPIER_CALLBACK_SECRET.encode('utf-8'), request.get_data(cache=True), hashlib.sha256
        ).digest()
        candidates = {
            digest.hex(),
            base64.b64encode(digest).decode('ascii'),
            base64.urlsafe_b64encode(digest).decode('ascii').rstrip('='),
        }
        valid = any(hmac.compare_digest(signature, candidate) for candidate in candidates)
    elif supplied:
        # Backward-compatible during migration from the old OSB callback.
        valid = hmac.compare_digest(str(supplied), SHOPIER_CALLBACK_SECRET)
    if not valid:
        print('[Security] Shopier callback rejected an invalid secret.')
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@app.before_request
def protect_privileged_panel_api():
    protected = (
        '/api/group-status', '/api/config', '/api/account-restrictions',
        '/api/start', '/api/stop', '/api/lisansarena/start', '/api/lisansarena/stop',
        '/api/ad-smoke/start', '/api/ad-smoke/status',
        '/api/supplier-opportunities', '/api/procurement',
        '/api/sales/group-candidates',
    )
    if request.path not in protected:
        if request.path.startswith('/api/procurement/'):
            pass
        else:
            return None
    expected = os.environ.get('PANEL_ADMIN_TOKEN', '').strip()
    supplied = request.headers.get('X-Admin-Token', '').strip()
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault('Cache-Control', 'no-store')
    if request.path.startswith('/la/') or request.path.startswith('/api/la/') or request.path == '/api/shopier/lisansarena/webhook':
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' https://telegram.org; "
            "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org; "
            "base-uri 'none'; form-action 'self'"
        )
        response.headers.pop('X-Frame-Options', None)
    return response


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


# Reklam botu (otomatik_katil.py) her slot icin birden fazla config anahtarini
# oncelik sirasiyla okur.  Panelden yeni bir oturum baglandiginda sadece taban
# anahtari yazmak yetmiyordu: eski "_new"/"_final" kopyalari daha yuksek
# oncelikli oldugu icin olu oturum kullanilmaya devam ediyordu.  Bu yuzden
# yazma islemi butun varyantlari birlikte gunceller.
SLOT_SESSION_KEYS = {
    "1": ["ad_string_session", "ad_string_session_new", "ad_string_session_final"],
    "2": ["ad_string_session2", "ad_string_session2_new", "ad_string_session2_final",
          "ad_string_session_2"],
    "3": ["ad_string_session3", "ad_string_session3_new", "ad_string_session3_final",
          "ad_string_session_3"],
}

# Render'da kalici olan degerler bunlar; dosya sistemi her deploy'da sifirlandigi
# icin panelden baglanan oturumun ayrica bu ortam degiskenine yazilmasi gerekir.
SLOT_ENV_VARS = {
    "1": "AD_STRING_SESSION_FROXY",
    "2": "AD_STRING_SESSION_KEYVADI",
    "3": "AD_STRING_SESSION_LISANSARENA",
}


def persist_render_session(slot, session_string):
    """Write a session directly to Render without returning or logging it."""
    import urllib.request
    env_var = SLOT_ENV_VARS.get(str(slot), '')
    api_key = os.environ.get('RENDER_API_KEY', '').strip()
    service_id = os.environ.get('RENDER_SERVICE_ID', '').strip()
    if not env_var or not api_key or not service_id:
        raise RuntimeError('Render session persistence is not configured')
    url = f'https://api.render.com/v1/services/{service_id}/env-vars/{env_var}'
    payload = json.dumps({'value': session_string}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='PUT')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('Accept', 'application/json')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status not in (200, 201):
            raise RuntimeError('Render rejected the session update')
    return env_var


# State variables for background processes
ad_process = None
support_process = None
froxy_process = None
lisansarena_process = None

LOG_FILE = "bot_log.txt"
SUPPORT_LOG_FILE = "froxy_bot_log.txt"
FROXY_LOG_FILE = "froxy_destek_log.txt"
LISANSARENA_LOG_FILE = "lisansarena_bot_log.txt"
MESSAGE_FILE = "message.txt"
CONFIG_FILE = "bot_config.json"
AD_STOP_FILE = "ad_worker.disabled"
AD_SMOKE_ACTIVE_FILE = "ad_smoke.active.json"
AD_SMOKE_RESULT_FILE = "ad_smoke_result.json"
AD_SMOKE_CHECKPOINT_FILE = "blast_smoke_checkpoint.json"


def bot_runtime_enabled():
    """Run Telegram workers only from the configured owner platform.

    The local Antigravity checkout is intentionally a dashboard/control
    surface. Starting the same Telegram sessions locally and on Render
    causes AuthKeyDuplicatedError and duplicate replies. A deployment can
    opt in explicitly with BOT_RUNTIME_ENABLED=true; Render is the default
    owner for production.
    """
    if (
        os.environ.get("WASMER_EDGE", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.environ.get("WASMER_TELEGRAM_WORKER", "0").strip().lower()
        not in {"1", "true", "yes", "on"}
    ):
        # Edge apps are stateless by default; keep Telegram sessions on the
        # dedicated persistent worker until Wasmer persistent workloads are
        # explicitly enabled and smoke-tested.
        return False
    value = os.environ.get("BOT_RUNTIME_ENABLED", "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True

    # Production cloud environment (Render/Linux) defaults to True so workers auto-start
    if os.name != "nt" or os.environ.get("PORT"):
        return True

    owner = os.environ.get("BOT_RUNTIME_OWNER", "render").strip().lower()
    if owner != "render":
        return False
    return bool(
        os.environ.get("RENDER", "").strip().lower() == "true"
        or os.environ.get("RENDER_SERVICE_ID", "").strip()
        or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    )


def ad_runtime_enabled():
    if not bot_runtime_enabled():
        return False
    value = os.environ.get("BOT_AD_ENABLED", "1").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    # Render keeps the service filesystem between deploys.  The old repository
    # marker was a one-time maintenance pause and can otherwise survive every
    # future deploy, even after the explicit BOT_AD_ENABLED resume switch is
    # turned back on.  Preserve deliberate panel stops and active smoke holds.
    if os.path.exists(AD_STOP_FILE):
        try:
            with open(AD_STOP_FILE, "r", encoding="utf-8", errors="replace") as marker:
                reason = marker.read().strip()
            active_hold = (
                reason.startswith("controlled smoke in progress")
                or reason == "disabled by panel"
            )
            if not active_hold:
                os.remove(AD_STOP_FILE)
                print("[App] Eski bakım durdurma işareti temizlendi; reklam worker yeniden açılabilir.")
            else:
                return False
        except (FileNotFoundError, OSError):
            return False
    return True

def update_config_state(key, value):
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg[key] = value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error updating config state: {e}")

# Process tracking helpers using psutil
def command_runs_python_script(process_name, command_line, script_name):
    """Match an actual Python script argument, never a shell command string."""
    command_line = [str(arg or "") for arg in (command_line or [])]
    executable = os.path.basename(command_line[0]).casefold() if command_line else ""
    process_name = str(process_name or "").casefold()
    is_python = process_name.startswith("python") or executable.startswith("python")
    wanted = os.path.basename(str(script_name)).casefold()
    script_args = {
        os.path.basename(arg.strip().strip('"\'')).casefold()
        for arg in command_line[1:]
        if arg.strip()
    }
    return is_python and wanted in script_args


class _ProcHandle:
    """Minimal psutil-compatible process handle for the WASIX fallback."""

    def __init__(self, pid):
        self.pid = int(pid)

    def children(self, recursive=False):
        return []

    def terminate(self):
        os.kill(self.pid, signal.SIGTERM)

    def kill(self):
        os.kill(self.pid, signal.SIGKILL)

    def wait(self, timeout=None):
        deadline = time.time() + (timeout or 0)
        while True:
            try:
                os.kill(self.pid, 0)
            except OSError:
                return 0
            if timeout is not None and time.time() >= deadline:
                raise TimeoutError()
            time.sleep(0.1)


def get_processes_by_script(script_name):
    """Return every Python process running a script, including stale duplicates."""
    if psutil is None:
        # WASIX has no psutil wheel. Keep a small /proc fallback for ordinary
        # Linux deployments and leave it empty on platforms without /proc.
        found = []
        proc_root = "/proc"
        try:
            for entry in os.listdir(proc_root):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                try:
                    raw = open(os.path.join(proc_root, entry, "cmdline"), "rb").read()
                    cmd = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
                    name = open(os.path.join(proc_root, entry, "comm"), encoding="utf-8").read().strip()
                    if command_runs_python_script(name, cmd, script_name):
                        found.append(_ProcHandle(pid))
                except (FileNotFoundError, PermissionError, OSError):
                    continue
        except (FileNotFoundError, PermissionError, OSError):
            return []
        return found
    found = {}
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = proc.info.get('cmdline') or []
                if command_runs_python_script(
                    proc.info.get('name'), cmd, script_name
                ):
                    found[proc.info['pid']] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass
    return list(found.values())

def get_process_by_script(script_name):
    """Return one process and clean up any extra copies of the same bot."""
    processes = get_processes_by_script(script_name)
    if len(processes) > 1:
        print(f"[Watchdog] {script_name} için {len(processes)} kopya bulundu; fazlalıklar kapatılıyor.")
        for proc in processes[1:]:
            try:
                proc.terminate()
            except Exception:
                pass
    return processes[0] if processes else None

def kill_process_by_script(script_name):
    """Kills any running python process that executes script_name using PID file."""
    processes = get_processes_by_script(script_name)
    killed = False
    for proc in processes:
        try:
            print(f"Killing process {proc.pid} running {script_name}")
            for child in proc.children(recursive=True):
                try: child.terminate()
                except: pass
            proc.terminate()
            try: proc.wait(timeout=3)
            except Exception: proc.kill()
            killed = True
        except Exception:
            pass
    return killed


def launch_ad_worker(*, env_overrides=None, truncate_log=False):
    """Start exactly one ad worker and return its process."""
    global ad_process
    if get_process_by_script('otomatik_katil.py') is not None:
        raise RuntimeError('Reklam worker zaten çalışıyor')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.update({
        str(key): str(value)
        for key, value in (env_overrides or {}).items()
    })
    mode = 'w' if truncate_log else 'a'
    file_out = open(LOG_FILE, mode, encoding="utf-8", buffering=1)
    ad_process = subprocess.Popen(
        [sys.executable, '-u', 'otomatik_katil.py'],
        stdout=file_out,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        env=env,
    )
    with open("otomatik_katil.py.pid", "w", encoding="utf-8") as handle:
        handle.write(str(ad_process.pid))
    return ad_process


def read_controlled_smoke_result():
    try:
        with open(AD_SMOKE_RESULT_FILE, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def monitor_controlled_smoke(process, expected_account, expected_group):
    """Keep ads paused on failure; auto-release the normal queue on success."""
    global ad_process
    try:
        process.wait()
        result = read_controlled_smoke_result()
        valid = (
            process.returncode == 0
            and result.get("status") == "passed"
            and result.get("account") == expected_account
            and str(result.get("group") or "").lower().lstrip("@") == expected_group
        )
        try:
            os.remove(AD_SMOKE_ACTIVE_FILE)
        except FileNotFoundError:
            pass
        try:
            os.remove("otomatik_katil.py.pid")
        except FileNotFoundError:
            pass
        ad_process = None
        if not valid:
            with open(AD_STOP_FILE, "w", encoding="utf-8") as marker:
                marker.write("controlled smoke failed; manual review required\n")
            return
        if os.environ.get("BOT_AD_ENABLED", "1").strip().lower() in {
            "0", "false", "no", "off"
        } or not bot_runtime_enabled():
            result["auto_start"] = "blocked_by_runtime_configuration"
            with open(AD_SMOKE_RESULT_FILE, "w", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            return
        try:
            os.remove(AD_STOP_FILE)
        except FileNotFoundError:
            pass
        launch_ad_worker()
        update_config_state("ad_bot_running", True)
        result["auto_start"] = "started"
        result["normal_worker_pid"] = ad_process.pid
        with open(AD_SMOKE_RESULT_FILE, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    except Exception as exc:
        with open(AD_STOP_FILE, "w", encoding="utf-8") as marker:
            marker.write("controlled smoke monitor failed; manual review required\n")
        result = read_controlled_smoke_result()
        result.update({
            "status": "failed",
            "reason": f"monitor:{type(exc).__name__}",
        })
        with open(AD_SMOKE_RESULT_FILE, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)

# WATCHDOG SYSTEM: Keeps both bots running 24/7 unconditionally
def bot_watchdog():
    global ad_process, support_process, froxy_process, lisansarena_process
    if not bot_runtime_enabled():
        print("[Watchdog] BOT_RUNTIME_ENABLED=false; Telegram processes will not be started.")
        return
    print("🛡️ [Watchdog] Bot takip sistemi başlatıldı. Botlar her 15 saniyede bir denetlenecek.")
    time.sleep(30) # Give the web server 30 seconds to bind and report healthy first
    
    while True:
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            ad_enabled = False
            support_enabled = False
            has_token = False
            cfg = {}
            
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    ad_enabled = cfg.get("ad_bot_running", False)
                    # Production ownership is Render-only.  If the legacy
                    # local config still has the old false flag, Render may
                    # opt in through BOT_AD_ENABLED (true by default); local
                    # watchdogs remain disabled by bot_runtime_enabled().
                    if ad_runtime_enabled():
                        ad_enabled = True
                    elif bot_runtime_enabled():
                        ad_enabled = False
                    support_enabled = cfg.get("support_bot_running", False)
                    token = os.environ.get("KEYVADI_SUPPORT_BOT_TOKEN", "").strip()
                    if token and token != "YOUR_TELEGRAM_BOT_TOKEN":
                        has_token = True
                except Exception as ex:
                    print(f"Error checking config: {ex}")

            # 1. Check Ad Bot (otomatik_katil.py)
            ad_proc_os = get_process_by_script('otomatik_katil.py')
            smoke_active = os.path.exists(AD_SMOKE_ACTIVE_FILE)
            if smoke_active:
                # A controlled smoke deliberately runs while the normal ad
                # marker remains disabled. Never kill it and never replace a
                # failed/finished smoke with an unrestricted normal worker.
                ad_process = ad_proc_os
            elif ad_enabled:
                if ad_proc_os is None:
                    print("📢 [Watchdog] Reklam botu aktif değil veya durmuş. Başlatılıyor...")
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Reklam botu otomatik olarak başlatılıyor...\n")
                    
                    kill_process_by_script('otomatik_katil.py')
                    
                    file_out = open(LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    ad_process = subprocess.Popen(
                        [sys.executable, '-u', 'otomatik_katil.py'],
                        stdout=file_out,
                        stderr=subprocess.STDOUT,
                        creationflags=flags,
                        env=env
                    )
                    try:
                        with open("otomatik_katil.py.pid", "w") as f:
                            f.write(str(ad_process.pid))
                    except:
                        pass
                    time.sleep(10)  # Stagger startup to prevent RAM/CPU spikes
                else:
                    ad_process = ad_proc_os
            else:
                if ad_proc_os is not None:
                    print("📢 [Watchdog] Reklam botu durduruluyor (Yapılandırmada kapalı)...")
                    kill_process_by_script('otomatik_katil.py')
                    # Remove PID file
                    try: os.remove("otomatik_katil.py.pid")
                    except: pass
                    ad_process = None

            # 2. Check Support Bot (froxy_bot.py)
            if has_token and support_enabled:
                support_proc_os = get_process_by_script('froxy_bot.py')
                if support_proc_os is None:
                    print("🤖 [Watchdog] Destek botu aktif değil veya durmuş. Başlatılıyor...")
                    with open(SUPPORT_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Destek botu otomatik olarak başlatılıyor...\n")
                    
                    kill_process_by_script('froxy_bot.py')
                    
                    file_out = open(SUPPORT_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    support_process = subprocess.Popen(
                        [sys.executable, '-u', 'froxy_bot.py'],
                        stdout=file_out,
                        stderr=subprocess.STDOUT,
                        creationflags=flags,
                        env=env
                    )
                    try:
                        with open("froxy_bot.py.pid", "w") as f:
                            f.write(str(support_process.pid))
                    except:
                        pass
                    time.sleep(10)  # Stagger startup to prevent RAM/CPU spikes
                else:
                    support_process = support_proc_os
            else:
                support_proc_os = get_process_by_script('froxy_bot.py')
                if support_proc_os is not None:
                    print("🤖 [Watchdog] Destek botu durduruluyor (Yapılandırmada kapalı)...")
                    kill_process_by_script('froxy_bot.py')
                    # Remove PID file
                    try: os.remove("froxy_bot.py.pid")
                    except: pass
                    support_process = None

            # 3. Check Froxy AI Bot (froxy_destek_bot.py)
            froxy_enabled = False
            has_froxy_token = False
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    froxy_enabled = FROXY_ENABLED and cfg.get("froxy_bot_running", False)
                    froxy_token = os.environ.get("FROXY_SUPPORT_BOT_TOKEN", "").strip()
                    if froxy_token and froxy_token != "YOUR_TELEGRAM_BOT_TOKEN":
                        has_froxy_token = True
                except Exception:
                    pass

            if has_froxy_token and froxy_enabled:
                froxy_proc_os = get_process_by_script('froxy_destek_bot.py')
                if froxy_proc_os is None:
                    print("🤖 [Watchdog] Froxy AI botu aktif değil veya durmuş. Başlatılıyor...")
                    with open(FROXY_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Froxy AI botu otomatik olarak başlatılıyor...\n")
                    
                    kill_process_by_script('froxy_destek_bot.py')
                    
                    file_out = open(FROXY_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    froxy_process = subprocess.Popen(
                        [sys.executable, '-u', 'froxy_destek_bot.py'],
                        stdout=file_out,
                        stderr=subprocess.STDOUT,
                        creationflags=flags,
                        env=env
                    )
                    try:
                        with open("froxy_destek_bot.py.pid", "w") as f:
                            f.write(str(froxy_process.pid))
                    except:
                        pass
                    time.sleep(10)  # Stagger startup to prevent RAM/CPU spikes
                else:
                    froxy_process = froxy_proc_os
            else:
                froxy_proc_os = get_process_by_script('froxy_destek_bot.py')
                if froxy_proc_os is not None:
                    print("🤖 [Watchdog] Froxy AI botu durduruluyor (Yapılandırmada kapalı)...")
                    kill_process_by_script('froxy_destek_bot.py')
                    try: os.remove("froxy_destek_bot.py.pid")
                    except: pass
                    froxy_process = None

            # 4. Check LisansArena Bot (lisansarena_bot.py)
            lisansarena_enabled = False
            has_lisansarena_token = False
            if cfg:
                lisansarena_enabled = cfg.get("lisansarena_bot_running", False)
                lisansarena_token = os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
                if lisansarena_token and lisansarena_token != "YOUR_TELEGRAM_BOT_TOKEN":
                    has_lisansarena_token = True

            if has_lisansarena_token and lisansarena_enabled:
                la_proc_os = get_process_by_script('lisansarena_bot.py')
                if la_proc_os is None:
                    print("🤖 [Watchdog] LisansArena botu aktif değil veya durmuş. Başlatılıyor...")
                    with open(LISANSARENA_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] LisansArena botu otomatik olarak başlatılıyor...\n")
                    
                    kill_process_by_script('lisansarena_bot.py')
                    file_out = open(LISANSARENA_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    lisansarena_process = subprocess.Popen(
                        [sys.executable, '-u', 'lisansarena_bot.py'],
                        stdout=file_out,
                        stderr=file_out,
                        cwd=base_dir,
                        creationflags=flags,
                        env=env
                    )
                    try:
                        with open("lisansarena_bot.py.pid", "w") as f:
                            f.write(str(lisansarena_process.pid))
                    except:
                        pass
                    time.sleep(10)
                else:
                    lisansarena_process = la_proc_os
            else:
                la_proc_os = get_process_by_script('lisansarena_bot.py')
                if la_proc_os is not None:
                    print("🤖 [Watchdog] LisansArena botu durduruluyor (Yapılandırmada kapalı)...")
                    kill_process_by_script('lisansarena_bot.py')
                    try: os.remove("lisansarena_bot.py.pid")
                    except: pass
                    lisansarena_process = None

        except Exception as e:
            print(f"⚠️ [Watchdog] Genel denetleme hatası: {e}")
            
        time.sleep(15)

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# REKLAM BOTU (ADVERTISING BOT) API ENDPOINTS
# ==========================================


@app.route('/api/status', methods=['GET'])
def status():
    ad_processes = get_processes_by_script('otomatik_katil.py')
    ad_accounts = {}
    status_path = os.path.join(base_dir, 'ad_account_status.json')
    try:
        if os.path.exists(status_path):
            with open(status_path, 'r', encoding='utf-8') as handle:
                ad_accounts = json.load(handle)
    except Exception:
        ad_accounts = {}

    process_running = bool(ad_processes)
    expected_accounts = ('FroxyOnline', 'KeyVadiOnline', 'LisansArenaOnline')
    for account_name in expected_accounts:
        account = ad_accounts.setdefault(account_name, {})
        account['process_running'] = process_running
        if not process_running:
            account['telegram_connected'] = False
            account['telegram_authorized'] = False
            if account.get('phase') not in {'session_invalid', 'configuration_error'}:
                account['phase'] = 'stopped'
        else:
            account.setdefault('telegram_connected', False)
            account.setdefault('telegram_authorized', False)
    authorized_count = sum(
        1 for account in ad_accounts.values()
        if account.get('telegram_authorized') is True
    )
    overall_status = (
        'running' if process_running and authorized_count == len(expected_accounts)
        else 'degraded' if process_running
        else 'stopped'
    )
    # Detailed group names belong to the token-protected group-status API.
    public_ad_accounts = {
        name: {
            key: value for key, value in account.items()
            if key not in {'group_states', 'candidate_groups'}
        }
        for name, account in ad_accounts.items()
    }
    checkpoint = load_blast_snapshot(os.path.join(base_dir, 'blast_checkpoint_v3.json'))
    public_queue = {
        'active_account': checkpoint.get('active_account'),
        'updated_at': checkpoint.get('updated_at'),
        'accounts': {},
    }
    for name, queue_state in (checkpoint.get('accounts') or {}).items():
        targets = queue_state.get('targets') or []
        cursor = int(queue_state.get('cursor', 0) or 0)
        public_queue['accounts'][name] = {
            'status': queue_state.get('status'),
            'due_at': queue_state.get('due_at'),
            'current_index': cursor + 1 if targets and cursor < len(targets) else None,
            'total_groups': len(targets),
            'sent_count': sum(1 for item in targets if item.get('state') == 'accepted'),
            'failed_count': sum(1 for item in targets if item.get('state') == 'failed'),
            'skipped_count': sum(
                1 for item in targets
                if item.get('state') in {'skipped', 'skipped_uncertain'}
            ),
            'pending_count': sum(
                1 for item in targets
                if item.get('state') not in {'accepted', 'failed', 'skipped', 'skipped_uncertain'}
            ),
            'pause_reason': queue_state.get('pause_reason'),
        }
    return jsonify({
        'status': overall_status,
        'bot_runtime_enabled': bot_runtime_enabled(),
        'ad_runtime_enabled': ad_runtime_enabled(),
        'build': os.environ.get('RENDER_GIT_COMMIT', 'unknown')[:12],
        'ad_processes': len(ad_processes),
        'support_processes': len(get_processes_by_script('froxy_bot.py')),
        'froxy_support_processes': len(get_processes_by_script('froxy_destek_bot.py')),
        'lisansarena_processes': len(get_processes_by_script('lisansarena_bot.py')),
        'ad_accounts': public_ad_accounts,
        'blast_queue': public_queue,
    })


@app.route('/api/system-checkup', methods=['GET'])
def system_checkup():
    """Read-only health summary for bots, durable claims, store and blast queue."""
    try:
        import firestore_helper
        claim_service = firestore_helper.health_check()
    except Exception as exc:
        claim_service = {
            'configured': False,
            'reachable': False,
            'status': type(exc).__name__,
        }

    expected_processes = {
        'keyvadi_support': len(get_processes_by_script('froxy_bot.py')),
        'froxy_support': len(get_processes_by_script('froxy_destek_bot.py')),
        'lisansarena_support': len(get_processes_by_script('lisansarena_bot.py')),
        'blast_worker': len(get_processes_by_script('otomatik_katil.py')),
    }
    from lisansarena_store import store_health as inspect_lisansarena_store
    store_health = inspect_lisansarena_store()

    process_health = {
        name: count == 1 for name, count in expected_processes.items()
    }
    overall = (
        'healthy'
        if all(process_health.values())
        and claim_service.get('reachable') is True
        and store_health.get('reachable') is True
        else 'degraded'
    )
    return jsonify({
        'status': overall,
        'build': os.environ.get('RENDER_GIT_COMMIT', 'unknown')[:12],
        'processes': expected_processes,
        'processes_healthy': process_health,
        'durable_claims': claim_service,
        'lisansarena_store': store_health,
        'lisansarena_traffic_enabled': store_health.get('reachable') is True,
        'shopier_catalogs': catalog_refresh_status(),
        'keyvadi_mini_app': {
            'url': os.environ.get(
                'KEYVADI_MINI_APP_URL',
                'https://froxy-bot-live.onrender.com/keyvadi/',
            ),
            'mounted': True,
        },
        'group_state_files': {
            name: os.path.exists(os.path.join(base_dir, name))
            for name in (
                'blast_checkpoint_v3.json',
                'group_cooldown.json',
                'group_failures.json',
                'account_group_blocks.json',
            )
        },
    })


@app.route('/api/group-status', methods=['GET'])
def group_status():
    def load_json_file(path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as handle:
                    return json.load(handle)
        except Exception:
            pass
        return default

    global_blacklist = []
    try:
        with open('blacklist.txt', 'r', encoding='utf-8') as handle:
            global_blacklist = sorted({line.strip() for line in handle if line.strip()})
    except FileNotFoundError:
        pass
    def flatten(states):
        rows = []
        for group, accounts in states.items():
            if not isinstance(accounts, dict):
                continue
            for account, state in accounts.items():
                if not isinstance(state, dict):
                    continue
                rows.append({'group': group, 'account': account, **state})
        return rows

    permanent = flatten(load_json_file('account_group_blocks.json', {}))
    failures = flatten(load_json_file('group_failures.json', {}))
    review_reasons = {'ChannelPrivateReview', 'UsernameInvalidReview', 'AccessReview'}
    review = [row for row in failures if row.get('reason') in review_reasons]
    temporary = [row for row in failures if row.get('reason') not in review_reasons]
    account_status = load_json_file('ad_account_status.json', {})
    account_targets = {
        account: state.get('group_states', {})
        for account, state in account_status.items()
        if isinstance(state, dict) and isinstance(state.get('group_states'), dict)
    }
    candidate_groups = {
        account: state.get('candidate_groups', [])
        for account, state in account_status.items()
        if isinstance(state, dict) and isinstance(state.get('candidate_groups'), list)
    }
    return jsonify({
        'global_blacklist': global_blacklist,
        'permanent': permanent,
        'temporary': temporary,
        'review': review,
        'policies': load_policies(),
        'delivery_states': moderation_snapshot(),
        'account_targets': account_targets,
        'candidate_groups': candidate_groups,
        'blast_checkpoint': load_blast_snapshot(
            os.path.join(base_dir, 'blast_checkpoint_v3.json')
        ),
    })


@app.route('/api/account-restrictions', methods=['GET'])
def account_restrictions():
    path = os.path.join(base_dir, 'account_restrictions.json')
    try:
        if not os.path.exists(path):
            return jsonify({})
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    checkpoint = load_blast_snapshot(os.path.join(base_dir, 'blast_checkpoint_v3.json'))
    account_cycles = {}
    for account, state in (checkpoint.get('accounts') or {}).items():
        current = state.get('targets') or []
        account_cycles[account] = current or state.get('last_targets') or []
    total_groups = sum(len(items) for items in account_cycles.values())
    done_count = sum(
        1 for items in account_cycles.values() for item in items
        if item.get('state') in {'accepted', 'failed', 'skipped', 'skipped_uncertain'}
    )
    sent_count = sum(
        1 for items in account_cycles.values() for item in items
        if item.get('state') == 'accepted'
    )
    failed_count = sum(
        1 for items in account_cycles.values() for item in items
        if item.get('state') == 'failed'
    )
    skipped_count = sum(
        1 for items in account_cycles.values() for item in items
        if item.get('state') in {'skipped', 'skipped_uncertain'}
    )

    blacklist_count = 0
    if os.path.exists("blacklist.txt"):
        try:
            with open("blacklist.txt", "r", encoding="utf-8") as f:
                blacklist_count = len([line.strip() for line in f if line.strip()])
        except:
            pass
            
    auto_discovered = 0
    if os.path.exists("auto_groups.txt"):
        try:
            with open("auto_groups.txt", "r", encoding="utf-8") as f:
                auto_discovered = len([line.strip() for line in f if line.strip()])
        except:
            pass

    return jsonify({
        "total_groups": total_groups,
        "done_groups": done_count,
        "blacklist_groups": blacklist_count,
        "sent_messages": sent_count,
        "failed_messages": failed_count,
        "skipped_groups": skipped_count,
        "auto_discovered": auto_discovered
    })

@app.route('/api/sales/summary', methods=['GET'])
def sales_summary():
    """Return the privacy-preserving funnel journal for the dashboard."""
    try:
        days = min(max(int(request.args.get('days', 7)), 1), 30)
    except (TypeError, ValueError):
        days = 7
    summary = summarize_sales(days)
    summary['cta_experiment'] = cta_experiment_status()
    return jsonify(summary)


@app.route('/api/supplier-opportunities', methods=['GET'])
def supplier_opportunities_api():
    from supplier_opportunities import load_opportunities
    return jsonify(load_opportunities())


@app.route('/api/sales/group-candidates', methods=['GET'])
def sales_group_candidates_api():
    path = os.path.join(base_dir, 'group_candidates_sales_20260820.json')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return jsonify(json.load(handle))
    except (OSError, ValueError, json.JSONDecodeError):
        return jsonify({'error': 'Aday raporu okunamadı'}), 500


@app.route('/api/procurement', methods=['GET', 'POST'])
def procurement_api():
    from supplier_opportunities import create_procurement_request, list_procurement_requests
    if request.method == 'GET':
        return jsonify({'requests': list_procurement_requests()})
    data = request.get_json(silent=True) or {}
    try:
        row = create_procurement_request(
            str(data.get('opportunity_id') or ''),
            str(data.get('customer_reference') or ''),
            int(data.get('quantity') or 1),
        )
        return jsonify(row), 201
    except (TypeError, ValueError, RuntimeError) as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/api/procurement/<request_id>', methods=['POST'])
def procurement_update_api(request_id):
    from supplier_opportunities import update_procurement_request
    data = request.get_json(silent=True) or {}
    try:
        row = update_procurement_request(
            request_id,
            action=str(data.get('action') or ''),
            observed_unit_cost_cents=data.get('observed_unit_cost_cents'),
            stock_available=data.get('stock_available'),
            admin_id=request.headers.get('X-Admin-Id', 'panel'),
        )
        return jsonify(row)
    except (TypeError, ValueError, RuntimeError) as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/go/<token>', methods=['GET'])
def purchase_redirect(token):
    """Record an anonymous purchase click and redirect only to a known product."""
    payload = parse_purchase_token(token)
    if not payload:
        abort(404)
    product = product_by_id(payload['b'], payload['p'])
    if not product:
        abort(404)
    record_event(
        "purchase_click",
        payload['b'],
        product=product['title'],
        product_id=product['id'],
        source=payload.get('s', ''),
        arm=payload.get('a', ''),
        cta_key=payload.get('c', ''),
    )
    return redirect(purchase_target_url(payload['b'], product), code=302)

@app.route('/api/start', methods=['POST'])
def start():
    if os.environ.get("BOT_AD_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return jsonify({"success": False, "message": "Render maintenance lock keeps the ad worker disabled."}), 409
    try:
        os.remove(AD_STOP_FILE)
    except FileNotFoundError:
        pass
    if not bot_runtime_enabled():
        return jsonify({"success": False, "message": "Bu serviste Telegram bot çalışma zamanı kapalı."}), 409
    if get_process_by_script('otomatik_katil.py') is not None:
        return jsonify({"success": False, "message": "Reklam botu zaten çalışıyor!"})
    
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("🚀 Reklam botu başlatılıyor...\n")
        
    try:
        kill_process_by_script('otomatik_katil.py')
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(LOG_FILE, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        global ad_process
        ad_process = subprocess.Popen(
            [sys.executable, '-u', 'otomatik_katil.py'],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        try:
            with open("otomatik_katil.py.pid", "w") as f:
                f.write(str(ad_process.pid))
        except:
            pass
        update_config_state("ad_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})


@app.route('/api/ad-smoke/start', methods=['POST'])
def start_controlled_ad_smoke():
    """Run one KeyVadi message and keep every normal blast paused for 10m."""
    if not bot_runtime_enabled():
        return jsonify({"success": False, "message": "Telegram runtime kapalı"}), 409
    data = request.get_json(silent=True) or {}
    account = str(data.get("account") or "KeyVadiOnline").strip()
    group = str(data.get("group") or "").strip().lower().lstrip("@")
    if account != "KeyVadiOnline":
        return jsonify({"success": False, "message": "İlk smoke yalnız KeyVadi ile çalışır"}), 400
    if not re.fullmatch(r"(?:[a-z0-9_]{5,32}|-?\d{6,20})", group):
        return jsonify({"success": False, "message": "Geçerli bir onaylı grup gir"}), 400
    if get_process_by_script('otomatik_katil.py') is not None:
        return jsonify({"success": False, "message": "Reklam worker hâlâ çalışıyor"}), 409

    with open(AD_STOP_FILE, "w", encoding="utf-8") as marker:
        marker.write("controlled smoke in progress; normal blast disabled\n")
    for path in (AD_SMOKE_RESULT_FILE, AD_SMOKE_CHECKPOINT_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    active = {
        "account": account,
        "group": group,
        "started_at": time.time(),
        "verification_seconds": 600,
    }
    with open(AD_SMOKE_ACTIVE_FILE, "w", encoding="utf-8") as handle:
        json.dump(active, handle, ensure_ascii=False, indent=2)
    try:
        process = launch_ad_worker(
            env_overrides={
                "BOT_AD_ENABLED": "1",
                "BOT_AD_RUN_MODE": "controlled_smoke",
                "BOT_AD_SMOKE_ACCOUNT": account,
                "BOT_AD_SMOKE_GROUP": group,
                "BOT_AD_SMOKE_SECONDS": "600",
            },
            truncate_log=True,
        )
    except Exception as exc:
        try:
            os.remove(AD_SMOKE_ACTIVE_FILE)
        except FileNotFoundError:
            pass
        return jsonify({"success": False, "message": str(exc)}), 500
    threading.Thread(
        target=monitor_controlled_smoke,
        args=(process, account, group),
        daemon=True,
    ).start()
    return jsonify({
        "success": True,
        "status": "running",
        "account": account,
        "group": group,
        "verification_seconds": 600,
    }), 202


@app.route('/api/ad-smoke/status', methods=['GET'])
def controlled_ad_smoke_status():
    active = {}
    try:
        with open(AD_SMOKE_ACTIVE_FILE, "r", encoding="utf-8") as handle:
            active = json.load(handle)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return jsonify({
        "active": bool(active),
        "request": active,
        "result": read_controlled_smoke_result(),
        "normal_ads_paused": os.path.exists(AD_STOP_FILE),
        "worker_running": get_process_by_script('otomatik_katil.py') is not None,
    })

@app.route('/api/stop', methods=['POST'])
def stop():
    with open(AD_STOP_FILE, "w", encoding="utf-8") as marker:
        marker.write("disabled by panel\n")
    kill_process_by_script('otomatik_katil.py')
    try: os.remove("otomatik_katil.py.pid")
    except: pass
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n🛑 Reklam botu kullanıcı tarafından durduruldu.\n")
    global ad_process
    ad_process = None
    update_config_state("ad_bot_running", False)
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})
    
    try:
        with open(LOG_FILE, 'r', encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": lines[-100:]}) # Son 100 satır
    except Exception as e:
        return jsonify({"logs": [f"Log okuma hatası: {str(e)}"]})

@app.route('/api/full_logs', methods=['GET'])
def get_full_logs():
    if not os.path.exists(LOG_FILE):
        return "Log file not found", 404
    try:
        with open(LOG_FILE, 'r', encoding="utf-8", errors="replace") as f:
            return f.read(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return str(e), 500

@app.route('/api/dm-logs', methods=['GET'])
def get_dm_logs():
    """Tum destek botlarindaki DM olaylarini tek akista gosterir."""
    try:
        limit = min(max(int(request.args.get('lines', 200)), 20), 2000)
        markers = (
            'DM Alındı', 'Özel mesaj', 'GÖNDEREN=', 'New message', 'New Support',
            'Smart match', 'AI response', 'Ignoring non-sales', 'Yeni Destek',
            'otomatik yanıtlandı', '[AutoReply]', '[LisansArena]', '[KeyVadi]', '[Froxy]'
        )
        result = []
        for log_path in (LOG_FILE, SUPPORT_LOG_FILE, FROXY_LOG_FILE, LISANSARENA_LOG_FILE):
            if not os.path.exists(log_path):
                continue
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                result.extend(line for line in f if any(marker in line for marker in markers))
        return jsonify({"logs": result[-limit:]})
    except Exception as e:
        return jsonify({"logs": [f"DM log okuma hatasi: {str(e)}"]})

# ==========================================
# DESTEK/SATIŞ BOTU (SUPPORT BOT) API ENDPOINTS
# ==========================================

@app.route('/api/support/status', methods=['GET'])
def support_status():
    is_running = get_process_by_script('froxy_bot.py') is not None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/support/start', methods=['POST'])
def support_start():
    if not bot_runtime_enabled():
        return jsonify({"success": False, "message": "Bu serviste Telegram bot çalışma zamanı kapalı."}), 409
    if get_process_by_script('froxy_bot.py') is not None:
        return jsonify({"success": False, "message": "Destek botu zaten çalışıyor!"})
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = os.environ.get("KEYVADI_SUPPORT_BOT_TOKEN", "").strip()
        if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
            return jsonify({"success": False, "message": "Lütfen önce geçerli bir Telegram Bot Token kaydedin!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Yapılandırma hatası: {str(e)}"})

    with open(SUPPORT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("🚀 Destek ve Satış botu başlatılıyor...\n")
        
    try:
        kill_process_by_script('froxy_bot.py')
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(SUPPORT_LOG_FILE, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        global support_process
        support_process = subprocess.Popen(
            [sys.executable, '-u', 'froxy_bot.py'],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        try:
            with open("froxy_bot.py.pid", "w") as f:
                f.write(str(support_process.pid))
        except:
            pass
        update_config_state("support_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/support/stop', methods=['POST'])
def support_stop():
    kill_process_by_script('froxy_bot.py')
    try: os.remove("froxy_bot.py.pid")
    except: pass
    with open(SUPPORT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n🛑 Destek ve Satış botu kullanıcı tarafından durduruldu.\n")
    global support_process
    support_process = None
    update_config_state("support_bot_running", False)
    return jsonify({"success": True})

@app.route('/api/support/logs', methods=['GET'])
def get_support_logs():
    if not os.path.exists(SUPPORT_LOG_FILE):
        return jsonify({"logs": []})
    
    try:
        with open(SUPPORT_LOG_FILE, 'r', encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": lines[-100:]}) # Son 100 satır
    except Exception as e:
        return jsonify({"logs": [f"Log okuma hatası: {str(e)}"]})

# ==========================================
# FROXY AI BOT (@FroxyDestekBOT) API ENDPOINTS
# ==========================================

@app.route('/api/froxy/status', methods=['GET'])
def froxy_status():
    is_running = get_process_by_script('froxy_destek_bot.py') is not None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/froxy/start', methods=['POST'])
def froxy_start():
    if not bot_runtime_enabled():
        return jsonify({"success": False, "message": "Bu serviste Telegram bot çalışma zamanı kapalı."}), 409
    if get_process_by_script('froxy_destek_bot.py') is not None:
        return jsonify({"success": False, "message": "Froxy AI botu zaten çalışıyor!"})
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = os.environ.get("FROXY_SUPPORT_BOT_TOKEN", "").strip()
        if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
            return jsonify({"success": False, "message": "Lütfen önce geçerli bir Froxy Bot Token kaydedin!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Yapılandırma hatası: {str(e)}"})

    with open(FROXY_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("🚀 Froxy AI destek botu başlatılıyor...\n")
        
    try:
        kill_process_by_script('froxy_destek_bot.py')
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(FROXY_LOG_FILE, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        global froxy_process
        froxy_process = subprocess.Popen(
            [sys.executable, '-u', 'froxy_destek_bot.py'],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        try:
            with open("froxy_destek_bot.py.pid", "w") as f:
                f.write(str(froxy_process.pid))
        except:
            pass
        update_config_state("froxy_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/froxy/stop', methods=['POST'])
def froxy_stop():
    kill_process_by_script('froxy_destek_bot.py')
    try: os.remove("froxy_destek_bot.py.pid")
    except: pass
    with open(FROXY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n🛑 Froxy AI destek botu kullanıcı tarafından durduruldu.\n")
    global froxy_process
    froxy_process = None
    update_config_state("froxy_bot_running", False)
    return jsonify({"success": True})

@app.route('/api/froxy/logs', methods=['GET'])
def get_froxy_logs():
    if not os.path.exists(FROXY_LOG_FILE):
        return jsonify({"logs": []})
    
    try:
        with open(FROXY_LOG_FILE, 'r', encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": lines[-100:]})
    except Exception as e:
        return jsonify({"logs": [f"Log okuma hatası: {str(e)}"]})

@app.route('/api/froxy/config', methods=['GET'])
def get_froxy_config():
    if not os.path.exists(CONFIG_FILE):
        return jsonify({})
    try:
        with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
            cfg = json.load(f)
        return jsonify({"froxy_admin_id": cfg.get("froxy_admin_id", "")})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/froxy/config', methods=['POST'])
def save_froxy_config():
    data = request.json
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        
        if any(marker in key.lower() for key in data for marker in ('token', 'session', 'secret', 'key', 'hash')):
            return jsonify({"success": False, "message": "Secret değerleri panelden değiştirilemez."}), 400
        if data.get("froxy_admin_id"):
            cfg["froxy_admin_id"] = int(data["froxy_admin_id"])
        
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# LISANSARENA BOT API ENDPOINTS
# ==========================================

@app.route('/api/lisansarena/status', methods=['GET'])
def lisansarena_status():
    is_running = get_process_by_script('lisansarena_bot.py') is not None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/lisansarena/start', methods=['POST'])
def lisansarena_start():
    if not bot_runtime_enabled():
        return jsonify({"success": False, "message": "Bu serviste Telegram bot çalışma zamanı kapalı."}), 409
    if get_process_by_script('lisansarena_bot.py') is not None:
        return jsonify({"success": False, "message": "LisansArena botu zaten çalışıyor!"})
        
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
            
    token = os.environ.get("LISANSARENA_BOT_TOKEN", "").strip()
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
        return jsonify({"success": False, "message": "Lütfen önce geçerli bir LisansArena Bot Token kaydedin!"})
        
    try:
        with open(LISANSARENA_LOG_FILE, "w", encoding="utf-8") as f:
            f.write("🚀 LisansArena destek botu başlatılıyor...\n")
            
        kill_process_by_script('lisansarena_bot.py')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        file_out = open(LISANSARENA_LOG_FILE, 'a', encoding="utf-8", buffering=1)
        
        global lisansarena_process
        lisansarena_process = subprocess.Popen(
            [sys.executable, '-u', 'lisansarena_bot.py'],
            stdout=file_out,
            stderr=file_out,
            cwd=base_dir,
            creationflags=flags,
            env=env
        )
        try:
            with open("lisansarena_bot.py.pid", "w") as f:
                f.write(str(lisansarena_process.pid))
        except:
            pass
        update_config_state("lisansarena_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/lisansarena/stop', methods=['POST'])
def lisansarena_stop():
    kill_process_by_script('lisansarena_bot.py')
    try: os.remove("lisansarena_bot.py.pid")
    except: pass
    with open(LISANSARENA_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n🛑 LisansArena destek botu kullanıcı tarafından durduruldu.\n")
    global lisansarena_process
    lisansarena_process = None
    update_config_state("lisansarena_bot_running", False)
    return jsonify({"success": True})

@app.route('/api/lisansarena/logs', methods=['GET'])
def get_lisansarena_logs():
    if not os.path.exists(LISANSARENA_LOG_FILE):
        return jsonify({"logs": []})
    
    try:
        with open(LISANSARENA_LOG_FILE, 'r', encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": lines[-100:]})
    except Exception as e:
        return jsonify({"logs": [f"Log okuma hatası: {str(e)}"]})

@app.route('/api/lisansarena/config', methods=['GET'])
def get_lisansarena_config():
    if not os.path.exists(CONFIG_FILE):
        return jsonify({})
    try:
        with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
            cfg = json.load(f)
        return jsonify({"admin_id": cfg.get("admin_id", "")})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/lisansarena/config', methods=['POST'])
def save_lisansarena_config():
    data = request.json
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        
        if any(marker in key.lower() for key in data for marker in ('token', 'session', 'secret', 'key', 'hash')):
            return jsonify({"success": False, "message": "Secret değerleri panelden değiştirilemez."}), 400
        if data.get("admin_id"):
            cfg["admin_id"] = int(data["admin_id"])
        
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# YAPILANDIRMA VE DİĞER YARDIMCI API'LER
# ==========================================

@app.route('/api/message', methods=['GET'])
def get_message():
    try:
        with open(MESSAGE_FILE, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message', methods=['POST'])
def update_message():
    data = request.json
    new_message = data.get('message', '')
    try:
        with open(MESSAGE_FILE, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
MESSAGE_2_FILE = "message_2.txt"

@app.route('/api/message2', methods=['GET'])
def get_message2():
    try:
        with open(MESSAGE_2_FILE, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message2', methods=['POST'])
def update_message2():
    data = request.json
    new_message = data.get('message', '')
    try:
        with open(MESSAGE_2_FILE, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

MESSAGE_3_FILE = "message_3.txt"

@app.route('/api/message3', methods=['GET'])
def get_message3():
    try:
        with open(MESSAGE_3_FILE, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message3', methods=['POST'])
def update_message3():
    data = request.json
    new_message = data.get('message', '')
    try:
        with open(MESSAGE_3_FILE, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
@app.route('/api/config', methods=['GET'])
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return jsonify({})
    try:
        with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
            cfg = json.load(f)
        safe_keys = {'admin_id', 'ad_sleep_min', 'ad_sleep_max'}
        safe_cfg = {key: cfg.get(key) for key in safe_keys if key in cfg}
        return jsonify(safe_cfg)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/config', methods=['POST'])
def save_config():
    data = request.json or {}
    try:
        if any(marker in key.lower() for key in data for marker in ('token', 'session', 'secret', 'key', 'hash', 'proxy')):
            return jsonify({"success": False, "message": "Secret değerleri panelden değiştirilemez."}), 400
        allowed = {'admin_id', 'ad_sleep_min', 'ad_sleep_max'}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                old_cfg = json.load(f)
        else:
            old_cfg = {}
        for key in allowed:
            if key in data:
                old_cfg[key] = data[key]
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(old_cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

DEFAULT_SCRAPE_KEYWORDS = [
    # Genel ticaret (Dijital Odaklı)
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "ikinci el", "2.el satış", "alim satim",
    "e-ticaret satış", "trendyol satıcı", "freelance iş",
    "referans reklam", "satılık ilan", "epin satış",
    "sanal ticaret", "dijital tedarik", "shopier satış", "shopier ilan",
    # AI ve yazılım
    "yapay zeka", "chatgpt türkçe", "ai araçları", "ai tools",
    "adobe lisans", "canva pro", "premium hesap",
    "lisans satış", "yazılım indirim", "midjourney türkçe",
    "capcut pro", "chatgpt plus", "dijital araçlar",
    # Kupon ve indirim
    "trendyol indirim", "trendyol kupon", "yemek kuponu",
    "indirim kodu", "promosyon kodu", "kampanya kodu",
    "trendyol indirimleri", "yemeksepeti kupon", "getir indirim",
    # Freelance ve dijital
    "dijital pazarlama", "sosyal medya yönetimi",
    "instagram takipçi", "youtube abone", "tiktok takipçi",
    "grafik tasarım iş", "makale yazarı", "freelance türkiye",
    "home office iş", "tasarımcı iş ilanları", "yazılımcı yardımlaşma",
    # Oyun hesapları
    "pubg hesap", "brawl stars hesap", "valorant hesap",
    "oyun hesap satış", "game account", "steam cüzdan",
    "ucuz uc", "pubg uc", "vp satın al", "valorant puanı",
    "brawl stars elmas", "oyun pazarı", "epin bayilik",
    # Yeni eklenen genişletilmiş kelimeler (100+ Kelime Hedefi)
    "pazar yeri", "spotify premium", "netflix premium", "youtube premium",
    "disney premium", "exxen hesap", "blutv hesap", "ucuz lisans",
    "windows key", "office lisans", "steam key", "ucuz oyun",
    "gta 5 hesap", "lol hesap", "league of legends", "metin2 yang",
    "metin2 hesap", "smm bayi", "takipçi satın al", "instagram satılık",
    "tiktok satılık", "kanal satılık", "grup satılık", "reklam alım",
    "reklam satım", "backlink satış", "seo uzmanı", "webmaster forum",
    "r10 davetiye", "w10 lisans", "canva tasarım", "dijital marketing",
    "dropshipping tr", "amazon fba", "e-ticaret yardımlaşma", "ucuz vds",
    "hosting satış", "hesap alım satım", "reklam satışı", "satis grubu"
]

@app.route('/api/scraper/config', methods=['GET'])
def get_scraper_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
    active = cfg.get("scraper_active", True)
    keywords = cfg.get("scrape_keywords", DEFAULT_SCRAPE_KEYWORDS)
    return jsonify({"scraper_active": active, "scrape_keywords": keywords})

@app.route('/api/scraper/config', methods=['POST'])
def save_scraper_config():
    data = request.json
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
    
    if "scraper_active" in data:
        cfg["scraper_active"] = bool(data["scraper_active"])
    if "scrape_keywords" in data:
        keywords = [k.strip() for k in data["scrape_keywords"] if k.strip()]
        cfg["scrape_keywords"] = keywords
        
    try:
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/scraper/trigger', methods=['POST'])
def trigger_scraper():
    try:
        with open("trigger_scraper.flag", "w", encoding="utf-8") as f:
            f.write("trigger")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# AUTO-DM API
# ==========================================

@app.route('/api/autodm/config', methods=['GET'])
def get_autodm_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
    return jsonify({
        "auto_dm_active": cfg.get("auto_dm_active", True),
        "ai_response_enabled": cfg.get("ai_response_enabled", False),
        "max_dm_per_day": cfg.get("max_dm_per_day", 20),
    })

@app.route('/api/autodm/config', methods=['POST'])
def save_autodm_config():
    data = request.json
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
    
    if "auto_dm_active" in data:
        cfg["auto_dm_active"] = bool(data["auto_dm_active"])
    if "ai_response_enabled" in data:
        cfg["ai_response_enabled"] = bool(data["ai_response_enabled"])
    if "max_dm_per_day" in data:
        cfg["max_dm_per_day"] = int(data["max_dm_per_day"])
    
    try:
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# MESAJ ŞABLONLARI API
# ==========================================

MESSAGES_DIR = "messages"

@app.route('/api/templates', methods=['GET'])
def get_templates():
    templates = []
    if os.path.exists(MESSAGES_DIR):
        for fname in sorted(os.listdir(MESSAGES_DIR)):
            if fname.endswith('.txt'):
                fpath = os.path.join(MESSAGES_DIR, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    templates.append({
                        "name": fname,
                        "content": content,
                        "size": len(content),
                    })
                except:
                    pass
    return jsonify({"templates": templates})

@app.route('/api/templates/<name>', methods=['GET'])
def get_template(name):
    fpath = os.path.join(MESSAGES_DIR, name)
    if not os.path.exists(fpath):
        return jsonify({"error": "Template not found"}), 404
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            return jsonify({"name": name, "content": f.read()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/<name>', methods=['POST'])
def save_template(name):
    data = request.json
    content = data.get('content', '')
    fpath = os.path.join(MESSAGES_DIR, name)
    try:
        os.makedirs(MESSAGES_DIR, exist_ok=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

BLACKLIST_FILE = "blacklist.txt"

def get_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            pass
    return []

def save_blacklist(blacklist_list):
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(blacklist_list) + '\n')
        
        # Firestore'a senkronize et (sadece blacklist_list alanını güncelliyoruz)
        try:
            import requests
            API_KEY = os.environ.get("FIREBASE_API_KEY", "").strip()
            if not API_KEY:
                raise RuntimeError("FIREBASE_API_KEY is not configured")
            PROJECT_ID = "bot-2-63772"
            url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam/state?updateMask.fieldPaths=blacklist_list&key={API_KEY}"
            
            blacklist_content = '\n'.join(blacklist_list) + '\n'
            
            fields = {
                "blacklist_list": {"stringValue": blacklist_content}
            }
            requests.patch(url, json={"fields": fields}, timeout=5)
        except Exception as fs_err:
            print(f"Firestore sync error from web api: {fs_err}")
        return True
    except Exception as e:
        print(f"Error saving blacklist: {e}")
        return False

@app.route('/api/blacklist', methods=['GET'])
def api_get_blacklist():
    return jsonify(get_blacklist())

@app.route('/api/blacklist/add', methods=['POST'])
def api_add_blacklist():
    data = request.json
    username = data.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({"success": False, "message": "Grup adı boş olamaz."})
    
    blacklist = get_blacklist()
    blacklist_lower = [b.lower() for b in blacklist]
    if username.lower() not in blacklist_lower:
        blacklist.append(username)
        if save_blacklist(blacklist):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Kara liste dosyası kaydedilemedi."})
    return jsonify({"success": True, "message": "Grup zaten kara listede."})

@app.route('/api/blacklist/remove', methods=['POST'])
def api_remove_blacklist():
    data = request.json
    username = data.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({"success": False, "message": "Grup adı boş olamaz."})
    
    blacklist = get_blacklist()
    new_blacklist = [b for b in blacklist if b.lower() != username.lower()]
    if len(new_blacklist) != len(blacklist):
        if save_blacklist(new_blacklist):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Kara liste dosyası kaydedilemedi."})
    return jsonify({"success": False, "message": "Grup kara listede bulunamadı."})

@app.route('/api/groups')
def api_groups():
    """Tüm önbelleğe alınan grupları döndür"""
    result = {}
    for fname in ["cached_groups_Hesap_1.json", "cached_groups_Hesap_2.json"]:
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                groups = json.load(f)
                # Sadece broadcast olmayan grupları göster
                groups = [g for g in groups if not g.get('broadcast', False)]
                groups.sort(key=lambda x: x.get('members') or 0, reverse=True)
                result[fname.replace("cached_groups_", "").replace(".json", "")] = groups
        except:
            pass
    return jsonify(result)

# KEEP-ALIVE: Render free tier uyku modunu engelle (her 10dk kendine ping at)
def keep_alive():
    import urllib.request
    time.sleep(30)  # App'in ayağa kalkmasını bekle
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://froxy-bot-live.onrender.com")
    ping_url = render_url.rstrip('/') + "/api/status"
    print(f"[KeepAlive] Başlatıldı. Her 10dk {ping_url} adresine ping atılacak.")
    while True:
        try:
            urllib.request.urlopen(ping_url, timeout=10)
        except Exception:
            pass
        time.sleep(600)  # 10 dakika

@app.route('/api/scraped-groups')
def get_scraped_groups():
    groups = []
    if os.path.exists("scraped_groups.txt"):
        try:
            with open("scraped_groups.txt", "r", encoding="utf-8") as f:
                groups = [line.strip() for line in f if line.strip()]
        except Exception as e:
            return jsonify({"error": str(e)})
@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    tickets = []
    if os.path.exists("tickets.json"):
        try:
            with open("tickets.json", "r", encoding="utf-8") as f:
                tickets = json.load(f)
        except Exception as e:
            return jsonify({"error": str(e)})
    try:
        from lisansarena_store import get_store
        lisansarena_tickets = get_store().list_tickets(limit=200)
        for item in lisansarena_tickets:
            tickets.append({
                "source": "lisansarena",
                "bot_type": "LisansArena",
                **item,
            })
        tickets.sort(
            key=lambda item: str(item.get("created_at") or item.get("timestamp") or ""),
            reverse=True,
        )
    except Exception:
        # The shared support queue remains available if the store DB is down.
        pass
    return jsonify({"tickets": tickets})

@app.route('/api/tickets/clear', methods=['POST'])
def clear_tickets():
    try:
        if os.path.exists("tickets.json"):
            os.remove("tickets.json")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/shopier/callback', methods=['POST'])
def shopier_callback():
    try:
        data = request.form.to_dict()
        if not data:
            data = request.json or {}
        order_id = (
            data.get("orderNumber") or data.get("order_number") or data.get("id")
            or data.get("platform_order_id") or data.get("platformOrderId")
        )
        if not order_id:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        account = (
            data.get("shop_slug") or data.get("shop")
            or request.headers.get("Shopier-Account-Id") or "shopier"
        )
        ingest_shopier_order(data, account, "webhook")
        return "OK", 200
    except Exception as e:
        print(f"⚠️ Shopier webhook processing error: {e}")
        return str(e), 500
try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.errors import SessionPasswordNeededError
except ImportError:  # Web-only Wasmer build keeps Telegram workers on Render.
    TelegramClient = None
    StringSession = None
    SessionPasswordNeededError = Exception

telegram_logins = {}

# Helper to run async functions safely in Flask threads
def run_async_auth(coro, loop=None):
    import asyncio
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def disconnect_auth_client(client):
    """Telethon disconnect may be sync or awaitable depending on its loop state."""
    result = client.disconnect()
    if hasattr(result, "__await__"):
        await result

@app.route('/api/telegram/send-code', methods=['POST'])
def tg_send_code():
    if TelegramClient is None:
        return jsonify({"success": False, "message": "Telegram doğrulama bu web worker'da kapalı; aktif worker Render üzerinde çalışıyor."}), 503
    data = request.json or {}
    phone = data.get("phone", "").strip()
    api_id = os.environ.get('TELEGRAM_API_ID', '').strip()
    api_hash = os.environ.get('TELEGRAM_API_HASH', '').strip()
    slot = data.get("slot", "1") # "1", "2", "3"
    
    if not phone:
        return jsonify({"success": False, "message": "Lütfen telefon numarasını giriniz."})
    if not api_id or not api_hash:
        return jsonify({"success": False, "message": "Telegram API bilgileri sunucuda yapılandırılmamış."}), 503
        
    try:
        api_id_int = int(api_id)
    except:
        return jsonify({"success": False, "message": "API ID geçersiz."})
        
    auth_loop = asyncio.new_event_loop()

    async def _send():
        # Disconnect previous temporary client if exists
        if slot in telegram_logins:
            try:
                await telegram_logins[slot]["client"].disconnect()
            except: pass
            
        client = TelegramClient(StringSession(), api_id_int, api_hash)
        await client.connect()
        sent_code = await client.send_code_request(phone)
        telegram_logins[slot] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent_code.phone_code_hash,
            "api_id": api_id_int,
            "api_hash": api_hash,
            "slot": slot,
            # Telethon clients must be verified on the same event loop that
            # opened their temporary connection. Flask may handle the next
            # request on another thread, so keep this loop with the login.
            "loop": auth_loop,
        }
        return True

    try:
        run_async_auth(_send(), auth_loop)
        return jsonify({"success": True, "message": "Doğrulama kodu gönderildi!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Kod gönderme hatası: {str(e)}"})

@app.route('/api/telegram/verify-code', methods=['POST'])
def tg_verify_code():
    if TelegramClient is None:
        return jsonify({"success": False, "message": "Telegram doğrulama bu web worker'da kapalı; aktif worker Render üzerinde çalışıyor."}), 503
    data = request.json or {}
    code = data.get("code", "").strip()
    slot = data.get("slot", "1")
    
    if slot not in telegram_logins:
        return jsonify({"success": False, "message": "Aktif bir giriş işlemi bulunamadı. Lütfen tekrar deneyin."})
        
    state = telegram_logins[slot]
    client = state["client"]
    phone = state["phone"]
    phone_code_hash = state["phone_code_hash"]
    
    async def _verify():
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            return {"success": True}
        except SessionPasswordNeededError:
            return {"success": True, "requires_password": True}
            
    try:
        res = run_async_auth(_verify(), state.get("loop"))
        if res.get("requires_password"):
            return jsonify({"success": True, "requires_password": True, "message": "İki adımlı doğrulama şifresi gerekli."})
            
        session_str = client.session.save()
        run_async_auth(disconnect_auth_client(client), state.get("loop"))
        telegram_logins.pop(slot, None)
        if state.get("loop") and not state["loop"].is_closed():
            state["loop"].close()
        
        env_var = persist_render_session(slot, session_str)
        return jsonify({
            "success": True,
            "message": f"Hesap #{slot} doğrulandı ve Render secret güncellendi.",
            "render_env_var": env_var,
            "deploy_required": True,
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Doğrulama hatası: {str(e)}"})

@app.route('/api/telegram/verify-password', methods=['POST'])
def tg_verify_password():
    if TelegramClient is None:
        return jsonify({"success": False, "message": "Telegram doğrulama bu web worker'da kapalı; aktif worker Render üzerinde çalışıyor."}), 503
    data = request.json or {}
    password = data.get("password", "").strip()
    slot = data.get("slot", "1")
    
    if slot not in telegram_logins:
        return jsonify({"success": False, "message": "Aktif bir giriş işlemi bulunamadı."})
        
    state = telegram_logins[slot]
    client = state["client"]
    
    async def _verify_pw():
        await client.sign_in(password=password)
        
    try:
        run_async_auth(_verify_pw(), state.get("loop"))
        session_str = client.session.save()
        run_async_auth(disconnect_auth_client(client), state.get("loop"))
        telegram_logins.pop(slot, None)
        if state.get("loop") and not state["loop"].is_closed():
            state["loop"].close()
        
        env_var = persist_render_session(slot, session_str)
        return jsonify({
            "success": True,
            "message": f"Hesap #{slot} doğrulandı ve Render secret güncellendi.",
            "render_env_var": env_var,
            "deploy_required": True,
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Şifre doğrulama hatası: {str(e)}"})


_shutdown_started = False


def shutdown_child_processes():
    global _shutdown_started
    if _shutdown_started:
        return
    _shutdown_started = True
    for script_name in (
        'otomatik_katil.py', 'froxy_bot.py',
        'froxy_destek_bot.py', 'lisansarena_bot.py',
    ):
        kill_process_by_script(script_name)


def _handle_shutdown_signal(signum, _frame):
    print(f"[App] shutdown signal {signum}; stopping Telegram children.")
    shutdown_child_processes()
    raise SystemExit(0)


atexit.register(shutdown_child_processes)
if threading.current_thread() is threading.main_thread():
    try:
        import signal as _signal
        _signal.signal(_signal.SIGTERM, _handle_shutdown_signal)
        _signal.signal(_signal.SIGINT, _handle_shutdown_signal)
    except Exception:
        pass


# Start background threads at module load (works under Gunicorn and direct python app.py)
_started_lock = threading.Lock()
_bg_threads_started = False

def start_background_threads():
    global _bg_threads_started
    with _started_lock:
        if not _bg_threads_started:
            _bg_threads_started = True
            if bot_runtime_enabled():
                print("🚀 [App] Starting background bot watchdog & keep-alive threads...")
                t = threading.Thread(target=bot_watchdog, daemon=True)
                t.start()
            else:
                print("🌐 [App] Web/static-only mode; Telegram watchdog is disabled.")
            ka = threading.Thread(target=keep_alive, daemon=True)
            ka.start()
            def catalog_refresh_loop():
                while True:
                    refreshed = refresh_configured_catalogs()
                    reconciled = reconcile_configured_orders()
                    if any(refreshed.values()):
                        print(f"[Catalog] Shopier API refresh completed: {refreshed}")
                    if any(reconciled.values()):
                        print(f"[Orders] Shopier API reconciliation completed: {reconciled}")
                    time.sleep(30 * 60)
            threading.Thread(target=catalog_refresh_loop, daemon=True).start()

start_background_threads()
start_store_worker()

# KeyVadi & LisansArena Mini Apps mounted under the web service
mounts = {}

class _MountedRootMiddleware:
    """Normalize DispatcherMiddleware's empty mounted path to Flask's root."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if not environ.get('PATH_INFO'):
            environ = dict(environ)
            environ['PATH_INFO'] = '/'
        return self.wsgi_app(environ, start_response)
try:
    from miniapp.server import app as keyvadi_miniapp
    mounts['/keyvadi'] = _MountedRootMiddleware(keyvadi_miniapp)
    print('[App] KeyVadi Mini App mounted at /keyvadi')
except Exception as exc:
    print(f'[App] KeyVadi Mini App mount unavailable: {exc}')

# LisansArena is intentionally *not* mounted through DispatcherMiddleware.
# Its PostgreSQL-backed Blueprint owns /la/app/, /api/la/* and the wallet/order
# flow.  Mounting the legacy JSON application here shadowed those routes and
# exposed an obsolete 34-product catalogue with a hard-coded test customer.
print('[App] LisansArena PostgreSQL Mini App served at /la/app/')

if mounts:
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, mounts)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
