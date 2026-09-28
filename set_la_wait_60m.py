import requests
import asyncio
import time
import sys
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = """
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
"""
r = requests.post(url, json={'query': q, 'variables': {
    'projId': '5fa77867-f818-4da3-b9d9-702529879e6f',
    'envId': '6ea40a3d-d7cc-4675-a593-29f6db038de1',
    'svcId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
}}, headers=headers)
vars = r.json().get('data', {}).get('variables', {})
session_str = vars.get('AD_STRING_SESSION_LISANSARENA', '')
API_ID = int(vars.get('TELEGRAM_API_ID') or 31076280)
API_HASH = vars.get('TELEGRAM_API_HASH') or '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    client_name = "LisansArenaOnline"
    now_utc = datetime.now(timezone.utc)
    due_utc = now_utc + timedelta(minutes=60)
    now_iso = now_utc.isoformat()
    due_iso = due_utc.isoformat()
    due_timestamp = due_utc.timestamp()

    print(f"Setting 60-minute wait for {client_name}...")
    print(f"Now: {now_iso}")
    print(f"Due: {due_iso} (timestamp: {due_timestamp})")

    # 1. Telegram 'me' Saved Messages
    if session_str:
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            await client.send_message('me', f"__BLAST_COMPLETED__{client_name}:{now_iso}")
            await client.send_message('me', f"__BLAST_DUE__{client_name}:{due_iso}")
            print("Telegram 'me' saved messages updated successfully!")
        else:
            print("Client is not authorized.")
        await client.disconnect()

    # 2. Firestore blast_checkpoint_v3
    try:
        import os
        os.environ['FIREBASE_API_KEY'] = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
        from firestore_helper import get_document, set_document
        doc = get_document("blast_checkpoint_v3") or {}
        accounts = doc.get("accounts", {})
        if client_name in accounts:
            accounts[client_name]["status"] = "waiting"
            accounts[client_name]["due_at"] = due_timestamp
            accounts[client_name]["pause_reason"] = "user_requested_60m_wait"
            doc["updated_at"] = now_iso
            set_document("blast_checkpoint_v3", doc)
            print("Firestore blast_checkpoint_v3 updated successfully!")
        else:
            print(f"Account {client_name} not in accounts: {list(accounts.keys())}")
    except Exception as e:
        print(f"Firestore update error: {e}")

asyncio.run(main())
