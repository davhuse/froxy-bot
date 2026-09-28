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

sessions = {
    'KEYVADI': vars.get('AD_STRING_SESSION_KEYVADI'),
    'LISANSARENA': vars.get('AD_STRING_SESSION_LISANSARENA'),
    'FROXY': vars.get('AD_STRING_SESSION_FROXY'),
    'JARVIS': vars.get('AD_STRING_SESSION_JARVIS'),
}

async def inspect():
    for name, s_str in sessions.items():
        if not s_str: continue
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        me = await client.get_me()
        try:
            entity = await client.get_entity('kuponhesapsatis')
            p = await client(GetParticipantRequest(entity, 'me'))
            print(f"[{name}] {me.first_name} (@{me.username}) ID: {me.id}:")
            print(f"  Participant: {type(p.participant).__name__}")
            if hasattr(p.participant, 'banned_rights') and p.participant.banned_rights:
                print(f"  banned_rights: {p.participant.banned_rights}")
            else:
                print(f"  No individual banned_rights on user.")
        except Exception as e:
            print(f"[{name}] Error: {e}")
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(inspect())
