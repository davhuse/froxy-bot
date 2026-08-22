import json
import urllib.request
import re

with open("yeni_birebir_hedef_gruplar.json", "r", encoding="utf-8") as f:
    groups = json.load(f)

# Hard filters against pure deal channels where only admins post affiliate links
ADMIN_DEAL_INDICATORS = [
    "indirimde al", "indirim paylaşımları", "fırsat paylaşımları", "günün fırsatları"
]

pure_vetted = []

for g in groups:
    uname = g["username"]
    title = g["title"].lower()
    desc = g.get("about_description", "").lower()
    
    # 1. Skip admin deal / affiliate announcement groups
    if uname in ["indirimdeal", "indirimciyizbiz", "buy_panel_premium_members_adder"]:
        continue
    if any(adi in title for adi in ADMIN_DEAL_INDICATORS):
        continue
        
    pure_vetted.append(g)

print(f"[*] Tam Uyumlu Saf Grup Sayısı: {len(pure_vetted)}")

with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
    json.dump(pure_vetted, f, ensure_ascii=False, indent=2)

with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
    for g in pure_vetted:
        f.write(f"{g['username']}\n")

for idx, g in enumerate(pure_vetted, 1):
    print(f"{idx:2d}. @{g['username']:<25} | Üye: {g['members']:<6} | Online: {g['online']:<4} | {g['category']}")
