import requests
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://bot-service-production-9d74.up.railway.app"

print("=== 4. BLAST / AUTO-MESSAGE STATUS TEST ===")
r_status = requests.get(f"{BASE}/api/status")
try:
    data = r_status.json()
    for acc, info in data.get("accounts", {}).items():
        print(f"Account: {acc} | Phase: {info.get('phase')} | Sent: {info.get('sent_count')} | Next: {info.get('next_blast_at')} | Restrict: {info.get('account_restriction')} | Error: {info.get('error')}")
except Exception as e:
    print("Parse error:", e, r_status.text[:200])

print("\n=== 5. TELEGRAM BOT MENU BUTTON TEST ===")
TOKEN = "8940174381:AAE5M4yFbIZ8F5W8dsINCD3tQipHCYgOlzg"
r_btn = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChatMenuButton")
print("Menu Button API Response:", json.dumps(r_btn.json(), indent=2, ensure_ascii=False))
