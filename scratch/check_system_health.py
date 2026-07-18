import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://froxy-bot.onrender.com/api"

def check_endpoint(endpoint):
    url = f"{base_url}/{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            print(f"\n=== Endpoint: {endpoint} ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
    except Exception as e:
        print(f"Error checking {endpoint}: {e}")
        return None

print("Starting Comprehensive System Check-Up on Render...")
status_data = check_endpoint("status")
stats_data = check_endpoint("stats")

# Check if support bots are running (check app.py list of bots status)
# In app.py:
# froxy_bot.py status, lisansarena_bot.py status, otomatik_katil.py status
# Let's inspect the process names in app.py's status JSON response
