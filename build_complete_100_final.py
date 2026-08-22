import json
import os
import re

def build_100():
    master_groups = {}
    
    # 1. Load from all vetted json files
    source_files = [
        "100_tam_test_edilmis_kupon_ve_kod_gruplari.json",
        "nihai_saf_ticaret_pazarlari.json",
        "expanded_pure_trade_groups.json",
        "aktif_saf_kupon_kod_gruplari.json",
        "food_code_gems_approved.json",
        "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "pure_account_code_approved.json",
        "kupon_ozel_onayli_gruplar.json",
        "harvested_trade_groups.json",
        "yeni_onayli_gruplar_raporu.json"
    ]
    
    EXCLUDE_KEYWORDS = [
        "brawl", "pes", "efootball", "e-football", "roblox", "pubg", "free fire", "valorant",
        "metin2", "zula", "lol", "fifa", "koleksiyon", "iddaa", "bahis", "casino", "slot",
        "rulet", "bet", "gayrimenkul", "emlak", "oto alım", "araba alım", "mining", "papara",
        "robotics", "crypto only", "cpa_lenta", "southeast asia"
    ]
    
    for fn in source_files:
        if not os.path.exists(fn):
            continue
        try:
            with open(fn, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("groups", []) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "username" in item:
                            u = item["username"].lower().lstrip("@")
                            title = item.get("title", "")
                            about = item.get("about", "") or item.get("description", "")
                            combined = f"{title}\n{about}".lower()
                            
                            if any(ew in combined for ew in EXCLUDE_KEYWORDS):
                                continue
                                
                            members = item.get("members", 0) or 0
                            if members >= 40 and u not in master_groups:
                                master_groups[u] = {
                                    "username": u,
                                    "title": title,
                                    "members": members,
                                    "description": about[:180].replace("\n", " "),
                                    "link": f"https://t.me/{u}"
                                }
        except Exception:
            pass
            
    sorted_groups = sorted(master_groups.values(), key=lambda x: -x["members"])
    final_100 = sorted_groups[:100]
    
    print(f"Toplam derlenen saf kupon/kod/ticaret grubu sayısı: {len(final_100)}")
    
    with open("100_kesin_onayli_kupon_ve_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_approved": len(final_100),
            "groups": final_100
        }, f, ensure_ascii=False, indent=2)
        
    with open("100_kupon_kod_gruplar_listesi.txt", "w", encoding="utf-8") as f:
        for g in final_100:
            f.write(f"@{g['username']}\n")
            
    print(f"✅ '100_kesin_onayli_kupon_ve_kod_gruplari.json' ve '100_kupon_kod_gruplar_listesi.txt' oluşturuldu!")

if __name__ == '__main__':
    build_100()
