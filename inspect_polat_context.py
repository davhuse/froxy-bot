import urllib.request
import json
import re

url = "https://froxy-bot-kgky.onrender.com/api/logs"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
logs = data.get("logs", [])

for i, line in enumerate(logs):
    if "polat" in line.lower() or "5112921888" in line:
        start = max(0, i - 15)
        end = min(len(logs), i + 15)
        print(f"\n--- CONTEXT AROUND LINE {i} ---")
        for idx in range(start, end):
            print(logs[idx].encode("ascii", errors="replace").decode("ascii"))
