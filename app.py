from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
import json
import threading
import time
import psutil

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

# State variables for background processes
ad_process = None
support_process = None
froxy_process = None

LOG_FILE = "bot_log.txt"
SUPPORT_LOG_FILE = "froxy_bot_log.txt"
FROXY_LOG_FILE = "froxy_destek_log.txt"
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
def get_process_by_script(script_name):
    """Finds a running python process that executes script_name."""
    # 1. Try checking the PID file first
    pid_file = f"{script_name}.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                cmd = proc.cmdline() or []
                if any(script_name in arg for arg in cmd):
                    return proc
        except Exception:
            pass

    # 2. Fallback to process iteration
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline') or []
            if any(script_name in arg for arg in cmd):
                # Save it to the PID file for future fast checks
                try:
                    with open(pid_file, "w") as f:
                        f.write(str(proc.pid))
                except:
                    pass
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def kill_process_by_script(script_name):
    """Kills any running python process that executes script_name."""
    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline') or []
            if any(script_name in arg for arg in cmd):
                print(f"Killing orphan process {proc.info['pid']} running {script_name}")
                for child in proc.children(recursive=True):
                    try: child.terminate()
                    except: pass
                proc.terminate()
                try: proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed

# WATCHDOG SYSTEM: Keeps both bots running 24/7 unconditionally
def bot_watchdog():
    global ad_process, support_process
    print("🛡️ [Watchdog] Bot takip sistemi başlatıldı. Botlar her 15 saniyede bir denetlenecek.")
    time.sleep(5) # Give the system some time to initialize
    
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
                        [sys.executable, 'otomatik_katil.py'],
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
                        [sys.executable, 'froxy_bot.py'],
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
                    froxy_enabled = cfg.get("froxy_bot_running", False)
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
                        [sys.executable, 'froxy_destek_bot.py'],
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
    is_running = get_process_by_script('otomatik_katil.py') is not None
    return jsonify({"status": "running" if is_running else "stopped"})

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
                    if "Mesaj gönderildi!" in line:
                        sent_count += 1
        except:
            pass
            
    total_groups = 0
    try:
        # Avoid full import overhead by parsing gruplar length directly
        with open("otomatik_katil.py", "r", encoding="utf-8") as f:
            content = f.read()
            # Match the gruplar list size roughly or import safely since watchdog isn't running main
            from otomatik_katil import gruplar
            total_groups = len(gruplar)
    except Exception as e:
        print(f"Error reading total groups: {e}")
        total_groups = 410 # Fallback default
        
    return jsonify({
        "total_groups": total_groups,
        "done_groups": done_count,
        "blacklist_groups": blacklist_count,
        "sent_messages": sent_count
    })

@app.route('/api/start', methods=['POST'])
def start():
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
            [sys.executable, 'otomatik_katil.py'],
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
            [sys.executable, 'froxy_bot.py'],
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
            [sys.executable, 'froxy_destek_bot.py'],
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
@app.route('/api/config', methods=['GET'])
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return jsonify({})
    try:
        with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
            return jsonify(json.load(f))
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
            
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    # Start the watchdog thread
    t = threading.Thread(target=bot_watchdog, daemon=True)
    t.start()
        
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
