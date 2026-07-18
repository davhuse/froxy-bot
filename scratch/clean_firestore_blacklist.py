import os
import requests
import json

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# Whitelisted target groups
whitelist_groups = [
    "ticaretforumofficial", "sultanbeyliikinciel0", "tahaaslan11", "casinox_grup",
    "reklamonliene", "alimsatimmerkezii", "illegalalimsatimerkezi", "ilanticaret",
    "reklamreferans", "sosyalmedyaalimsatimticaret", "referansreklamyardimlasma",
    "sanalalimsatimticaret", "kuponsatisgrup", "referansreklam1", "referanslinkpaylasimigrup",
    "kuponsatislari0", "yucekuponsatis", "letgoilanlari", "-1001572316417", "-3608209943",
    "ticar4t", "kuponhesapsatis", "reklamvereferanss", "kuponvekodsatisgrubu", "indirimkodusatis",
    "takipcisatiyor", "ttingalimsatim", "auzefeticaretreklamsiz", "kuponceksatisi", "alcaponesat",
    "kuponsatimalim", "dolapilanlari", "gurcistanticaret"
]

protected_groups = set(g.lower() for g in whitelist_groups)
if os.path.exists("auto_groups.txt"):
    with open("auto_groups.txt", "r", encoding="utf-8") as f:
        for line in f:
            g = line.strip().lower()
            if g:
                protected_groups.add(g)

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

def fs_set_blacklist(blacklist_str):
    url = f"{BASE_URL}/reklam/state?key={API_KEY}&updateMask.fieldPaths=blacklist_list"
    payload = {
        "fields": {
            "blacklist_list": {"stringValue": blacklist_str}
        }
    }
    r = requests.patch(url, json=payload, timeout=10)
    return r.status_code == 200

def main():
    print("Fetching current state from Firestore...")
    progress, blacklist_str, auto_groups, scraped_groups, cooldowns = fs_get_state()
    
    if not blacklist_str:
        print("Blacklist is empty or failed to load.")
        return
        
    blacklist_lines = [x.strip() for x in blacklist_str.splitlines() if x.strip()]
    print(f"Current Firestore blacklist count: {len(blacklist_lines)}")
    
    cleaned_lines = []
    removed_count = 0
    for line in blacklist_lines:
        if line.lower() in protected_groups:
            print(f"Removing target group from blacklist: {line}")
            removed_count += 1
        else:
            cleaned_lines.append(line)
            
    print(f"\nRemoved {removed_count} target groups. New count: {len(cleaned_lines)}")
    
    new_blacklist_str = "\n".join(cleaned_lines) + "\n"
    
    # Save back to Firestore
    if fs_set_blacklist(new_blacklist_str):
        print("Successfully updated Firestore blacklist!")
    else:
        print("Failed to update Firestore blacklist!")
        
    # Also clean local blacklist.txt
    if os.path.exists("blacklist.txt"):
        with open("blacklist.txt", "r", encoding="utf-8") as f:
            local_lines = f.readlines()
        
        local_cleaned = []
        for line in local_lines:
            val = line.strip()
            if val and val.lower() not in protected_groups:
                local_cleaned.append(val)
                
        with open("blacklist.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(local_cleaned) + "\n")
        print("Successfully cleaned local blacklist.txt!")

if __name__ == "__main__":
    main()
