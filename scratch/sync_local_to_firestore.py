import os
import requests

API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def fs_set_state(progress=None, blacklist=None, auto_groups=None, scraped_groups=None, cooldowns=None):
    url = f"{BASE_URL}/reklam/state?key={API_KEY}"
    
    fields = {}
    mask_parts = []
    
    if progress is not None:
        fields["progress_list"] = {"stringValue": progress}
        mask_parts.append("updateMask.fieldPaths=progress_list")
    if blacklist is not None:
        fields["blacklist_list"] = {"stringValue": blacklist}
        mask_parts.append("updateMask.fieldPaths=blacklist_list")
    if auto_groups is not None:
        fields["auto_groups_list"] = {"stringValue": auto_groups}
        mask_parts.append("updateMask.fieldPaths=auto_groups_list")
    if scraped_groups is not None:
        fields["scraped_groups_list"] = {"stringValue": scraped_groups}
        mask_parts.append("updateMask.fieldPaths=scraped_groups_list")
    if cooldowns is not None:
        fields["cooldowns_list"] = {"stringValue": cooldowns}
        mask_parts.append("updateMask.fieldPaths=cooldowns_list")
        
    if not mask_parts:
        return False
        
    url += "&" + "&".join(mask_parts)
    payload = {"fields": fields}
    
    r = requests.patch(url, json=payload, timeout=10)
    return r.status_code == 200

def main():
    print("Syncing local auto_groups.txt and blacklist.txt to Firestore...")
    
    blacklist_content = ""
    if os.path.exists("blacklist.txt"):
        with open("blacklist.txt", "r", encoding="utf-8") as f:
            blacklist_content = f.read()
            
    auto_groups_content = ""
    if os.path.exists("auto_groups.txt"):
        with open("auto_groups.txt", "r", encoding="utf-8") as f:
            auto_groups_content = f.read()
            
    if fs_set_state(blacklist=blacklist_content, auto_groups=auto_groups_content):
        print("SUCCESSFULLY synced local state to Firestore!")
    else:
        print("FAILED to sync state to Firestore!")

if __name__ == "__main__":
    main()
