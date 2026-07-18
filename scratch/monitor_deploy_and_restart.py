import urllib.request
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

RENDER_API_KEY = "rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE"
SERVICE_ID = "srv-d8ecii58nd3s73afm620"

def get_latest_deploy():
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys?limit=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {RENDER_API_KEY}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read().decode("utf-8"))
            if res and isinstance(res, list):
                dep = res[0].get("deploy", {})
                return dep.get("id"), dep.get("status")
    except Exception as e:
        print(f"Error fetching deploy: {e}")
    return None, None

print("Monitoring Render deploy status...")
while True:
    dep_id, status = get_latest_deploy()
    print(f"[{time.strftime('%H:%M:%S')}] Deploy ID: {dep_id} | Status: {status}")
    if status == "live":
        print("\nDEPOLYMENT IS LIVE! The bot has restarted with the blacklist safety fix.")
        break
    if status in ["build_failed", "update_failed", "deactivated"]:
        print(f"\nDeployment failed: {status}")
        break
    time.sleep(15)
