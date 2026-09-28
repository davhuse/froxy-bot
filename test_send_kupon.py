import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

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

async def try_test_send():
    for name in ['KEYVADI', 'JARVIS']:
        s_str = vars.get(f'AD_STRING_SESSION_{name}')
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        me = await client.get_me()
        print(f"\n--- Testing send for {name} ({me.first_name}, @{me.username}) ---")
        try:
            entity = await client.get_entity('kuponhesapsatis')
            # Dry check or send a quick harmless dot and delete
            msg = await client.send_message(entity, ".")
            print(f"SUCCESS: Message sent! (ID: {msg.id})")
            await client.delete_messages(entity, msg.id)
            print("Message deleted successfully.")
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
        finally:
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(try_test_send())
