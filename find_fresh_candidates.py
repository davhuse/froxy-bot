import json
import os
import re
import urllib.request
import html
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. Active blasting list
active_groups = set()
with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        u = line.strip().lower().lstrip("@")
        if u:
            active_groups.add(u)

# 2. Blacklist
blacklist = set()
with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        u = line.strip().lower().lstrip("@")
        if u:
            blacklist.add(u)

print(f"Mevcut Aktif Blast Listesi: {len(active_groups)} grup")
print(f"Kara Liste: {len(blacklist)} grup")

# Gather all candidates from all files
candidate_pool = set()
for fn in os.listdir("."):
    if not (fn.endswith(".json") or fn.endswith(".txt")):
        continue
    if fn in ["gruplar.txt", "blacklist.txt"]:
        continue
    try:
        if fn.endswith(".json"):
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                d = json.load(f)
                items = d if isinstance(d, list) else (list(d.values()) if isinstance(d, dict) else [])
                for it in items:
                    if isinstance(it, dict):
                        uname = it.get("username") or it.get("group")
                        if uname and isinstance(uname, str):
                            u = uname.lower().strip().lstrip("@")
                            if 3 < len(u) < 35:
                                candidate_pool.add(u)
                    elif isinstance(it, str):
                        u = it.lower().strip().lstrip("@")
                        if 3 < len(u) < 35:
                            candidate_pool.add(u)
        elif fn.endswith(".txt"):
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for m in re.finditer(r"([a-zA-Z0-9_]{4,32})", line):
                        u = m.group(1).lower()
                        if u not in {"joinchat", "share", "proxy", "http", "https", "true", "false", "none"}:
                            candidate_pool.add(u)
    except Exception:
        pass

print(f"Toplam Aday Havuzu: {len(candidate_pool)}")

# Filter out groups already in gruplar.txt or blacklist.txt
fresh_candidates = sorted(list(candidate_pool - active_groups - blacklist))
print(f"Mevcut Listede Olmayan Taze Aday Sayısı: {len(fresh_candidates)}")

with open("fresh_candidates_to_audit.json", "w", encoding="utf-8") as f:
    json.dump(fresh_candidates, f, indent=2)
