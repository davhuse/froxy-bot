import os
import re
import json

def get_known_groups():
    known = set()
    files = ["gruplar.txt", "auto_groups.txt", "scraped_groups.txt", "blacklist.txt", "new_target_groups_found.txt"]
    for f in files:
        if os.path.exists(f):
            with open(f, "r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    line = line.strip().lstrip("@").lower()
                    m = re.search(r"([a-za-z0-9_]{4,32})", line)
                    if m:
                        known.add(m.group(1).lower())
    for f in os.listdir("."):
        if f.startswith("cached_groups_") and f.endswith(".json"):
            try:
                with open(f, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        for k in data.keys():
                            known.add(k.lower().lstrip("@"))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                known.add(item.lower().lstrip("@"))
                            elif isinstance(item, dict):
                                val = item.get("username") or item.get("group")
                                if val:
                                    known.add(val.lower().lstrip("@"))
            except Exception:
                pass
    return sorted(list(known))

if __name__ == "__main__":
    k = get_known_groups()
    print(f"Toplam bilinen/kayıtlı grup sayısı: {len(k)}")
    with open("known_groups_dump.json", "w", encoding="utf-8") as f:
        json.dump(k, f, ensure_ascii=False, indent=2)
