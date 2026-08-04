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
import psutil
import socket

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

PANEL_ADMIN_TOKEN = os.environ.get('PANEL_ADMIN_TOKEN', '').strip()
SHOPIER_CALLBACK_SECRET = os.environ.get('SHOPIER_CALLBACK_SECRET', '').strip()
FROXY_ENABLED = True

@app.before_request
def protect_panel_api():
    """Require an explicit Render/local environment token for panel writes."""
    if not request.path.startswith('/api/'):
        return None
    public_paths = {'/api/status', '/api/account-restrictions'}
    if request.path in public_paths and request.method == 'GET':
        return None
    # Shopier bu uca kendi sunucusundan POST atiyor, panel token'i gonderemez.
    # Onceki kosul 'A and B or C' seklindeydi ve Python'da 'and' daha siki
    # bagladigi icin '(A and B) or C' olarak cozuluyordu: uc HER metot icin
    # kosulsuz muaf kaliyordu.  Isteyen sahte siparis POST'layip bedava lisans
    # aldirabiliyordu.  SHOPIER_CALLBACK_SECRET tanimliysa artik zorunlu;
    # tanimli degilse calismaya devam eder ama her istekte uyari basar.
    if request.path == '/api/shopier/callback':
        if not SHOPIER_CALLBACK_SECRET:
            print('⚠️ [Guvenlik] /api/shopier/callback korumasiz calisiyor. '
                  'SHOPIER_CALLBACK_SECRET tanimlayin ve Shopier bildirim '
                  'adresine ?secret=... ekleyin.')
            return None
        verilen = (request.args.get('secret')
                   or request.headers.get('X-Shopier-Secret', ''))
        if verilen != SHOPIER_CALLBACK_SECRET:
            print('🚫 [Guvenlik] Shopier callback gecersiz secret ile reddedildi.')
            return jsonify({'error': 'Unauthorized'}), 401
        return None
    return None


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


def store_slot_session(cfg, slot, session_str):
    """Yeni oturumu ilgili slotun tum varyant anahtarlarina yazar."""
    keys = SLOT_SESSION_KEYS.get(str(slot))
    if not keys:
        keys = ["ad_string_session" if str(slot) == "1" else f"ad_string_session{slot}"]
    for key in keys:
        cfg[key] = session_str
    return keys


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


