import os
import sys
import time
import psutil

sys.stdout.reconfigure(encoding='utf-8')

print("Force cleaning all stale ad bot and control bot processes...")

killed = 0
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in p.info['name'].lower():
            # Match any of our script keywords
            if any(k in cmd for k in ['otomatik_katil', 'froxy_bot', 'lisansarena_bot', 'froxy_destek_bot', 'watchdog_service', 'watchdog.py', 'control_bot.py']):
                if p.info['pid'] != os.getpid():
                    p.kill()
                    print(f"✅ Killed PID {p.info['pid']}: {cmd[:100]}...")
                    killed += 1
    except Exception as e:
        pass

print(f"\nCleaned up {killed} stale background processes.")
time.sleep(3)
