import time
import urllib.request
import json

RENDER_API_KEY = "rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE"
SERVICE_ID = "srv-d8ecii58nd3s73afm620"

def get_latest_deploy_status():
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
        print(f"Error: {e}")
    return None, None

print("Monitoring Render deploy status...")
while True:
    dep_id, status = get_latest_deploy_status()
    print(f"[{time.strftime('%H:%M:%S')}] Deploy ID: {dep_id} | Status: {status}")
    if status == "live":
        print("DEPOLYMENT IS LIVE!")
        break
    if status in ["build_failed", "update_failed", "deactivated"]:
        print("DEPLOYMENT FAILED!")
        break
    time.sleep(15)