def bot_runtime_enabled():
    """Allow a Render service to host the dashboard/assets without running bots."""
    value = os.environ.get("BOT_RUNTIME_ENABLED", "true").strip().lower()
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
            
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    ad_enabled = cfg.get("ad_bot_running", False)
                    support_enabled = cfg.get("support_bot_running", False)
                    token = cfg.get("bot_token", "")
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
                    froxy_token = cfg.get("froxy_bot_token", "")
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
                lisansarena_token = cfg.get("lisansarena_bot_token", "")
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
            with open(status_path, 'r', encoding='utf-8') as f:
                ad_accounts = json.load(f)
    except Exception:
        # Health status must stay available even if a runtime status file is
        # temporarily incomplete while an ad worker is writing it.
        ad_accounts = {}
    return jsonify({
        "status": "running" if ad_processes else "stopped",
        "bot_runtime_enabled": bot_runtime_enabled(),
        "build": os.environ.get("RENDER_GIT_COMMIT", "unknown")[:12],
        "instance": socket.gethostname(),
        "ad_processes": len(ad_processes),
        "support_processes": len(get_processes_by_script('froxy_bot.py')),
        "froxy_support_processes": len(get_processes_by_script('froxy_destek_bot.py')),
        "lisansarena_processes": len(get_processes_by_script('lisansarena_bot.py')),
        "ad_accounts": ad_accounts,
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

@app.route('/api/start', methods=['POST'])
def start():
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
        token = cfg.get("bot_token", "")
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
        token = cfg.get("froxy_bot_token", "")
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
        return jsonify({
            "froxy_bot_token": "<configured>" if cfg.get("froxy_bot_token") else "",
            "froxy_admin_id": cfg.get("froxy_admin_id", "")
        })
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
        
        if data.get("froxy_bot_token") and data.get("froxy_bot_token") != "<configured>":
            cfg["froxy_bot_token"] = data["froxy_bot_token"]
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
            
    token = cfg.get("lisansarena_bot_token", "")
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
        return jsonify({
            "lisansarena_bot_token": "<configured>" if cfg.get("lisansarena_bot_token") else "",
            "admin_id": cfg.get("admin_id", "")
        })
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
        
        if data.get("lisansarena_bot_token") and data.get("lisansarena_bot_token") != "<configured>":
            cfg["lisansarena_bot_token"] = data["lisansarena_bot_token"]
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
        secret_markers = ('token', 'session', 'key', 'hash', 'secret', 'proxy')
        safe_cfg = {
            k: ("<configured>" if any(marker in k.lower() for marker in secret_markers) and v else v)
            for k, v in cfg.items()
        }
        return jsonify(safe_cfg)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/config', methods=['POST'])
def save_config():
    data = request.json
    try:
        # Keep internal running states and merge shopier links when saving config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                old_cfg = json.load(f)
            data["ad_bot_running"] = old_cfg.get("ad_bot_running", False)
            data["support_bot_running"] = old_cfg.get("support_bot_running", False)
            
            # Merge shopier_links to protect 24 keys
            old_links = old_cfg.get("shopier_links", {})
            new_links = data.get("shopier_links", {})
            for k, v in new_links.items():
                if v:  # Only update if a value is provided
                    old_links[k] = v
            data["shopier_links"] = old_links

            # Redacted/blank secret fields from the dashboard must not erase
            # the stored credentials when ordinary settings are saved.
            for key, old_value in old_cfg.items():
                if any(marker in key.lower() for marker in ('token', 'session', 'key', 'hash', 'secret', 'proxy')):
                    if not data.get(key) or data.get(key) == '<configured>':
                        data[key] = old_value
            
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
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
            API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
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
    import urllib.request, ssl
    time.sleep(30)  # App'in ayağa kalkmasını bekle
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://froxy-bot.onrender.com")
    ping_url = render_url.rstrip('/') + "/api/status"
    print(f"[KeepAlive] Başlatıldı. Her 10dk {ping_url} adresine ping atılacak.")
    ctx = ssl._create_unverified_context()
    while True:
        try:
            urllib.request.urlopen(ping_url, context=ctx, timeout=10)
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
            
        print(f"📥 Received Shopier Webhook: {data}")
        
        platform_order_id = data.get("platform_order_id")
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        product_name = data.get("product_name", "")
        total_amount = data.get("total_amount", "0")
        
        if not platform_order_id or not email:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
            
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
def run_async_auth(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/api/telegram/send-code', methods=['POST'])
def tg_send_code():
    data = request.json or {}
    phone = data.get("phone", "").strip()
    api_id = data.get("api_id", "").strip()
    api_hash = data.get("api_hash", "").strip()
    slot = data.get("slot", "1") # "1", "2", "3"
    
    if not phone or not api_id or not api_hash:
        return jsonify({"success": False, "message": "Lütfen Telefon, API ID ve API Hash giriniz."})
        
    try:
        api_id_int = int(api_id)
    except:
        return jsonify({"success": False, "message": "API ID geçersiz."})
        
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
            "slot": slot
        }
        return True

    try:
        run_async_auth(_send())
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
        res = run_async_auth(_verify())
        if res.get("requires_password"):
            return jsonify({"success": True, "requires_password": True, "message": "İki adımlı doğrulama şifresi gerekli."})
            
        session_str = client.session.save()
        run_async_auth(client.disconnect())
        telegram_logins.pop(slot, None)
        
        # Save to single-tenant config (bot_config.json)
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        store_slot_session(cfg, slot, session_str)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        env_var = SLOT_ENV_VARS.get(slot, "")
        note = (f"\n\nÖNEMLİ: Render'da kalıcı olması için yeni anahtarı {env_var} "
                "ortam değişkenine yapıştırın.") if env_var else ""
        return jsonify({
            "success": True,
            "message": f"Hesap #{slot} başarıyla bağlandı!" + note,
            "session_string": session_str,
            "render_env_var": env_var,
            "warning": (
                f"Render'da kalıcı olması için bu anahtarı {env_var} ortam "
                "değişkenine yapıştırın; aksi halde ilk deploy'da kaybolur."
            ) if env_var else "",
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
        run_async_auth(_verify_pw())
        session_str = client.session.save()
        run_async_auth(client.disconnect())
        telegram_logins.pop(slot, None)
        
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        store_slot_session(cfg, slot, session_str)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        env_var = SLOT_ENV_VARS.get(slot, "")
        note = (f"\n\nÖNEMLİ: Render'da kalıcı olması için yeni anahtarı {env_var} "
                "ortam değişkenine yapıştırın.") if env_var else ""
        return jsonify({
            "success": True,
            "message": f"Hesap #{slot} iki adımlı doğrulama ile başarıyla bağlandı!" + note,
            "session_string": session_str,
            "render_env_var": env_var,
            "warning": (
                f"Render'da kalıcı olması için bu anahtarı {env_var} ortam "
                "değişkenine yapıştırın; aksi halde ilk deploy'da kaybolur."
            ) if env_var else "",
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Şifre doğrulama hatası: {str(e)}"})


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
