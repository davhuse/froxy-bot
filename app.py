from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
import json
import threading
import time
import asyncio
import psutil
import socket
import hmac
import atexit
from sales_metrics import record_event, summarize as summarize_sales

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

PANEL_ADMIN_TOKEN = os.environ.get('PANEL_ADMIN_TOKEN', '').strip()
SHOPIER_CALLBACK_SECRET = os.environ.get('SHOPIER_CALLBACK_SECRET', '').strip()
FROXY_ENABLED = True

app.config.update(
    MAX_CONTENT_LENGTH=1024 * 1024,
    MAX_FORM_MEMORY_SIZE=256 * 1024,
    MAX_FORM_PARTS=100,
)

@app.before_request
def protect_panel_api():
    """Fail closed for every privileged panel API."""
    if not request.path.startswith('/api/'):
        return None
    if request.path == '/api/status' and request.method == 'GET':
        return None
    if request.path == '/api/shopier/callback':
        if not SHOPIER_CALLBACK_SECRET:
            print('[Security] Shopier callback is disabled: secret is missing.')
            return jsonify({'error': 'Callback is not configured'}), 503
        supplied = (request.args.get('secret')
                    or request.headers.get('X-Shopier-Secret', ''))
        if not hmac.compare_digest(str(supplied), SHOPIER_CALLBACK_SECRET):
            print('[Security] Shopier callback rejected an invalid secret.')
            return jsonify({'error': 'Unauthorized'}), 401
        return None

    if not PANEL_ADMIN_TOKEN:
        return jsonify({'error': 'Panel authentication is not configured'}), 503
    supplied = request.headers.get('X-Admin-Token', '')
    authorization = request.headers.get('Authorization', '')
    if not supplied and authorization.lower().startswith('bearer '):
        supplied = authorization[7:].strip()
    if not supplied or not hmac.compare_digest(str(supplied), PANEL_ADMIN_TOKEN):
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault('Cache-Control', 'no-store')
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


