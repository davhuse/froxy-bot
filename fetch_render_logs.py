import urllib.request
import json
import ssl
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def fetch_logs():
    context = ssl._create_unverified_context()
    url = "https://froxy-bot.onrender.com/api/logs"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            logs = data.get("logs", [])
            print("=" * 80)
            print("LATEST 40 LOG LINES FROM RENDER")
            print("=" * 80)
            for line in logs[-40:]:
                print(line.strip())
            print("=" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_logs()
