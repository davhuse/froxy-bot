import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/status"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        
        # print specific parts of the JSON
        ad_acc = data.get("ad_accounts", {})
        kv = ad_acc.get("KeyVadiOnline", {})
        print(f"KeyVadi Phase: {kv.get('phase')}, Process Running: {kv.get('process_running')}, target_groups: {kv.get('target_groups')}")
        
        print("Bot Runtime Enabled:", data.get("bot_runtime_enabled"))
        print("AD Runtime Enabled:", data.get("ad_runtime_enabled"))
        print("Status:", data.get("status"))
        print("Blast Queue:", data.get("blast_queue"))
except Exception as e:
    print("Error:", e)
