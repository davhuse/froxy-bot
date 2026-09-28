import requests
import json

r = requests.get('https://bot-service-production-9d74.up.railway.app/api/status')
data = r.json()
accounts = data.get('ad_accounts', {})
queue = data.get('blast_queue', {}).get('accounts', {})

for name in sorted(accounts.keys()):
    acc = accounts[name]
    q = queue.get(name, {})
    print(f"[{name}]")
    print(f"  Phase: {acc.get('phase')} | Process: {acc.get('process_running')} | Auth: {acc.get('telegram_authorized')}")
    print(f"  Queue Status: {q.get('status')} | Due: {acc.get('next_blast_at')} | Kalan: {acc.get('remaining_minutes')} dk")
    print(f"  Sent: {acc.get('sent_count')} | Failed: {acc.get('failed_count')} | Current: {acc.get('current_index')}/{acc.get('total_groups')}")
    print()
