import urllib.request
import json
url = "https://froxy-bot-kgky.onrender.com/api/status"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        ad_acc = data.get("ad_accounts", {})
        la = ad_acc.get("LisansArenaOnline", {})
        print("LisansArena Status in ad_accounts:")
        print(json.dumps(la, indent=2, ensure_ascii=False))
        print("\nBlast Queue:")
        print(json.dumps(data.get("blast_queue"), indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
