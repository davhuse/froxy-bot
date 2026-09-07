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
headers = {
    "X-Admin-Token": token,
    "User-Agent": "Mozilla/5.0"
}

# 1. Fetch group status
req = urllib.request.Request(f"{base}/api/group-status", headers=headers)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        gdata = json.loads(r.read().decode('utf-8'))
        print("=== KEYVADI GROUP STATUS ===")
        print("Total permanent blocks:", len(gdata.get("permanent", [])))
        print("Total temporary blocks:", len(gdata.get("temporary", [])))
        print("Total review blocks:", len(gdata.get("review", [])))

        # Find KeyVadi specific errors in failures
        kv_fails = [row for row in gdata.get("temporary", []) + gdata.get("review", []) + gdata.get("permanent", []) if row.get("account") == "KeyVadiOnline"]
        print(f"\nKeyVadi Failure records ({len(kv_fails)}):")
        for f in kv_fails:
            print(f" - {f.get('group')}: reason={f.get('reason')} err={f.get('error')} date={f.get('date')}")

        checkpoint = gdata.get("blast_checkpoint", {}).get("accounts", {}).get("KeyVadiOnline", {})
        print(f"\n=== KEYVADI BLAST CHECKPOINT ===")
        print("Status:", checkpoint.get("status"))
        print("Cursor:", checkpoint.get("cursor"))
        print("Due at:", checkpoint.get("due_at"))
        targets = checkpoint.get("targets", [])
        print(f"Targets in current/last blast ({len(targets)}):")
        accepted = []
        failed = []
        skipped = []
        for t in targets:
            state = t.get("state")
            grp = t.get("group")
            reason = t.get("reason")
            err = t.get("error")
            if state == "accepted":
                accepted.append(grp)
            elif state == "failed":
                failed.append((grp, reason, err))
            else:
                skipped.append((grp, state, reason))
        
        print(f"Accepted ({len(accepted)}):", ", ".join(accepted[:10]), "..." if len(accepted) > 10 else "")
        print(f"\nFailed ({len(failed)}):")
        for grp, reason, err in failed:
            print(f"  ❌ {grp} -> Reason: {reason} | Error: {err}")
        print(f"\nSkipped ({len(skipped)}):")
        for grp, state, reason in skipped:
            print(f"  ⏭️ {grp} -> State: {state} | Reason: {reason}")
except Exception as e:
    print("Error:", e)
