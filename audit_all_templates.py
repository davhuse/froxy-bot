import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = glob.glob("messages/*.txt")
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE
)

print(f"Auditing {len(files)} template files in messages/ ...\n")
total_issues = 0

for fpath in sorted(files):
    fname = os.path.basename(fpath)
    try:
        content = open(fpath, "r", encoding="utf-8").read()
    except Exception as e:
        print(f"[ERROR] {fname}: cannot read: {e}")
        total_issues += 1
        continue

    issues = []
    # 1. Emoji check
    emojis_found = emoji_pattern.findall(content)
    if emojis_found:
        issues.append(f"EMOJI_FOUND: {emojis_found[:5]}")

    # 2. Shopier link check
    if "shopier" in content.lower():
        issues.append("SHOPIER_LINK_FOUND")

    # 3. Check for invalid @ mentions or multiple bots
    bots = re.findall(r"@\w+Bot", content, re.IGNORECASE)
    unique_bots = set(b.lower() for b in bots)
    if len(unique_bots) > 1:
        issues.append(f"MULTIPLE_BOTS_FOUND: {unique_bots}")

    if issues:
        print(f"[FAIL] {fname}: {', '.join(issues)}")
        total_issues += 1
    else:
        # print first line
        first_line = content.splitlines()[0] if content.splitlines() else "(empty)"
        # print(f"[OK] {fname}: {first_line[:40]}")

print(f"\nAudit complete: {len(files) - total_issues}/{len(files)} OK, {total_issues} issues found.")
