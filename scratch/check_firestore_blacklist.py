import os
import requests

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def fs_get_state():
    try:
        url = f"{BASE_URL}/reklam/state?key={API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            fields = r.json().get("fields", {})
            progress = fields.get("progress_list", {}).get("stringValue", "")
            blacklist = fields.get("blacklist_list", {}).get("stringValue", "")
            auto_groups = fields.get("auto_groups_list", {}).get("stringValue", "")
            scraped_groups = fields.get("scraped_groups_list", {}).get("stringValue", "")
            cooldowns = fields.get("cooldowns_list", {}).get("stringValue", "")
            return progress, blacklist, auto_groups, scraped_groups, cooldowns
    except Exception as e:
        print(f"Firestore load error: {e}")
    return "", "", "", "", ""

target_groups = [
    "ticaretforumofficial", "sultanbeyliikinciel0", "tahaaslan11", "casinox_grup",
    "reklamonliene", "alimsatimmerkezii", "illegalalimsatimerkezi", "ilanticaret",
    "reklamreferans", "sosyalmedyaalimsatimticaret", "referansreklamyardimlasma",
    "sanalalimsatimticaret", "kuponsatisgrup", "referansreklam1", "referanslinkpaylasimigrup",
    "kuponsatislari0", "yucekuponsatis", "letgoilanlari", "-1001572316417", "-3608209943",
    "ticar4t", "kuponhesapsatis", "reklamvereferanss", "kuponvekodsatisgrubu", "indirimkodusatis",
    "takipcisatiyor", "ttingalimsatim", "auzefeticaretreklamsiz", "kuponceksatisi", "alcaponesat",
    "kuponsatimalim", "dolapilanlari", "gurcistanticaret"
]

print("Reading state from Firestore...")
_, fs_black, _, _, _ = fs_get_state()
if not fs_black:
    print("Firestore blacklist is empty or not found!")
else:
    blacklisted_in_fs = set(x.strip().lower() for x in fs_black.splitlines() if x.strip())
    print(f"Total blacklisted in Firestore: {len(blacklisted_in_fs)}")
    
    found = []
    for tg in target_groups:
        if tg.lower() in blacklisted_in_fs:
            found.append(tg)
            print(f"  BLACKLISTED ON FIRESTORE: {tg}")
    print(f"Total target groups blacklisted on Firestore: {len(found)}")
