import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantsBots

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

async def check():
    client = TelegramClient(StringSession(vars['AD_STRING_SESSION_FROXY']), api_id, api_hash)
    await client.connect()
    entity = await client.get_entity('kuponhesapsatis')
    
    print("=== ADMINS ===")
    try:
        admins = await client.get_participants(entity, filter=ChannelParticipantsAdmins())
        for a in admins:
            print(f"  Admin: {a.first_name} (@{a.username}) - ID: {a.id} - Bot: {a.bot}")
    except Exception as e:
        print(f"  Error fetching admins: {e}")

    print("=== BOTS IN GROUP ===")
    try:
        bots = await client.get_participants(entity, filter=ChannelParticipantsBots())
        for b in bots:
            print(f"  Bot: {b.first_name} (@{b.username}) - ID: {b.id}")
    except Exception as e:
        print(f"  Error fetching bots: {e}")

    p = await client.get_permissions(entity, 'me')
    print("=== PERMS FOR ME ===")
    for k in dir(p):
        if not k.startswith('_'):
            try:
                print(f"  {k}: {getattr(p, k)}")
            except Exception as e:
                print(f"  {k}: error {e}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
