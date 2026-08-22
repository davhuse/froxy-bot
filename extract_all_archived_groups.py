import json
import os
import re

files = [
    "100_kesin_onayli_kupon_kod_gruplari.json",
    "100_kesin_onayli_kupon_ve_kod_gruplari.json",
    "100_onayli_test_edilmis_kupon_gruplari.json",
    "100_tam_dogrulanmis_kupon_kod_gruplari.json",
    "100_tam_test_edilmis_kupon_ve_kod_gruplari.json",
    "aktif_saf_kupon_kod_gruplari.json",
    "canli_mesaj_onayli_kupon_gruplari.json",
    "kupon_ozel_onayli_gruplar.json",
    "birebir_yeni_kupon_kod_alimsatim_gruplari.json",
    "food_code_gems_approved.json",
    "pure_account_code_approved.json",
    "derin_kesif_onayli_yeni_gruplar.json",
    "derin_web_kesif_onayli.json",
    "kesinlikle_yepyeni_kupon_gruplari.json",
    "yep_yeni_kupon_gruplari_kesif.json",
    "nihai_saf_ticaret_pazarlari.json",
    "expanded_pure_trade_groups.json"
]

all_extracted_groups = {}

for fn in files:
    if not os.path.exists(fn):
        continue
    try:
        with open(fn, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if "groups" in data and isinstance(data["groups"], list):
                    items = data["groups"]
                elif "approved_groups" in data and isinstance(data["approved_groups"], list):
                    items = data["approved_groups"]
                else:
                    for k, v in data.items():
                        if isinstance(v, list):
                            items.extend(v)
            for item in items:
                if isinstance(item, dict):
                    uname = item.get("username") or item.get("group")
                    if uname and isinstance(uname, str):
                        u_clean = uname.strip().lower().lstrip("@")
                        if u_clean not in all_extracted_groups:
                            all_extracted_groups[u_clean] = item
                elif isinstance(item, str):
                    u_clean = item.strip().lower().lstrip("@")
                    if u_clean not in all_extracted_groups:
                        all_extracted_groups[u_clean] = {"username": u_clean}
    except Exception as e:
        print(f"Error {fn}: {e}")

print(f"Total unique groups across existing archives: {len(all_extracted_groups)}")
with open("all_archived_coupon_groups.json", "w", encoding="utf-8") as f:
    json.dump(all_extracted_groups, f, ensure_ascii=False, indent=2)
