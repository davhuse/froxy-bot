import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open("all_trader_active_groups.json", "r", encoding="utf-8") as f:
    trader_groups = json.load(f)

with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
    active_in_gruplar = {line.strip().lower().lstrip("@") for line in f if line.strip()}

with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
    blacklisted = {line.strip().lower().lstrip("@") for line in f if line.strip()}

already_in_gruplar = []
in_blacklist = []
completely_new = []

for u, data in trader_groups.items():
    u_clean = u.lower().lstrip("@")
    title = data.get("title", "")
    queries = data.get("matched_queries", [])
    if u_clean in active_in_gruplar:
        already_in_gruplar.append((u_clean, title, queries))
    elif u_clean in blacklisted:
        in_blacklist.append((u_clean, title, queries))
    else:
        completely_new.append((u_clean, title, queries))

print(f"Total in all_trader_active_groups: {len(trader_groups)}")
print(f"In gruplar.txt: {len(already_in_gruplar)}")
print(f"In blacklist.txt: {len(in_blacklist)}")
print(f"Completely New: {len(completely_new)}")

print("\n=== COMPLETELY NEW & NOT IN LISTS ===")
for u, t, q in completely_new:
    print(f" - @{u:<24} | {t[:28]:<28} | {q}")
