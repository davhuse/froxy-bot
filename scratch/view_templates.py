import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

templates = [
    "message_a.txt", "message_b.txt", "message_c.txt",
    "message_2a.txt", "message_2b.txt", "message_2c.txt",
    "message_3a.txt", "message_3b.txt", "message_3c.txt"
]

print("=== CHECKING AD BLAST MESSAGE TEMPLATES ===")
for t in templates:
    print(f"\n--- {t} ---")
    if os.path.exists(t):
        with open(t, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Print first 200 chars or full content if small
            print(content if len(content) < 300 else content[:300] + "\n... (truncated)")
    else:
        print("[NOT FOUND]")
