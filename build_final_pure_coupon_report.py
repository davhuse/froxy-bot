import json
import os

# Load task-400 results
with open("birebir_saf_kupon_kod_gruplari.json", "r", encoding="utf-8") as f:
    task_groups = json.load(f)

# Load previously vetted target groups
with open("yeni_birebir_hedef_gruplar.json", "r", encoding="utf-8") as f:
    prev_groups = json.load(f)

# Combine both lists and deduplicate
combined_map = {}
for g in task_groups + prev_groups:
    u = g["username"].lower()
    
    # Exclude game accounts or irrelevant groups
    if u in ["pubgmobilehesapalimsatim", "bonuslardiyarii", "kuponprofesoruu", "texasconfigchat", "ikinciel01chat", "smsngsatis"]:
        continue
        
    if u not in combined_map:
        combined_map[u] = g

final_list = list(combined_map.values())

# Sort by online count and member count
final_list.sort(key=lambda x: (-x["online"], -x["members"]))

print(f"Final 1'e 1 Saf Kupon / Kod / Ticaret Grubu Sayısı: {len(final_list)}")

with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
    json.dump(final_list, f, ensure_ascii=False, indent=2)

with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
    for g in final_list:
        f.write(f"{g['username']}\n")

print("\n--- 1'E 1 BİREBİR HEDEF KUPON / KOD / TİCARET GRUPLARI ---")
for idx, g in enumerate(final_list, 1):
    print(f"{idx:2d}. @{g['username']:<26} | Üye: {g['members']:<6} | Online: {g['online']:<4} | {g['category']}")
