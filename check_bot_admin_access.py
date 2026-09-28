import asyncio
from telethon import TelegramClient
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

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
vars_data = r.json().get('data', {}).get('variables', {})

api_id = int(vars_data['TELEGRAM_API_ID'])
api_hash = vars_data['TELEGRAM_API_HASH']

bots = [
    ("KeyVadiSatisBot", vars_data['KEYVADI_SUPPORT_BOT_TOKEN']),
    ("LisansArenaBot", vars_data['LISANSARENA_BOT_TOKEN']),
    ("FroxyDestekBOT", vars_data['FROXY_SUPPORT_BOT_TOKEN']),
    ("JarvisCraftsBot", vars_data['JARVIS_BOT_TOKEN']),
]

async def check():
    for name, token in bots:
        b = TelegramClient(f'temp_{name}', api_id, api_hash)
        await b.start(bot_token=token)
        try:
            # Check if user 7499698483 is accessible
            u = await b.get_input_entity(7499698483)
            print(f"[{name}] User 7499698483 is ACCESSIBLE (user has started the bot!)")
        except Exception as e:
            print(f"[{name}] User 7499698483 NOT accessible ({type(e).__name__})")
        await b.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
