import json
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("candidate_groups_found.json", "r", encoding="utf-8") as f:
    groups = json.load(f)

print(f"Total candidates: {len(groups)}\n")

clean_candidates = []
excluded = []

for g in groups:
    uname = g["username"]
    title = g["title"]
    members = g["members"]
    kw = g["keyword"]
    
    t_lower = title.lower()
    
    # Exclusion checks
    if any(w in t_lower for w in ["nargile", "oto", "otomobil", "فروشگاه", "izmir"]):
        excluded.append((uname, title, "İlgisiz kategori / Yabancı"))
        continue
    
    clean_candidates.append(g)

print(f"Clean Candidates ({len(clean_candidates)}):")
for i, g in enumerate(clean_candidates, 1):
    print(f"{i:2d}. @{g['username']:<25} | Üye: {g['members']:<6} | Başlık: {g['title']}")

print(f"\nExcluded ({len(excluded)}):")
for uname, title, reason in excluded:
    print(f" - @{uname} ({title}) -> {reason}")

with open("final_filtered_candidates.json", "w", encoding="utf-8") as f:
    json.dump(clean_candidates, f, indent=2, ensure_ascii=False)
