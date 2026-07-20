import os
import sys
import time
import subprocess
import psutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BOT_SCRIPTS = [
    ("otomatik_katil.py", "bot_log.txt"),
    ("froxy_bot.py", "froxy_bot_log.txt"),
    ("lisansarena_bot.py", "lisansarena_bot_log.txt")
]

processes = {}

def get_running_cmdlines():
    running = {}
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = ' '.join(p.info['cmdline'] or [])
            if 'python' in p.info['name'].lower():
                for script, _ in BOT_SCRIPTS:
                    if script in cmd:
                        running[script] = p.info['pid']
        except Exception:
            pass
    return running

def start_bot(script, logfile):
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    f = open(logfile, 'a', encoding='utf-8')
    p = subprocess.Popen([sys.executable, '-u', script], stdout=f, stderr=f, env=env, creationflags=0x08000208)
    print(f"🚀 [WATCHDOG] Started {script} (PID: {p.pid})")
    return p.pid

def main():
    print("====================================================")
    print("     HABİL REKLAM & SATIŞ BOTLARI WATCHDOG SERVİSİ   ")
    print("====================================================\n")
    print("🛡️ Nöbetçi Servis Aktif: Tüm botlar 7/24 izleniyor ve çökerse anında otomatik yeniden başlatılacak.\n")

    while True:
        try:
            running = get_running_cmdlines()
            for script, logfile in BOT_SCRIPTS:
                if script not in running:
                    print(f"⚠️ [WATCHDOG] {script} kapalı/çökmüş tespit edildi! Otomatik yeniden başlatılıyor...")
                    pid = start_bot(script, logfile)
                    running[script] = pid
        except Exception as e:
            print(f"⚠️ [WATCHDOG Error]: {e}")
        time.sleep(10)

if __name__ == '__main__':
    main()
