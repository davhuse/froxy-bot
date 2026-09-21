import json
import urllib.request
import asyncio
import sys
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient
from telethon.sessions import StringSession

with open('extracted_all_render_envs.json', 'r', encoding='utf-8') as f:
    envs = json.load(f)

print("=== CHECKING TELEGRAM BOT TOKENS ===")
bot_tokens = set()
for label, data in envs.items():
    for k, v in data.items():
        if 'BOT_TOKEN' in k and v and not v.startswith('YOUR_'):
            bot_tokens.add((k, v, label))

print(f"Found {len(bot_tokens)} unique bot token references:")
unique_tokens = {}
for k, v, label in bot_tokens:
    unique_tokens.setdefault(v, []).append(f"{label}:{k}")

for token, origins in unique_tokens.items():
    # Test token with api.telegram.org/bot<token>/getMe
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getMe")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get('ok'):
                u = data['result']
                print(f"✅ Bot Token: @{u.get('username')} (ID: {u.get('id')}) -> Origins: {origins}")
            else:
                print(f"❌ Bot Token invalid: {data} -> Origins: {origins}")
    except Exception as e:
        print(f"❌ Bot Token error ({e}): {token[:15]}... -> Origins: {origins}")

print("\n=== CHECKING TELEGRAM STRING SESSIONS ===")
sessions = set()
for label, data in envs.items():
    for k, v in data.items():
        if 'STRING_SESSION' in k and v:
            sessions.add((k, v, label))

unique_sessions = {}
for k, v, label in sessions:
    unique_sessions.setdefault(v, []).append(f"{label}:{k}")

# We will test sessions in an async function
api_id = 31076280
api_hash = "7ba4072dcf65651e06fae968ec99b6d8"

async def test_sessions():
    for s_str, origins in unique_sessions.items():
        masked = s_str[:12] + "..." + s_str[-6:]
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"✅ Session ALIVE: @{me.username} (Name: {me.first_name}, ID: {me.id}, Phone: {me.phone}) -> Origins: {origins}")
            else:
                print(f"❌ Session UNAUTHORIZED / REVOKED: {masked} -> Origins: {origins}")
        except Exception as e:
            print(f"❌ Session ERROR ({e}): {masked} -> Origins: {origins}")
        finally:
            await client.disconnect()

asyncio.run(test_sessions())

print("\n=== CHECKING SHOPIER TOKENS ===")
shopier_tokens = set()
for label, data in envs.items():
    for k, v in data.items():
        if 'SHOPIER' in k and 'ACCESS_TOKEN' in k and v:
            shopier_tokens.add((k, v, label))

unique_shopier = {}
for k, v, label in shopier_tokens:
    unique_shopier.setdefault(v, []).append(f"{label}:{k}")

for tok, origins in unique_shopier.items():
    # Test Shopier token
    req = urllib.request.Request("https://api.shopier.com/v1/products?limit=1", headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"✅ Shopier HTTP {resp.status} SUCCESS! -> Origins: {origins}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:150]
        print(f"❌ Shopier HTTP {e.code} ({e.reason}): {body} -> Origins: {origins}")
    except Exception as e:
        print(f"❌ Shopier Error: {e} -> Origins: {origins}")
