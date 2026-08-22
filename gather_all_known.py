import os
import json
import re

def gather_all_known():
    known = set()
    files = [
        "known_groups_dump.json", "gruplar.txt", "auto_groups.txt", "scraped_groups.txt",
        "yeni_onayli_gruplar_raporu.json", "yeni_onayli_gruplar_v2.json",
        "nihai_onayli_yeni_satis_gruplari.json", "kupon_ozel_onayli_gruplar.json",
        "pure_account_code_approved.json", "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
        "harvested_trade_groups.json"
    ]
    for fn in files:
        if not os.path.exists(fn):
            continue
        if fn.endswith(".json"):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                known.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                u = item.get("username") or item.get("group")
                                if u:
                                    known.add(u.lower().lstrip("@"))
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict) and "username" in item:
                                        known.add(item["username"].lower().lstrip("@"))
                                    elif isinstance(item, str):
                                        known.add(item.lower().lstrip("@"))
                            elif isinstance(k, str) and len(k) < 35:
                                known.add(k.lower().lstrip("@"))
            except Exception:
                pass
        elif fn.endswith(".txt"):
            try:
                with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip().lstrip("@").lower()
                        m = re.search(r"([a-z0-9_]{4,32})", line)
                        if m:
                            known.add(m.group(1).lower())
            except Exception:
                pass

    print(f"Toplam bilinen / daha önce işlenen grup sayısı: {len(known)}")
    with open("master_known_blacklist.json", "w", encoding="utf-8") as out:
        json.dump(sorted(list(known)), out, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    gather_all_known()
