import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest

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

api_id = int(vars['TELEGRAM_API_ID'])
api_hash = vars['TELEGRAM_API_HASH']

async def check_keyvadi():
    client = TelegramClient(StringSession(vars['AD_STRING_SESSION_KEYVADI']), api_id, api_hash)
    await client.connect()
    entity = await client.get_entity('kuponhesapsatis')
    
    try:
        p = await client(GetParticipantRequest(entity, 'me'))
        print(f"KeyVadi participant type: {type(p.participant).__name__}")
        print(f"KeyVadi participant: {p.participant}")
    except Exception as e:
        print(f"KeyVadi GetParticipant error: {e}")

    # Check if KeyVadi has slowmode wait
    try:
        from telethon.tl.functions.channels import GetFullChannelRequest
        full = await client(GetFullChannelRequest(entity))
        print(f"Slowmode next send date for KeyVadi: {full.full_chat.slowmode_next_send_date}")
    except Exception as e:
        print(f"FullChannel error: {e}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check_keyvadi())
