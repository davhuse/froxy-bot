import json
import os

# 1. Clean the bad groups from auto_groups.txt right now
AUTO_GROUPS_FILE = "auto_groups.txt"
bad_groups = {"kuponsatimalim", "alcaponesat", "auzefeticaretreklamsiz"}

if os.path.exists(AUTO_GROUPS_FILE):
    with open(AUTO_GROUPS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    cleaned_auto = [x for x in lines if x.lower() not in bad_groups]
    with open(AUTO_GROUPS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_auto) + "\n")
    print(f"Cleaned auto_groups.txt! Removed bad groups: {bad_groups}")

# 2. Add these bad groups to blacklist.txt so they are blacklisted and not joined again
BLACKLIST_FILE = "blacklist.txt"
if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        blacklist = set(line.strip().lower() for line in f if line.strip())
        
    added = 0
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        for bg in bad_groups:
            if bg.lower() not in blacklist:
                f.write(bg + "\n")
                added += 1
    print(f"Added {added} bad groups to blacklist.txt")
