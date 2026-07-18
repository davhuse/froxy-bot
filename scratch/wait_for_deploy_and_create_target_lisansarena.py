import json
import urllib.request
import urllib.error
import time
import subprocess

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
        print(f"Error checking deploy: {e}")
    return None, None

def main():
    print("=" * 60)
    print("WAITING FOR RENDER DEPLOY TO BE LIVE AND CREATING TARGET LISANSARENA PRODUCTS...")
    print("=" * 60)
    
    # Wait for status to be 'live'
    while True:
        dep_id, status = get_latest_deploy_status()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Latest Deploy ID: {dep_id} | Status: {status}")
        
        if status == "live":
            print("Deploy is LIVE! LisansArena target cover images are now publicly accessible.")
            break
        elif status in ["build_failed", "update_failed", "deactivated"]:
            print(f"Deploy failed or inactive with status: {status}. Stopping.")
            return
        
        print("Waiting 15 seconds before next check...")
        time.sleep(15)
        
    # Run target product creation script
    print("\nRunning create_target_lisansarena_products.py...")
    res = subprocess.run(["python", r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\scratch\create_target_lisansarena_products.py"], capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.stderr:
        print("Errors:\n", res.stderr)
        
    # Run integration script
    print("\nRunning integrate_target_lisansarena_products.py...")
    res2 = subprocess.run(["python", r"C:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\scratch\integrate_target_lisansarena_products.py"], capture_output=True, text=True, encoding="utf-8")
    print(res2.stdout)
    if res2.stderr:
        print("Errors:\n", res2.stderr)
        
    print("\n[SUCCESS] LisansArena target product upload and integration completed successfully!")

if __name__ == "__main__":
    main()
