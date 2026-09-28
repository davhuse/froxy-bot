import requests
import asyncio
import sys
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

async def find_candidates():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    dialogs = await client.get_dialogs()
    candidates = []
    for d in dialogs:
        if d.is_group or d.is_channel:
            uname = getattr(d.entity, 'username', None)
            if uname:
                r = getattr(d.entity, 'default_banned_rights', None)
                send_msg = getattr(r, 'send_messages', False) if r else False
                if not send_msg:
                    candidates.append((d.name, uname, d.id))
    print(f'Found {len(candidates)} candidate groups with usernames.')
    for c in candidates[:15]:
        print(f'  {c[0]} (@{c[1]}) ID={c[2]}')
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(find_candidates())
