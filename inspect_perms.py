import asyncio
import requests
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
        if not s_str:
            continue
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        me = await client.get_me()
        print(f"\n==========================================")
        print(f"ACCOUNT: {name} | Name: {me.first_name} | Phone: {me.phone} | ID: {me.id}")
        entity = await client.get_entity('kuponhesapsatis')
        perms = await client.get_permissions(entity, 'me')
        for prop in ['is_admin', 'is_creator', 'has_left', 'is_banned', 'send_messages', 'send_media', 'send_stickers', 'send_gifs', 'embed_link_previews']:
            val = getattr(perms, prop, 'N/A')
            print(f"  {prop}: {val}")
        
        # Check what SpamBot says in detail (date until restricted)
        spambot = await client.get_entity('SpamBot')
        msgs = await client.get_messages(spambot, limit=3)
        print("  SpamBot full response:")
        for m in msgs:
            if m.sender_id != me.id:
                print(f"    {m.text}")
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(inspect())
