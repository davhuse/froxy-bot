from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
import json
import threading
import time

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

# State variables for background processes
ad_process = None
support_process = None

LOG_FILE = "bot_log.txt"
SUPPORT_LOG_FILE = "froxy_bot_log.txt"
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

            # 1. Check Ad Bot (otomatik_katil.py) - Always run
            if ad_process is None or ad_process.poll() is not None:
                print("📢 [Watchdog] Reklam botu aktif değil veya durmuş. Başlatılıyor...")
                # Write a startup log
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write("\n🚀 [Watchdog] Reklam botu otomatik olarak başlatılıyor...\n")
                
                file_out = open(LOG_FILE, 'a', encoding="utf-8", buffering=1)
                ad_process = subprocess.Popen(
                    [sys.executable, 'otomatik_katil.py'],
                    stdout=file_out,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                    env=env
                )
                update_config_state("ad_bot_running", True)

            # 2. Check Support Bot (froxy_bot.py) - Only run if configured
            has_token = False
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    token = cfg.get("bot_token", "")
                    if token and token != "YOUR_TELEGRAM_BOT_TOKEN":
                        has_token = True
                except Exception as ex:
                    print(f"Error checking config: {ex}")
            
            if has_token:
                if support_process is None or support_process.poll() is not None:
                    print("🤖 [Watchdog] Destek botu aktif değil veya durmuş. Başlatılıyor...")
                    with open(SUPPORT_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write("\n🚀 [Watchdog] Destek botu otomatik olarak başlatılıyor...\n")
                    
                    file_out = open(SUPPORT_LOG_FILE, 'a', encoding="utf-8", buffering=1)
                    support_process = subprocess.Popen(
                        [sys.executable, 'froxy_bot.py'],
                        stdout=file_out,
                        stderr=subprocess.STDOUT,
                        creationflags=flags,
                        env=env
                    )
                    update_config_state("support_bot_running", True)
            else:
                print("⚠️ [Watchdog] Destek botu için geçerli bir Token bulunamadı. Bekleniyor...")

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
    global ad_process
    is_running = ad_process is not None and ad_process.poll() is None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/start', methods=['POST'])
def start():
    global ad_process
    if ad_process is not None and ad_process.poll() is None:
        return jsonify({"success": False, "message": "Reklam botu zaten çalışıyor!"})
    
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("🚀 Reklam botu başlatılıyor...\n")
        
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(LOG_FILE, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        ad_process = subprocess.Popen(
            [sys.executable, 'otomatik_katil.py'],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        update_config_state("ad_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/stop', methods=['POST'])
def stop():
    global ad_process
    if ad_process is not None and ad_process.poll() is None:
        try:
            ad_process.terminate()
            ad_process.wait(timeout=3)
        except Exception:
            try:
                ad_process.kill()
            except: pass
            
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n🛑 Reklam botu kullanıcı tarafından durduruldu.\n")
            
        ad_process = None
        update_config_state("ad_bot_running", False)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Reklam botu zaten durmuş durumda!"})

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
    global support_process
    is_running = support_process is not None and support_process.poll() is None
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route('/api/support/start', methods=['POST'])
def support_start():
    global support_process
    if support_process is not None and support_process.poll() is None:
        return jsonify({"success": False, "message": "Destek botu zaten çalışıyor!"})
    
    # Check if Bot Token is set first
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
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        file_out = open(SUPPORT_LOG_FILE, 'a', encoding="utf-8", buffering=1)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        support_process = subprocess.Popen(
            [sys.executable, 'froxy_bot.py'],
            stdout=file_out,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env
        )
        update_config_state("support_bot_running", True)
        return jsonify({"success": True})
    except Exception as e:
         return jsonify({"success": False, "message": str(e)})

@app.route('/api/support/stop', methods=['POST'])
def support_stop():
    global support_process
    if support_process is not None and support_process.poll() is None:
        try:
            support_process.terminate()
            support_process.wait(timeout=3)
        except Exception:
            try:
                support_process.kill()
            except: pass
            
        with open(SUPPORT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n🛑 Destek ve Satış botu kullanıcı tarafından durduruldu.\n")
            
        support_process = None
        update_config_state("support_bot_running", False)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Destek botu zaten durmuş durumda!"})

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
        # Keep internal running states when saving config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                old_cfg = json.load(f)
            data["ad_bot_running"] = old_cfg.get("ad_bot_running", False)
            data["support_bot_running"] = old_cfg.get("support_bot_running", False)
            
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
