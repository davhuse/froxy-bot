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

DEFAULT_SCRAPE_KEYWORDS = [
    "kupon satış", "kod satış", "kupon çek", "kupon satis",
    "alım satım", "ticaret grubu", "satış grubu", "ilan grubu",
    "hesap satış", "dijital ilan", "smm panel",
    "indirim kupon", "fırsat indirim", "reklam grubu",
    "ikinci el", "2.el satış", "alim satim",
    "e-ticaret satış", "trendyol satıcı", "freelance iş",
    "referans reklam", "satılık ilan", "epin satış"
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
def get_scraped_groups():
    groups = []
    if os.path.exists("scraped_groups.txt"):
        try:
            with open("scraped_groups.txt", "r", encoding="utf-8") as f:
                groups = [line.strip() for line in f if line.strip()]
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify({"groups": groups})

if __name__ == '__main__':
    # Start the watchdog thread
    t = threading.Thread(target=bot_watchdog, daemon=True)
    t.start()
    
    # Start keep-alive thread (Render sleep prevention)
    ka = threading.Thread(target=keep_alive, daemon=True)
    ka.start()
        
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