def bot_runtime_enabled():
    """Run Telegram workers only from the configured owner platform.

    The local Antigravity checkout is intentionally a dashboard/control
    surface.  Starting the same Telegram sessions locally and on Render
    causes AuthKeyDuplicatedError and duplicate replies.  A deployment can
    opt in explicitly with BOT_RUNTIME_ENABLED=true; Render is the default
    owner for production.
    """
    value = os.environ.get("BOT_RUNTIME_ENABLED", "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True

    owner = os.environ.get("BOT_RUNTIME_OWNER", "render").strip().lower()
    if owner != "render":
        return False
    # Render normally exposes RENDER=true, but older services only expose one
    # of the service URL/ID variables.  Accept those Render-only signals while
    # keeping a local checkout disabled by default.
    return bool(
        os.environ.get("RENDER", "").strip().lower() == "true"
        or os.environ.get("RENDER_SERVICE_ID", "").strip()
        or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    )


def ad_runtime_enabled():
    if not bot_runtime_enabled() or os.path.exists(AD_STOP_FILE):
        return False
    value = os.environ.get("BOT_AD_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}

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
def get_processes_by_script(script_name):
    """Return every Python process running a script, including stale duplicates."""
    found = {}
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = proc.info.get('cmdline') or []
                if any(script_name in arg for arg in cmd) and (
                    any('python' in arg.lower() for arg in cmd)
                    or proc.info.get('name') in ['python', 'python.exe']
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
            except psutil.TimeoutExpired: proc.kill()
            killed = True
        except Exception:
            pass
    return killed

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
            if ad_enabled:
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
    return jsonify({
        'status': overall_status,
        'bot_runtime_enabled': bot_runtime_enabled(),
        'ad_runtime_enabled': ad_runtime_enabled(),
        'build': os.environ.get('RENDER_GIT_COMMIT', 'unknown')[:12],
        'ad_processes': len(ad_processes),
        'support_processes': len(get_processes_by_script('froxy_bot.py')),
        'froxy_support_processes': len(get_processes_by_script('froxy_destek_bot.py')),
        'lisansarena_processes': len(get_processes_by_script('lisansarena_bot.py')),
        'ad_accounts': ad_accounts,
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
    return jsonify({
        'global_blacklist': global_blacklist,
        'permanent': permanent,
        'temporary': temporary,
        'review': review,
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
    done_count = 0
    if os.path.exists("progress.txt"):
        try:
            with open("progress.txt", "r", encoding="utf-8") as f:
                done_count = len([line.strip() for line in f if line.strip()])
        except:
            pass
            
    blacklist_count = 0
    if os.path.exists("blacklist.txt"):
        try:
            with open("blacklist.txt", "r", encoding="utf-8") as f:
                blacklist_count = len([line.strip() for line in f if line.strip()])
        except:
            pass
            
    sent_count = 0
    if os.path.exists("bot_log.txt"):
        try:
            with open("bot_log.txt", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "gönderildi!" in line.lower() or "gonderildi!" in line.lower():
                        sent_count += 1
        except:
            pass
            
    total_groups = 0
    try:
        with open("otomatik_katil.py", "r", encoding="utf-8") as f:
            content = f.read()
            # gruplar listesindeki elemanları say (her satırdaki tırnak içi string)
            import re
            match = re.search(r'gruplar\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if match:
                items = [x.strip().strip('"').strip("'") for x in match.group(1).split(',') if x.strip().strip('"').strip("'")]
                total_groups = len(items)
        # auto_groups.txt'deki grupları da ekle
        if os.path.exists("auto_groups.txt"):
            with open("auto_groups.txt", "r", encoding="utf-8") as f:
                auto_g = [x.strip() for x in f if x.strip()]
                total_groups += len(auto_g)
    except Exception as e:
        print(f"Error reading total groups: {e}")
        total_groups = 410 # Fallback default

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
        "auto_discovered": auto_discovered
    })

@app.route('/api/sales/summary', methods=['GET'])
def sales_summary():
    """Return the privacy-preserving funnel journal for the dashboard."""
    try:
        days = min(max(int(request.args.get('days', 7)), 1), 30)
    except (TypeError, ValueError):
        days = 7
    return jsonify(summarize_sales(days))

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
            'New message from user', 'New Support', 'DM Alındı',
            'Smart match for user', 'AI response for user',
            'Ignoring non-sales message', 'Yeni Destek Talebi',
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
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://froxy-bot.onrender.com")
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
    from datetime import datetime
    import firestore_helper
    try:
        data = request.form.to_dict()
        if not data:
            data = request.json or {}
        platform_order_id = data.get("platform_order_id")
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        product_name = data.get("product_name", "")
        total_amount = data.get("total_amount", "0")
        
        if not platform_order_id or not email:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        print(f"[Shopier] Received order callback: {platform_order_id}")
            
        phone_clean = phone.replace("+", "").replace(" ", "").strip()
        
        email_doc_id = "order_email_" + email.replace("@", "_").replace(".", "_")
        email_doc = firestore_helper.get_document(email_doc_id) or {"orders": []}
        
        if not any(o.get("order_id") == platform_order_id for o in email_doc.get("orders", [])):
            email_doc["orders"].append({
                "order_id": platform_order_id,
                "product_name": product_name,
                "amount": total_amount,
                "claimed": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            firestore_helper.set_document(email_doc_id, email_doc)
            try:
                amount = float(str(total_amount).replace(',', '.'))
            except (TypeError, ValueError):
                amount = 0.0
            record_event(
                "shopier_order",
                data.get("shop_slug") or data.get("shop") or "Shopier",
                amount=amount,
                product=product_name,
                status="paid",
            )
            
        if phone_clean:
            phone_doc_id = "order_phone_" + phone_clean
            phone_doc = firestore_helper.get_document(phone_doc_id) or {"orders": []}
            if not any(o.get("order_id") == platform_order_id for o in phone_doc.get("orders", [])):
                phone_doc["orders"].append({
                    "order_id": platform_order_id,
                    "product_name": product_name,
                    "amount": total_amount,
                    "claimed": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                firestore_helper.set_document(phone_doc_id, phone_doc)
                
        return "OK", 200
    except Exception as e:
        print(f"⚠️ Shopier webhook processing error: {e}")
        return str(e), 500
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

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

start_background_threads()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
