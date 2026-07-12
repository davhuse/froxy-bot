from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
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
import user_db

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "habil_secret_key_123!@#")
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30

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
def get_process_by_script(script_name, user_id=None):
    """Finds a running python process that executes script_name using PID file."""
    if user_id and script_name == 'otomatik_katil.py':
        pid_file = f"logs/otomatik_katil_{user_id}.pid"
    else:
        pid_file = f"{script_name}.pid"
        
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                cmd = proc.cmdline() or []
                if any(script_name in arg for arg in cmd):
                    if user_id:
                        if len(cmd) > 2 and user_id in cmd:
                            return proc
                    else:
                        return proc
        except Exception:
            pass
    return None

def kill_process_by_script(script_name, user_id=None):
    """Kills any running python process that executes script_name using PID file."""
    proc = get_process_by_script(script_name, user_id)
    if proc:
        try:
            print(f"Killing process {proc.pid} running {script_name} (user: {user_id})")
            for child in proc.children(recursive=True):
                try: child.terminate()
                except: pass
            proc.terminate()
            try: proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return True
        except Exception:
            pass
    return False

# WATCHDOG SYSTEM: Keeps both bots running 24/7 unconditionally
def bot_watchdog():
    print("🛡️ [Watchdog] Bot takip sistemi başlatıldı. Botlar her 15 saniyede bir denetlenecek.")
    time.sleep(15) # Give the web server 15 seconds to bind and report healthy first
    
    while True:
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            import user_db
            
            # 1. Load admin user config (for support bots)
            habil_cfg = user_db.get_user_config("habil") or {}
            
            support_enabled = habil_cfg.get("support_bot_running", False)
            token = habil_cfg.get("bot_token", "")
            has_token = token and token != "YOUR_TELEGRAM_BOT_TOKEN"
            
            froxy_enabled = habil_cfg.get("froxy_bot_running", False)
            froxy_token = habil_cfg.get("froxy_bot_token", "")
            has_froxy_token = froxy_token and froxy_token != "YOUR_TELEGRAM_BOT_TOKEN"
            
            lisansarena_enabled = habil_cfg.get("lisansarena_bot_running", False)
            lisansarena_token = habil_cfg.get("lisansarena_bot_token", "")
            has_lisansarena_token = lisansarena_token and lisansarena_token != "YOUR_TELEGRAM_BOT_TOKEN"

            # Check Support Bot (froxy_bot.py)
            if has_token and support_enabled:
                support_proc_os = get_process_by_script('froxy_bot.py')
                if support_proc_os is None:
                    print("🤖 [Watchdog] Destek botu aktif değil. Başlatılıyor...")
                    with open(SUPPORT_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Destek botu otomatik olarak başlatılıyor...\n")
                    kill_process_by_script('froxy_bot.py')
                    file_out = open(SUPPORT_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    proc = subprocess.Popen([sys.executable, '-u', 'froxy_bot.py'], stdout=file_out, stderr=subprocess.STDOUT, creationflags=flags, env=env)
                    try:
                        with open("froxy_bot.py.pid", "w") as f: f.write(str(proc.pid))
                    except: pass
            else:
                support_proc_os = get_process_by_script('froxy_bot.py')
                if support_proc_os is not None:
                    print("🤖 [Watchdog] Destek botu durduruluyor...")
                    kill_process_by_script('froxy_bot.py')
                    try: os.remove("froxy_bot.py.pid")
                    except: pass

            # Check Froxy AI Bot (froxy_destek_bot.py)
            if has_froxy_token and froxy_enabled:
                froxy_proc_os = get_process_by_script('froxy_destek_bot.py')
                if froxy_proc_os is None:
                    print("🤖 [Watchdog] Froxy AI botu aktif değil. Başlatılıyor...")
                    with open(FROXY_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Froxy AI botu otomatik olarak başlatılıyor...\n")
                    kill_process_by_script('froxy_destek_bot.py')
                    file_out = open(FROXY_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    proc = subprocess.Popen([sys.executable, '-u', 'froxy_destek_bot.py'], stdout=file_out, stderr=subprocess.STDOUT, creationflags=flags, env=env)
                    try:
                        with open("froxy_destek_bot.py.pid", "w") as f: f.write(str(proc.pid))
                    except: pass
            else:
                froxy_proc_os = get_process_by_script('froxy_destek_bot.py')
                if froxy_proc_os is not None:
                    print("🤖 [Watchdog] Froxy AI botu durduruluyor...")
                    kill_process_by_script('froxy_destek_bot.py')
                    try: os.remove("froxy_destek_bot.py.pid")
                    except: pass

            # Check LisansArena Bot (lisansarena_bot.py)
            if has_lisansarena_token and lisansarena_enabled:
                la_proc_os = get_process_by_script('lisansarena_bot.py')
                if la_proc_os is None:
                    print("🤖 [Watchdog] LisansArena botu aktif değil. Başlatılıyor...")
                    with open(LISANSARENA_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] LisansArena botu otomatik olarak başlatılıyor...\n")
                    kill_process_by_script('lisansarena_bot.py')
                    file_out = open(LISANSARENA_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    proc = subprocess.Popen([sys.executable, '-u', 'lisansarena_bot.py'], stdout=file_out, stderr=subprocess.STDOUT, creationflags=flags, env=env)
                    try:
                        with open("lisansarena_bot.py.pid", "w") as f: f.write(str(proc.pid))
                    except: pass
            else:
                la_proc_os = get_process_by_script('lisansarena_bot.py')
                if la_proc_os is not None:
                    print("🤖 [Watchdog] LisansArena botu durduruluyor...")
                    kill_process_by_script('lisansarena_bot.py')
                    try: os.remove("lisansarena_bot.py.pid")
                    except: pass

            # 2. Check SaaS Users Ad Bots
            all_configs = user_db.get_all_user_configs()
            for user_id, user_cfg in all_configs.items():
                ad_enabled = user_cfg.get("ad_bot_running", False)
                ad_proc = get_process_by_script('otomatik_katil.py', user_id)
                user_log = f"logs/user_{user_id}_bot_log.txt"
                
                if ad_enabled:
                    if ad_proc is None:
                        print(f"📢 [Watchdog] SaaS kullanıcısı {user_id} reklam botu durmuş. Başlatılıyor...")
                        with open(user_log, "a", encoding="utf-8") as f:
                            f.write(f"\n🚀 [Watchdog] Reklam botu {user_id} için otomatik olarak başlatılıyor...\n")
                        
                        kill_process_by_script('otomatik_katil.py', user_id)
                        
                        file_out = open(user_log, 'a', encoding="utf-8", buffering=1)
                        proc = subprocess.Popen(
                            [sys.executable, '-u', 'otomatik_katil.py', user_id],
                            stdout=file_out,
                            stderr=subprocess.STDOUT,
                            creationflags=flags,
                            env=env
                        )
                        try:
                            pid_file = f"logs/otomatik_katil_{user_id}.pid"
                            with open(pid_file, "w") as f:
                                f.write(str(proc.pid))
                        except:
                            pass
                else:
                    if ad_proc is not None:
                        print(f"📢 [Watchdog] SaaS kullanıcısı {user_id} reklam botu durduruluyor...")
                        kill_process_by_script('otomatik_katil.py', user_id)
                        try: os.remove(f"logs/otomatik_katil_{user_id}.pid")
                        except: pass

        except Exception as e:
            print(f"⚠️ [Watchdog] Genel denetleme hatası: {e}")
            
        time.sleep(15)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Giriş yapmanız gerekmektedir."}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login_page'))

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get("username", "")
    password = data.get("password", "")
    res = user_db.login_user(username, password)
    if res.get("success"):
        session['user_id'] = res["user_id"]
        session.permanent = True
        return jsonify({"success": True, "message": "Giriş başarılı!"})
    return jsonify({"success": False, "message": res.get("message")})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get("username", "")
    password = data.get("password", "")
    license_key = data.get("license_key", "")
    res = user_db.register_user(username, password, license_key)
    if res.get("success"):
        session['user_id'] = username.strip().lower()
        session.permanent = True
        return jsonify({"success": True, "message": "Kayıt başarılı!"})
    return jsonify({"success": False, "message": res.get("message")})

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ==========================================
# R@app.route('/api/status', methods=['GET'])
@login_required
def status():
    user_id = session['user_id']
    is_running = get_process_by_script('otomatik_katil.py', user_id) is not None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/stats', methods=['GET'])
@login_required
def stats():
    user_id = session['user_id']
    
    progress_file = f"logs/user_{user_id}_progress.txt"
    blacklist_file = f"logs/user_{user_id}_blacklist.txt"
    auto_groups_file = f"logs/user_{user_id}_auto_groups.txt"
    user_log = f"logs/user_{user_id}_bot_log.txt"
    
    done_count = 0
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                done_count = len([line.strip() for line in f if line.strip()])
        except:
            pass
            
    blacklist_count = 0
    if os.path.exists(blacklist_file):
        try:
            with open(blacklist_file, "r", encoding="utf-8") as f:
                blacklist_count = len([line.strip() for line in f if line.strip()])
        except:
            pass
            
    sent_count = 0
    if os.path.exists(user_log):
        try:
            with open(user_log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "gönderildi!" in line.lower() or "gonderildi!" in line.lower():
                        sent_count += 1
        except:
            pass
            
    total_groups = 0
    try:
        with open("otomatik_katil.py", "r", encoding="utf-8") as f:
            content = f.read()
            import re
            match = re.search(r'gruplar\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if match:
                items = [x.strip().strip('"').strip("'") for x in match.group(1).split(',') if x.strip().strip('"').strip("'")]
                total_groups = len(items)
        if os.path.exists(auto_groups_file):
            with open(auto_groups_file, "r", encoding="utf-8") as f:
                auto_g = [x.strip() for x in f if x.strip()]
                total_groups += len(auto_g)
    except Exception as e:
        print(f"Error reading total groups: {e}")
        total_groups = 410
        
    auto_discovered = 0
    if os.path.exists(auto_groups_file):
        try:
            with open(auto_groups_file, "r", encoding="utf-8") as f:
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
@login_required
def start():
    user_id = session['user_id']
    if get_process_by_script('otomatik_katil.py', user_id) is not None:
        return jsonify({"success": False, "message": "Reklam botu zaten çalışıyor!"})
    
    user_log = f"logs/user_{user_id}_bot_log.txt"
    os.makedirs("logs", exist_ok=True)
    with open(user_log, "w", encoding="utf-8") as f:
        f.write("🚀 Reklam botu başlatılıyor...\n")
        
    try:
        kill_process_by_script('otomatik_katil.py', user_id)
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(user_log, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            [sys.executable, '-u', 'otomatik_katil.py', user_id],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        try:
            pid_file = f"logs/otomatik_katil_{user_id}.pid"
            with open(pid_file, "w") as f:
                f.write(str(proc.pid))
        except:
            pass
            
        cfg = user_db.get_user_config(user_id) or {}
        cfg["ad_bot_running"] = True
        user_db.save_user_config(user_id, cfg)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/stop', methods=['POST'])
@login_required
def stop():
    user_id = session['user_id']
    kill_process_by_script('otomatik_katil.py', user_id)
    try: os.remove(f"logs/otomatik_katil_{user_id}.pid")
    except: pass
    
    user_log = f"logs/user_{user_id}_bot_log.txt"
    try:
        with open(user_log, "a", encoding="utf-8") as f:
            f.write("\n🛑 Reklam botu kullanıcı tarafından durduruldu.\n")
    except:
        pass
        
    cfg = user_db.get_user_config(user_id) or {}
    cfg["ad_bot_running"] = False
    user_db.save_user_config(user_id, cfg)
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    user_id = session['user_id']
    user_log = f"logs/user_{user_id}_bot_log.txt"
    if not os.path.exists(user_log):
        return jsonify({"logs": []})
    
    try:
        with open(user_log, 'r', encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": lines[-100:]})
    except Exception as e:
        return jsonify({"logs": [f"Log okuma hatası: {str(e)}"]})

# ==========================================
# DESTEK/SATIŞ BOTU (SUPPORT BOT) API ENDPOINTS
# ==========================================

@app.route('/api/support/status', methods=['GET'])
def support_status():
    is_running = get_process_by_script('froxy_bot.py') is not None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/support/start', methods=['POST'])
def support_start():
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
            "froxy_bot_token": cfg.get("froxy_bot_token", ""),
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
        
        if data.get("froxy_bot_token"):
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
            "lisansarena_bot_token": cfg.get("lisansarena_bot_token", ""),
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
        
        if data.get("lisansarena_bot_token"):
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

def get_user_msg_file(user_id, num):
    os.makedirs("logs", exist_ok=True)
    suffix = f"_{num}" if num > 1 else ""
    return f"logs/user_{user_id}_message{suffix}.txt"

@app.route('/api/message', methods=['GET'])
@login_required
def get_message():
    user_id = session['user_id']
    msg_file = get_user_msg_file(user_id, 1)
    try:
        with open(msg_file, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message', methods=['POST'])
@login_required
def update_message():
    user_id = session['user_id']
    data = request.json
    new_message = data.get('message', '')
    msg_file = get_user_msg_file(user_id, 1)
    try:
        with open(msg_file, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/message2', methods=['GET'])
@login_required
def get_message2():
    user_id = session['user_id']
    msg_file = get_user_msg_file(user_id, 2)
    try:
        with open(msg_file, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message2', methods=['POST'])
@login_required
def update_message2():
    user_id = session['user_id']
    data = request.json
    new_message = data.get('message', '')
    msg_file = get_user_msg_file(user_id, 2)
    try:
        with open(msg_file, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/message3', methods=['GET'])
@login_required
def get_message3():
    user_id = session['user_id']
    msg_file = get_user_msg_file(user_id, 3)
    try:
        with open(msg_file, 'r', encoding="utf-8") as f:
            return jsonify({"message": f.read()})
    except:
        return jsonify({"message": ""})

@app.route('/api/message3', methods=['POST'])
@login_required
def update_message3():
    user_id = session['user_id']
    data = request.json
    new_message = data.get('message', '')
    msg_file = get_user_msg_file(user_id, 3)
    try:
        with open(msg_file, 'w', encoding="utf-8") as f:
            f.write(new_message)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    user_id = session['user_id']
    try:
        cfg = user_db.get_user_config(user_id) or {}
        return jsonify(cfg)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/config', methods=['POST'])
@login_required
def save_config():
    user_id = session['user_id']
    data = request.json
    try:
        old_cfg = user_db.get_user_config(user_id) or {}
        data["ad_bot_running"] = old_cfg.get("ad_bot_running", False)
        data["support_bot_running"] = old_cfg.get("support_bot_running", False)
        data["froxy_bot_running"] = old_cfg.get("froxy_bot_running", False)
        data["lisansarena_bot_running"] = old_cfg.get("lisansarena_bot_running", False)
        
        old_links = old_cfg.get("shopier_links", {})
        new_links = data.get("shopier_links", {})
        for k, v in new_links.items():
            if v:
                old_links[k] = v
        data["shopier_links"] = old_links
        
        user_db.save_user_config(user_id, data)
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
@login_required
def get_scraper_config():
    user_id = session['user_id']
    cfg = user_db.get_user_config(user_id) or {}
    active = cfg.get("scraper_active", True)
    keywords = cfg.get("scrape_keywords", DEFAULT_SCRAPE_KEYWORDS)
    return jsonify({"scraper_active": active, "scrape_keywords": keywords})

@app.route('/api/scraper/config', methods=['POST'])
@login_required
def save_scraper_config():
    user_id = session['user_id']
    data = request.json
    try:
        cfg = user_db.get_user_config(user_id) or {}
        if "scraper_active" in data:
            cfg["scraper_active"] = bool(data["scraper_active"])
        if "scrape_keywords" in data:
            keywords = [k.strip() for k in data["scrape_keywords"] if k.strip()]
            cfg["scrape_keywords"] = keywords
            
        user_db.save_user_config(user_id, cfg)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/scraper/trigger', methods=['POST'])
@login_required
def trigger_scraper():
    user_id = session['user_id']
    flag_file = f"logs/user_{user_id}_trigger_scraper.flag"
    os.makedirs("logs", exist_ok=True)
    try:
        with open(flag_file, "w", encoding="utf-8") as f:
            f.write("trigger")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# AUTO-DM API
# ==========================================

@app.route('/api/autodm/config', methods=['GET'])
@login_required
def get_autodm_config():
    user_id = session['user_id']
    cfg = user_db.get_user_config(user_id) or {}
    return jsonify({
        "auto_dm_active": cfg.get("auto_dm_active", True),
        "max_dm_per_day": cfg.get("max_dm_per_day", 20),
    })

@app.route('/api/autodm/config', methods=['POST'])
@login_required
def save_autodm_config():
    user_id = session['user_id']
    data = request.json
    try:
        cfg = user_db.get_user_config(user_id) or {}
        if "auto_dm_active" in data:
            cfg["auto_dm_active"] = bool(data["auto_dm_active"])
        if "max_dm_per_day" in data:
            cfg["max_dm_per_day"] = int(data["max_dm_per_day"])
        
        user_db.save_user_config(user_id, cfg)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ==========================================
# MESAJ ŞABLONLARI API
# ==========================================

def get_user_messages_dir(user_id):
    path = os.path.join("messages", f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path

@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    user_id = session['user_id']
    user_dir = get_user_messages_dir(user_id)
    templates = []
    if os.path.exists(user_dir):
        for fname in sorted(os.listdir(user_dir)):
            if fname.endswith('.txt'):
                fpath = os.path.join(user_dir, fname)
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
@login_required
def get_template(name):
    user_id = session['user_id']
    user_dir = get_user_messages_dir(user_id)
    safe_name = os.path.basename(name)
    fpath = os.path.join(user_dir, safe_name)
    if not os.path.exists(fpath):
        return jsonify({"error": "Template not found"}), 404
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            return jsonify({"name": safe_name, "content": f.read()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/<name>', methods=['POST'])
@login_required
def save_template(name):
    user_id = session['user_id']
    user_dir = get_user_messages_dir(user_id)
    safe_name = os.path.basename(name)
    data = request.json
    content = data.get('content', '')
    fpath = os.path.join(user_dir, safe_name)
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def get_blacklist(user_id):
    blacklist_file = f"logs/user_{user_id}_blacklist.txt"
    if os.path.exists(blacklist_file):
        try:
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            pass
    return []

def save_blacklist(user_id, blacklist_list):
    blacklist_file = f"logs/user_{user_id}_blacklist.txt"
    os.makedirs("logs", exist_ok=True)
    try:
        with open(blacklist_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(blacklist_list) + '\n')
        
        try:
            import requests
            API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
            PROJECT_ID = "bot-2-63772"
            url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/reklam/saas_state_{user_id}?updateMask.fieldPaths=blacklist_list&key={API_KEY}"
            
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
@login_required
def api_get_blacklist():
    user_id = session['user_id']
    return jsonify(get_blacklist(user_id))

@app.route('/api/blacklist/add', methods=['POST'])
@login_required
def api_add_blacklist():
    user_id = session['user_id']
    data = request.json
    username = data.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({"success": False, "message": "Grup adı boş olamaz."})
    
    blacklist = get_blacklist(user_id)
    blacklist_lower = [b.lower() for b in blacklist]
    if username.lower() not in blacklist_lower:
        blacklist.append(username)
        if save_blacklist(user_id, blacklist):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Kara liste dosyası kaydedilemedi."})
    return jsonify({"success": True, "message": "Grup zaten kara listede."})

@app.route('/api/blacklist/remove', methods=['POST'])
@login_required
def api_remove_blacklist():
    user_id = session['user_id']
    data = request.json
    username = data.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({"success": False, "message": "Grup adı boş olamaz."})
    
    blacklist = get_blacklist(user_id)
    new_blacklist = [b for b in blacklist if b.lower() != username.lower()]
    if len(new_blacklist) != len(blacklist):
        if save_blacklist(user_id, new_blacklist):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Kara liste dosyası kaydedilemedi."})
    return jsonify({"success": False, "message": "Grup kara listede bulunamadı."})

@app.route('/api/groups')
@login_required
def api_groups():
    """Tüm önbelleğe alınan grupları döndür"""
    user_id = session['user_id']
    result = {}
    for fname in ["cached_groups_Hesap_1.json", "cached_groups_Hesap_2.json"]:
        user_fname = f"logs/user_{user_id}_{fname}"
        try:
            with open(user_fname, 'r', encoding='utf-8') as f:
                groups = json.load(f)
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
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not render_url:
        print("[KeepAlive] RENDER_EXTERNAL_URL bulunamadı, keep-alive devre dışı.")
        return
    ping_url = render_url + "/api/status"
    print(f"[KeepAlive] Başlatıldı. Her 10dk {ping_url} adresine ping atılacak.")
    ctx = ssl._create_unverified_context()
    while True:
        try:
            urllib.request.urlopen(ping_url, context=ctx, timeout=10)
        except Exception:
            pass
        time.sleep(600)  # 10 dakika

@app.route('/api/scraped-groups')
@login_required
def get_scraped_groups():
    user_id = session['user_id']
    scraped_file = f"logs/user_{user_id}_scraped_groups.txt"
    groups = []
    if os.path.exists(scraped_file):
        try:
            with open(scraped_file, "r", encoding="utf-8") as f:
                groups = [line.strip() for line in f if line.strip()]
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify(groups)
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

def run_async_auth(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/api/telegram/send-code', methods=['POST'])
@login_required
def tg_send_code():
    user_id = session['user_id']
    data = request.json or {}
    phone = data.get("phone", "").strip()
    api_id = data.get("api_id", "").strip()
    api_hash = data.get("api_hash", "").strip()
    slot = data.get("slot", "1")
    
    if not phone or not api_id or not api_hash:
        return jsonify({"success": False, "message": "Lütfen Telefon, API ID ve API Hash giriniz."})
        
    try:
        api_id_int = int(api_id)
    except:
        return jsonify({"success": False, "message": "API ID geçersiz."})
        
    async def _send():
        if user_id in telegram_logins:
            try:
                await telegram_logins[user_id]["client"].disconnect()
            except: pass
            
        client = TelegramClient(StringSession(), api_id_int, api_hash)
        await client.connect()
        sent_code = await client.send_code_request(phone)
        telegram_logins[user_id] = {
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
@login_required
def tg_verify_code():
    user_id = session['user_id']
    data = request.json or {}
    code = data.get("code", "").strip()
    
    if user_id not in telegram_logins:
        return jsonify({"success": False, "message": "Aktif bir giriş işlemi bulunamadı. Lütfen tekrar deneyin."})
        
    state = telegram_logins[user_id]
    client = state["client"]
    phone = state["phone"]
    phone_code_hash = state["phone_code_hash"]
    slot = state["slot"]
    
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
        telegram_logins.pop(user_id, None)
        
        cfg = user_db.get_user_config(user_id) or {}
        key_name = "ad_string_session" if slot == "1" else f"ad_string_session{slot}"
        cfg[key_name] = session_str
        user_db.save_user_config(user_id, cfg)
        
        return jsonify({"success": True, "message": f"Hesap #{slot} başarıyla bağlandı!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Doğrulama hatası: {str(e)}"})

@app.route('/api/telegram/verify-password', methods=['POST'])
@login_required
def tg_verify_password():
    user_id = session['user_id']
    data = request.json or {}
    password = data.get("password", "").strip()
    
    if user_id not in telegram_logins:
        return jsonify({"success": False, "message": "Aktif bir giriş işlemi bulunamadı."})
        
    state = telegram_logins[user_id]
    client = state["client"]
    slot = state["slot"]
    
    async def _verify_pw():
        await client.sign_in(password=password)
        
    try:
        run_async_auth(_verify_pw())
        session_str = client.session.save()
        run_async_auth(client.disconnect())
        telegram_logins.pop(user_id, None)
        
        cfg = user_db.get_user_config(user_id) or {}
        key_name = "ad_string_session" if slot == "1" else f"ad_string_session{slot}"
        cfg[key_name] = session_str
        user_db.save_user_config(user_id, cfg)
        
        return jsonify({"success": True, "message": f"Hesap #{slot} iki adımlı doğrulama ile başarıyla bağlandı!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Şifre doğrulama hatası: {str(e)}"})

@app.route('/api/admin/licenses', methods=['GET'])
@login_required
def api_admin_get_licenses():
    if session.get('user_id') != 'habil':
        return jsonify({"success": False, "message": "Yetkisiz işlem."}), 403
    try:
        licenses = user_db.get_all_licenses()
        licenses.sort(key=lambda x: (x.get("claimed", False), -x.get("created_at", 0)))
        return jsonify({"success": True, "licenses": licenses})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/admin/licenses', methods=['POST'])
@login_required
def api_admin_generate_license():
    if session.get('user_id') != 'habil':
        return jsonify({"success": False, "message": "Yetkisiz işlem."}), 403
    
    data = request.json or {}
    duration = int(data.get("duration", 30))
    
    import random, string
    rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    key = f"LIC-{rand_part[:4]}-{rand_part[4:]}"
    
    try:
        if user_db.create_license(key, duration):
            return jsonify({"success": True, "key": key})
        return jsonify({"success": False, "message": "Lisans oluşturulamadı."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/admin/licenses/delete', methods=['POST'])
@login_required
def api_admin_delete_license():
    if session.get('user_id') != 'habil':
        return jsonify({"success": False, "message": "Yetkisiz işlem."}), 403
    
    data = request.json or {}
    key = data.get("key", "").strip()
    if not key:
        return jsonify({"success": False, "message": "Lisans anahtarı belirtilmedi."})
        
    try:
        if user_db.delete_license(key):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Lisans silinemedi."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    # Clean up any orphaned bot processes from previous runs on startup
    for script_name in ['otomatik_katil.py', 'froxy_bot.py', 'froxy_destek_bot.py']:
        proc = get_process_by_script(script_name)
        if proc:
            print(f"🧹 Startup cleanup: Killing orphaned process {proc.pid} ({script_name})")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except:
                try: proc.kill()
                except: pass
        pid_file = f"{script_name}.pid"
        if os.path.exists(pid_file):
            try: os.remove(pid_file)
            except: pass

    # Start the watchdog thread
    t = threading.Thread(target=bot_watchdog, daemon=True)
    t.start()
    
    # Start keep-alive thread (Render sleep prevention)
    ka = threading.Thread(target=keep_alive, daemon=True)
    ka.start()
        
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
