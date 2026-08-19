import urllib.request
import json
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def fetch_logs():
    url = "https://froxy-bot-qy0a.onrender.com/api/logs"
    try:
        req = urllib.request.Request(url)
        token = os.environ.get("PANEL_ADMIN_TOKEN", "").strip()
        if not token:
            raise RuntimeError("PANEL_ADMIN_TOKEN is required")
        req.add_header("X-Admin-Token", token)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            logs = data.get("logs", [])
            print("=" * 80)
            print(f"LATEST {len(logs)} LOG LINES FROM RENDER")
            print("=" * 80)
            for line in logs:
                print(line.strip())
            print("=" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_logs()
