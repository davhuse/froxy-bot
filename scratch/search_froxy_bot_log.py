import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

log_path = r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\froxy_bot_log.txt"
if os.path.exists(log_path):
    print("Searching local froxy_bot_log.txt...")
    found = False
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if "islamix" in line.lower():
                print(f"Line {i}: {line.strip()}")
                found = True
    if not found:
        print("No match in local froxy_bot_log.txt.")
else:
    print("froxy_bot_log.txt not found.")
