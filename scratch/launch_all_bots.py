import os
import sys
import subprocess
import time
import psutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Kill any running instances
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in p.info['name'].lower() and any(k in cmd for k in ['froxy_bot', 'lisansarena_bot', 'otomatik_katil', 'froxy_destek_bot']):
            if p.info['pid'] != os.getpid():
                p.kill()
                print(f"Killed PID {p.info['pid']}")
    except Exception:
        pass

time.sleep(2)

env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'

bots = [
    ('otomatik_katil.py', 'bot_log.txt'),
    ('lisansarena_bot.py', 'lisansarena_bot_log.txt'),
    ('froxy_bot.py', 'froxy_bot_log.txt'),
    ('froxy_destek_bot.py', 'froxy_destek_bot_log.txt')
]

for script, logfile in bots:
    if os.path.exists(script):
        f = open(logfile, 'a', encoding='utf-8')
        p = subprocess.Popen([sys.executable, '-u', script], stdout=f, stderr=f, env=env, creationflags=0x08000208)
        print(f"✅ Launched {script:<25} (PID: {p.pid}) -> Log: {logfile}")

print("\n🚀 All Telegram Bot services have been restarted in the background!")
