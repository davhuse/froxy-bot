import psutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in p.info['name'].lower():
            print(f"PID {p.info['pid']}: {cmd[:120]}")
    except Exception:
        pass
