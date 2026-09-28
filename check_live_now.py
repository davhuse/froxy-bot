import urllib.request
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()

BASE = 'https://bot-service-production-9d74.up.railway.app'
ADMIN_TOKEN = 'VOJVbVkVHQBw5J3zI8vQeW2zP5iK6uY9'
headers = {'X-Admin-Token': ADMIN_TOKEN}

def get_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))

print("=== 1. STATUS & ACCOUNTS ===")
status_data = get_json(f"{BASE}/api/status")
print(f"Overall status: {status_data.get('status')}")
print(f"Bot runtime enabled: {status_data.get('bot_runtime_enabled')}")
print(f"Ad runtime enabled: {status_data.get('ad_runtime_enabled')}")

print("\n--- Ad Accounts ---")
for name, acc in status_data.get('ad_accounts', {}).items():
    print(f"[{name}]")
    print(f"  Phase: {acc.get('phase')}")
    print(f"  Connected: {acc.get('telegram_connected')}, Authorized: {acc.get('telegram_authorized')}")
    print(f"  Sent: {acc.get('sent_count')}, Failed: {acc.get('failed_count')}, Total: {acc.get('total_groups')}")
    print(f"  Current group: {acc.get('current_group')}, Index: {acc.get('current_index')}")
    print(f"  Current template: {acc.get('current_template')}")
    print(f"  Last accepted at: {acc.get('last_accepted_at')}")
    print(f"  Last error: {acc.get('last_error')}")

print("\n--- Sales / Support Bots ---")
for brand, bot in status_data.get('sales_bots', {}).items():
    print(f"[{brand}] @{bot.get('bot_username')} - State: {bot.get('state')}, Telegram Ready: {bot.get('telegram_ready')}, Last error: {bot.get('last_error')}")

print("\n=== 2. BLAST QUEUE ===")
queue = status_data.get('blast_queue', {})
print(f"Active account: {queue.get('active_account')}")
for name, q in queue.get('accounts', {}).items():
    print(f"[{name}] status={q.get('status')} sent={q.get('sent_count')} failed={q.get('failed_count')} pending={q.get('pending_count')} current_index={q.get('current_index')}")

print("\n=== 3. RECENT AD LOGS ===")
try:
    logs_data = get_json(f"{BASE}/api/logs")
    logs = logs_data.get('logs', [])
    print(f"Total log lines: {len(logs)}")
    for line in logs[-20:]:
        print(" ", line.strip())
except Exception as e:
    print(f"Logs error: {e}")
