import os
import json
import re

for fn in os.listdir("."):
    if not (fn.endswith(".txt") or fn.endswith(".json")):
        continue
    if any(k in fn.lower() for k in ["blacklist", "gruplar", "banned", "spam", "failed", "master", "sess"]):
        count = 0
        try:
            if fn.endswith(".json"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        count = len(d)
                    elif isinstance(d, dict):
                        count = len(d)
            elif fn.endswith(".txt"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    count = len([l for l in f if l.strip()])
            print(f"File: {fn:<35} | Entries: {count}")
        except Exception as e:
            print(f"File: {fn:<35} | Error: {e}")
