import urllib.request
import json
import time

url = "https://froxy-bot-kgky.onrender.com/api/status"

for i in range(5):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            print("Status:", r.status)
            print("Response:", r.read().decode('utf-8'))
            break
    except Exception as e:
        print(f"Attempt {i+1} failed:", e)
    time.sleep(5)
