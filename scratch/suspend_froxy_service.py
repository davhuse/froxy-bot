import json
import urllib.request
import urllib.error

RENDER_API_KEY = "rnd_uSYeDJkX0xrcNfgo2BP7Tu3dRvuE"
SERVICE_ID = "srv-d8ecii58nd3s73afm620" # froxy-bot

url = f"https://api.render.com/v1/services/{SERVICE_ID}/suspend"

req = urllib.request.Request(url, method="POST")
req.add_header("Authorization", f"Bearer {RENDER_API_KEY}")
req.add_header("Accept", "application/json")
req.add_header("Content-Type", "application/json")

print(f"Suspending duplicate Render service: {SERVICE_ID}...")
try:
    with urllib.request.urlopen(req) as r:
        print("Success! Service suspended. Status code:", r.getcode())
except urllib.error.HTTPError as e:
    print(f"Failed with HTTP Error {e.code}: {e.reason}")
    try:
        print("Body:", e.read().decode("utf-8"))
    except:
        pass
except Exception as e:
    print("Other error:", e)
