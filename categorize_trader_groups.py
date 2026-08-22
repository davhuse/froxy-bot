import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open("all_discovered_global_groups.json", "r", encoding="utf-8") as f:
    all_groups = json.load(f)

with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
    active_in_gruplar = {line.strip().lower().lstrip("@") for line in f if line.strip()}

with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
    hard_blacklist = {line.strip().lower().lstrip("@") for line in f if line.strip()}

print(f"Total globally discovered active trader groups: {len(all_groups)}")
print(f"Active in gruplar.txt: {len(active_in_gruplar)}")
print(f"In hard blacklist.txt: {len(hard_blacklist)}")

in_gruplar = []
in_blacklist = []
candidate_for_user = []

for u, data in all_groups.items():
    u_clean = u.lower().lstrip("@")
    title = data.get("title", "")
    queries = data.get("matched_queries", [])
    samples = data.get("sample_messages", [])
    
    if u_clean in active_in_gruplar:
        in_gruplar.append((u_clean, title, len(queries)))
    elif u_clean in hard_blacklist:
        in_blacklist.append((u_clean, title, len(queries)))
    else:
        candidate_for_user.append((u_clean, title, queries, samples))

print(f"\n--- GROUPS CURRENTLY IN GRUPLAR.TXT ({len(in_gruplar)}) ---")
for u, t, qcnt in in_gruplar:
    print(f"  @{u:<24} | {t[:28]:<28} | ({qcnt} query matches)")

print(f"\n--- GROUPS IN HARD BLACKLIST.TXT ({len(in_blacklist)}) ---")
for u, t, qcnt in in_blacklist:
    print(f"  @{u:<24} | {t[:28]:<28} | ({qcnt} query matches)")

print(f"\n--- GROUPS NOT IN GRUPLAR.TXT AND NOT IN BLACKLIST.TXT ({len(candidate_for_user)}) ---")
for u, t, q, s in candidate_for_user:
    print(f"  @{u:<24} | {t[:28]:<28} | Eşleşen: {q}")
    if s:
        print(f"    Canlı Mesaj: {s[0][:90]}...")
