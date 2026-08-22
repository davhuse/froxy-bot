import urllib.request
import re
from datetime import datetime, timezone

def inspect_web_group(username):
    url = f"https://t.me/{username}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            html = r.read().decode('utf-8', errors='ignore')
            
            title_m = re.search(r'<div class="tgme_page_title"[^>]*><span[^>]*>(.*?)</span>', html, re.DOTALL)
            extra_m = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.DOTALL)
            desc_m = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', html, re.DOTALL)
            
            title = title_m.group(1).strip() if title_m else ""
            extra = extra_m.group(1).strip() if extra_m else ""
            desc = desc_m.group(1).strip() if desc_m else ""
            
            # Extract members
            mem_m = re.search(r'([0-9\s]+)\s*members', extra, re.IGNORECASE) or re.search(r'([0-9\s]+)\s*üye', extra, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            # Check if it's a group (has members + online, or group actions)
            is_group = "online" in extra.lower() or "members" in extra.lower() or "üye" in extra.lower()
            
            print(f"User: @{username} | Title: {title} | Extra: {extra} | Members: {members} | IsGroup: {is_group}")
            return {
                "username": username,
                "title": title,
                "members": members,
                "extra": extra,
                "desc": desc,
                "is_group": is_group
            }
    except Exception as e:
        print(f"Error {username}: {e}")
        return None

if __name__ == "__main__":
    for u in ["me7alimsatim", "kuponsat", "alimsatimmerkezii", "letgoilanlari"]:
        inspect_web_group(u)
