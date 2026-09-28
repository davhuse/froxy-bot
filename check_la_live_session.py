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

async def check():
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('LisansArena is NOT authorized!')
        return
    me = await client.get_me()
    print(f'Connected as: {me.first_name} (@{me.username}) ID={me.id} Phone=+{me.phone}')
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group or d.is_channel]
    print(f'Total dialogs: {len(dialogs)}, Total groups/channels: {len(groups)}')
    print('Sample 15 groups:')
    for g in groups[:15]:
        uname = getattr(g.entity, 'username', 'no_username')
        print(f'  - {g.name} (@{uname}) | ID: {g.id}')
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
