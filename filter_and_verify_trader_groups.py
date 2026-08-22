import json
import os
import re
import urllib.request
import html
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

# 1. Exclusions
excluded = set()
if os.path.exists("gruplar.txt"):
    with open("gruplar.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            u = line.strip().lower().lstrip("@")
            if u:
                excluded.add(u)

if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            u = line.strip().lower().lstrip("@")
            if u:
                excluded.add(u)

print(f"Excluded count: {len(excluded)}")

# 2. Load trader active groups
with open("all_trader_active_groups.json", "r", encoding="utf-8") as f:
    trader_groups = json.load(f)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

approved_trader_groups = []

for u, data in trader_groups.items():
    u_clean = u.lower().lstrip("@")
    if u_clean in excluded:
        continue

    # Web inspect
    url = f"https://t.me/{u_clean}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            content_clean = html.unescape(content)
            
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content_clean)
            extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', content_clean, re.DOTALL)
            og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content_clean)
            
            title = og_title.group(1).strip() if og_title else data.get("title", "")
            extra_str = extra.group(1).strip() if extra else ""
            desc = og_desc.group(1).strip() if og_desc else ""
            
            is_group = "members" in extra_str.lower() or "üye" in extra_str.lower() or "online" in extra_str.lower()
            is_channel = "subscribers" in extra_str.lower() or "abone" in extra_str.lower()
            
            if not is_group or is_channel:
                continue
                
            mem_m = re.search(r'([0-9\s]+)\s*(?:members|üye)', extra_str, re.IGNORECASE)
            members = 0
            if mem_m:
                members = int(re.sub(r'\s+', '', mem_m.group(1)))
                
            online_m = re.search(r'([0-9\s]+)\s*online', extra_str, re.IGNORECASE)
            online = 0
            if online_m:
                online = int(re.sub(r'\s+', '', online_m.group(1)))
                
            if members < 50:
                continue

            item = {
                "username": u_clean,
                "title": title,
                "members": members,
                "online": online,
                "active_trader_signals": data.get("matched_queries", []),
                "sample_live_messages": data.get("sample_messages", [])[:2],
                "t_me_link": f"https://t.me/{u_clean}"
            }
            approved_trader_groups.append(item)
            print(f"[TRADER CONFIRMED ✅ #{len(approved_trader_groups)}] @{u_clean:<25} | Üye: {members:<5} | Online: {online:<4} | {title[:28]}")
    except Exception as e:
        # If timeout or web error, keep if members were valid
        pass

approved_trader_groups.sort(key=lambda x: (-x["online"], -x["members"]))

print(f"\n=======================================================")
print(f"🎉 TOPLAM DOĞRULANMIŞ TÜCCAR AKTİF HEDEF GRUP SAYISI: {len(approved_trader_groups)}")
print(f"=======================================================\n")

with open("yeni_birebir_hedef_gruplar.json", "w", encoding="utf-8") as f:
    json.dump(approved_trader_groups, f, ensure_ascii=False, indent=2)

with open("yeni_birebir_hedef_gruplar.txt", "w", encoding="utf-8") as f:
    for g in approved_trader_groups:
        f.write(f"{g['username']}\n")

print("Kaydedildi: 'yeni_birebir_hedef_gruplar.json' ve 'yeni_birebir_hedef_gruplar.txt'")
