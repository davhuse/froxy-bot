import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

files = [f for f in os.listdir(".") if f.startswith("message") and f.endswith(".txt")]
print(f"Found {len(files)} message files:")

for fname in sorted(files):
    print(f"\n======================================")
    print(f"File: {fname}")
    print(f"======================================")
    with open(fname, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
        safe_content = content.encode('utf-8', errors='replace').decode('utf-8')
        print(safe_content)
