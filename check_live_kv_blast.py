import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://froxy-bot-kgky.onrender.com"
token = "VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9"

# 1. Public status
try:
    req = urllib.request.Request(f"{base}/status")
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read().decode('utf-8'))
        print("=== LIVE PUBLIC STATUS ===")
        print("Ad accounts:", json.dumps(data.get("ad_accounts", {}), indent=2, ensure_ascii=False))
        print("Ad queue:", json.dumps(data.get("ad_queue", {}), indent=2, ensure_ascii=False))
except Exception as e:
    print("Public status error:", e)

# 2. Token-protected group-status
try:
    req2 = urllib.request.Request(
        f"{base}/api/group-status",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r:
        gdata = json.loads(r.read().decode('utf-8'))
        print("\n=== LIVE GROUP STATUS (PROTECTED) ===")
        kv_groups = gdata.get("accounts", {}).get("KeyVadiOnline", {})
        print("KeyVadi Group States count:", len(kv_groups.get("group_states", {})))
        print("KeyVadi summary:", {k: v for k, v in kv_groups.items() if k != "group_states"})
except Exception as e:
    print("Group status error:", e)
