import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://bot-service-production-9d74.up.railway.app"

print("==================================================")
print("       CANLI SISTEM FULL KONTROL VE TEST          ")
print("==================================================")

# 1. API STATUS
print("\n--- 1. API Status & Hesaplar (/api/status) ---")
try:
    r = requests.get(f"{BASE}/api/status", timeout=10)
    data = r.json()
    print("API Status HTTP:", r.status_code)
    
    print("\n[Ad Accounts]")
    ad_acc = data.get("ad_accounts", {})
    for name, info in ad_acc.items():
        print(f"  • {name}: phase={info.get('phase')}, sent={info.get('sent_count')}, target_groups={info.get('target_groups')}, connected={info.get('telegram_connected')}, auth={info.get('telegram_authorized')}")

    print("\n[Sales & Support Bots]")
    bots = data.get("sales_bots", {})
    for name, info in bots.items():
        print(f"  • {name} (@{info.get('bot_username')}): status={info.get('status')}, state={info.get('state')}, telegram_ready={info.get('telegram_ready')}")

except Exception as e:
    print("API Status Error:", e)

# 2. WEB ENDPOINTS
print("\n--- 2. Web & Mini App Endpoints ---")
endpoints = [
    ("/keyvadi/", "KeyVadi Mini App"),
    ("/la/app/", "LisansArena Mini App"),
    ("/froxy/", "Froxy Mini App"),
    ("/jarvis/app", "Jarvis Mini App"),
    ("/static/jarvis_demo_video.mp4", "Jarvis Video Demo"),
    ("/static/JARVIS_MUSTERI_DEMO_PAKETI.zip", "Jarvis PC Demo Zip")
]

for path, label in endpoints:
    try:
        if path.startswith("/static/"):
            r = requests.head(f"{BASE}{path}", timeout=10)
            print(f"  • {label} ({path}): HTTP {r.status_code} [size={r.headers.get('content-length')} bytes]")
        else:
            r = requests.get(f"{BASE}{path}", timeout=10)
            has_x_frame = "x-frame-options" in r.headers
            print(f"  • {label} ({path}): HTTP {r.status_code} [x-frame-options: {r.headers.get('x-frame-options', 'NONE - OK')}]")
    except Exception as e:
        print(f"  • {label} Error: {e}")

# 3. TELEGRAM BOT MENU BUTTONS
print("\n--- 3. Telegram Bot Menu Buttons (getChatMenuButton) ---")
from check_sessions import vars
bot_tokens = {
    'KeyVadiSatisBot': vars.get('KEYVADI_SUPPORT_BOT_TOKEN'),
    'LisansArenaBot': vars.get('LISANSARENA_BOT_TOKEN') or vars.get('LISANSARENA_SUPPORT_BOT_TOKEN'),
    'FroxyDestekBOT': vars.get('FROXY_SUPPORT_BOT_TOKEN') or vars.get('FROXY_BOT_TOKEN'),
    'JarvisCraftsBot': vars.get('JARVIS_BOT_TOKEN') or vars.get('BOT_TOKEN')
}

for name, tok in bot_tokens.items():
    if tok:
        try:
            res = requests.get(f"https://api.telegram.org/bot{tok}/getChatMenuButton", timeout=10).json()
            mb = res.get('result', {})
            print(f"  • {name}: type={mb.get('type')}, text='{mb.get('text')}', url='{mb.get('web_app', {}).get('url')}'")
        except Exception as e:
            print(f"  • {name} Error: {e}")
