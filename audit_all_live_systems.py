import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "https://bot-service-production-9d74.up.railway.app/api/status"
try:
    r = requests.get(url, timeout=10)
    data = r.json()
    print("=== LIVE SYSTEM STATUS ===")
    print("Main status:", data.get("status"))
    print("Active ad account in queue:", data.get("blast_queue", {}).get("active_account"))
    
    print("\n--- AD ACCOUNTS ---")
    for acc, info in data.get("ad_accounts", {}).items():
        print(f"[{acc}]")
        print(f"  Phase: {info.get('phase')}")
        print(f"  Connected: {info.get('telegram_connected')}")
        print(f"  Authorized: {info.get('telegram_authorized')}")
        print(f"  Sent count: {info.get('sent_count')}")
        print(f"  Failed count: {info.get('failed_count')}")
        print(f"  Target groups: {info.get('target_groups')}")
        print(f"  Sendable groups: {info.get('sendable_groups')}")
        print(f"  Last error: {info.get('last_error')}")
        print(f"  Next blast: {info.get('next_blast_at')}")

    print("\n--- SALES BOTS ---")
    for bname, binfo in data.get("sales_bots", {}).items():
        print(f"[{bname}] (@{binfo.get('bot_username')})")
        print(f"  Status: {binfo.get('status')}")
        print(f"  Process running: {binfo.get('process_running')}")
        print(f"  Telegram ready: {binfo.get('telegram_ready')}")
        print(f"  Last connected: {binfo.get('last_connected_at')}")
except Exception as e:
    print("Status fetch error:", e)
