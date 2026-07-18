import sys
import re

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

log_file = "bot_log.txt"
print("Checking bot_log.txt for leave events...")
leave_patterns = [
    r"grubundan çıkıldı",
    r"gruptan çıkılıyor",
    r"kara listeye alınıp çıkılıyor",
    r"çıkıldı",
    r"LeaveChannelRequest"
]

try:
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f):
            if any(re.search(pat, line, re.IGNORECASE) for pat in leave_patterns):
                safe_line = line.strip().encode('utf-8', errors='replace').decode('utf-8')
                print(f"Line {idx+1}: {safe_line}")
except Exception as e:
    print(f"Error reading log: {e}")
