import urllib.request
import json
import ssl
import time

ctx = ssl._create_unverified_context()
url = "https://api.render.com/v1/services/srv-d99tvf8k1i2s73eq3q7g/deploys?limit=1"
req = urllib.request.Request(url)
req.add_header("Authorization", "Bearer rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE")
req.add_header("Accept", "application/json")

print("Waiting for deployment to complete...")
start_time = time.time()
while time.time() - start_time < 300: # 5 minutes max
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data:
                deploy = data[0].get("deploy", data[0])
                status = deploy.get("status")
                commit_msg = deploy.get("commit", {}).get("message", "N/A")
                print(f"[{time.strftime('%H:%M:%S')}] Status: {status} | Commit: {commit_msg}")
                if status == "live":
                    print("\n🎉 Deployment is LIVE!")
                    break
                elif status in ["failed", "canceled"]:
                    print(f"\n❌ Deployment failed or was canceled! Status: {status}")
                    break
    except Exception as e:
        print("Error checking status:", e)
    time.sleep(20)
else:
    print("Timeout waiting for deployment.")
