import json
import urllib.request

bots = {
    "KeyVadi": "8712009642:AAE2jKKUwjhVpRC38dpFQkbSt2srjdUDuuc",
    "LisansArena": "8272543860:AAGESmDOiIXFoK7FYCh0UfP3IplBcvMhTEA",
    "Froxy": "8845484139:AAE7NeZdo4kSurKMNFctA08GhMQrbSQPvjg"
}

for name, token in bots.items():
    print(f"=== Checking {name} Bot ===")
    # 1. getMe
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url) as r:
            me_data = json.loads(r.read().decode('utf-8'))
            print(f"  getMe: {me_data.get('ok')}, username: @{me_data.get('result', {}).get('username')}")
    except Exception as e:
        print(f"  getMe error: {e}")

    # 2. getWebhookInfo
    try:
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        with urllib.request.urlopen(url) as r:
            wh_data = json.loads(r.read().decode('utf-8'))
            res = wh_data.get('result', {})
            print(f"  Webhook URL: '{res.get('url')}', Pending update count: {res.get('pending_update_count')}, Last error: {res.get('last_error_message')}")
    except Exception as e:
        print(f"  getWebhookInfo error: {e}")

    # 3. getUpdates check
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?limit=5"
        with urllib.request.urlopen(url) as r:
            up_data = json.loads(r.read().decode('utf-8'))
            print(f"  getUpdates ok: {up_data.get('ok')}, count: {len(up_data.get('result', []))}")
            for u in up_data.get('result', [])[:3]:
                msg = u.get('message', {})
                print(f"    Pending msg from {msg.get('from', {}).get('username') or msg.get('from', {}).get('id')}: '{msg.get('text')}'")
    except Exception as e:
        print(f"  getUpdates error: {e}")
    print()
