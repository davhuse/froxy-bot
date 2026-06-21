import os
import json
import requests

API_KEY    = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# Static target groups
gruplar = [
    "ticaretforumofficial",
    "sultanbeyliikinciel0",
    "tahaaslan11",
    "casinox_grup",
    "ReklamOnliene",
    "alimsatimmerkezii",
    "illegalalimsatimerkezi",
    "ilanticaret",
    "reklamreferans",
    "sosyalmedyaalimsatimticaret",
    "ReferansReklamYardimlasma",
    "sanalalimsatimticaret",
    "kuponsatisgrup",
    "referansreklam1",
    "referanslinkpaylasimigrup",
    "kuponsatislari0",
    "YuceKuponSatis",
    "letgoilanlari",
    "-1001572316417",
    "-3608209943",
    "ticar4t",
    "kuponhesapsatis",
    "reklamvereferanss",
    "kuponvekodsatisgrubu",
    "indirimkodusatis",
]

def get_list(dosya):
    if os.path.exists(dosya):
        with open(dosya, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f if line.strip())
    return set()

def fs_set_blacklist(blacklist_content):
    try:
        url = f"{BASE_URL}/reklam/state?updateMask.fieldPaths=blacklist_list&key={API_KEY}"
        fields = {
            "blacklist_list": {"stringValue": blacklist_content}
        }
        r = requests.patch(url, json={"fields": fields}, timeout=10)
        print(f"Firestore update response: {r.status_code}")
    except Exception as e:
        print(f"Firestore update error: {e}")

def main():
    # Load auto groups
    auto_groups = get_list("auto_groups.txt")
    
    # Target groups to protect
    protected = set(g.lower() for g in gruplar)
    protected.update(auto_groups)
    
    print(f"Protected groups ({len(protected)}): {protected}")
    
    # Load current local blacklist
    local_black = get_list("blacklist.txt")
    print(f"Current blacklist size: {len(local_black)}")
    
    # Filter out protected groups
    cleaned_black = []
    removed = []
    
    if os.path.exists("blacklist.txt"):
        with open("blacklist.txt", "r", encoding="utf-8") as f:
            for line in f:
                g = line.strip()
                if not g:
                    continue
                if g.lower() in protected:
                    removed.append(g)
                else:
                    cleaned_black.append(g)
                    
    print(f"Removing from blacklist: {removed}")
    print(f"New blacklist size: {len(cleaned_black)}")
    
    # Write back locally
    with open("blacklist.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_black) + "\n")
    print("Local blacklist.txt updated.")
    
    # Update Firestore
    blacklist_content = "\n".join(cleaned_black) + "\n"
    fs_set_blacklist(blacklist_content)
    print("Firestore blacklist synchronized.")

if __name__ == '__main__':
    main()
