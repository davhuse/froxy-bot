import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

log_path = r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\bot_log.txt"

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    print(f"Tail of log ({len(lines)} lines):")
    for line in lines[-50:]:
        print(line.strip())
else:
    print("Log file not found.")
