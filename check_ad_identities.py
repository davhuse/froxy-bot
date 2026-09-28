import asyncio, requests
from telethon import TelegramClient
from telethon.sessions import StringSession

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

API_ID = int(vars.get('TELEGRAM_API_ID') or 26500645)
API_HASH = vars.get('TELEGRAM_API_HASH') or 'ca29cb773b400938f3869b2d8e484a0c'

async def check():
    for k in ['AD_STRING_SESSION_JARVIS', 'AD_STRING_SESSION_LISANSARENA', 'AD_STRING_SESSION_KEYVADI', 'AD_STRING_SESSION_FROXY']:
        s = vars.get(k)
        if s:
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    print(f'{k}: ID={me.id}, username=@{me.username}, name={me.first_name}')
                else:
                    print(f'{k}: not authorized')
                await c.disconnect()
            except Exception as e:
                print(f'{k}: error {e}')

asyncio.run(check())
