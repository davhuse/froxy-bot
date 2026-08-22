import json
import os
import re

all_known_excluded = set()

files_to_check = [
    "gruplar.txt", "blacklist.txt", "master_known_blacklist.json",
    "banned_groups.txt", "active_groups_current.txt", "session_blacklist.json",
    "failed_groups.txt", "spam_groups.txt", "old_blacklist.txt"
]

for fn in os.listdir("."):
    if not (fn.endswith(".txt") or fn.endswith(".json")):
        continue
    # Let's check files with blacklist / grup / list in name
    if any(k in fn.lower() for k in ["blacklist", "gruplar", "banned", "spam", "failed", "master"]):
        try:
            if fn.endswith(".json"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        for item in d:
                            if isinstance(item, str):
                                all_known_excluded.add(item.lower().strip().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u and isinstance(u, str):
                                    all_known_excluded.add(u.lower().strip().lstrip("@"))
                    elif isinstance(d, dict):
                        for k, v in d.items():
                            all_known_excluded.add(k.lower().strip().lstrip("@"))
            elif fn.endswith(".txt"):
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for m in re.finditer(r"([a-zA-Z0-9_]{4,32})", line):
                            all_known_excluded.add(m.group(1).lower())
        except Exception:
            pass

print(f"Total exhaustive excluded groups across all blacklist/target files: {len(all_known_excluded)}")
with open("exhaustive_excluded_groups.json", "w", encoding="utf-8") as f:
    json.dump(sorted(list(all_known_excluded)), f, indent=2)
