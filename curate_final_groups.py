import json
import os

def create_curated_list():
    all_groups = []
    seen = set()
    
    # 1. Load round 1
    if os.path.exists("yeni_onayli_gruplar_raporu.json"):
        with open("yeni_onayli_gruplar_raporu.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for g in data.get("approved_groups", []):
                u = g["username"].lower()
                if u not in seen:
                    seen.add(u)
                    all_groups.append(g)
                    
    # 2. Load round 2
    if os.path.exists("yeni_onayli_gruplar_v2.json"):
        with open("yeni_onayli_gruplar_v2.json", "r", encoding="utf-8") as f:
            data2 = json.load(f)
            for g in data2:
                u = g["username"].lower()
                if u not in seen:
                    seen.add(u)
                    all_groups.append(g)

    # Strictly filter out game accounts, real estate, off-topic
    curated = []
    excluded_keywords = ["pubg", "pes", "brawl", "efootball", "roblox", "gayrimenkul", "emlak", "ev alım", "config"]
    
    for g in all_groups:
        title = g.get("title", "").lower()
        about = g.get("about", "").lower()
        username = g.get("username", "").lower()
        combined = f"{username} {title} {about}"
        
        # Check exclusion
        if any(ex in combined for ex in excluded_keywords):
            continue
            
        curated.append(g)
        
    curated.sort(key=lambda x: x["members"], reverse=True)
    
    with open("nihai_onayli_yeni_satis_gruplari.json", "w", encoding="utf-8") as out:
        json.dump({
            "total_curated_groups": len(curated),
            "groups": curated
        }, out, ensure_ascii=False, indent=2)
        
    print(f"Toplam nihai filtrelenmiş grup sayısı: {len(curated)}")

if __name__ == "__main__":
    create_curated_list()
