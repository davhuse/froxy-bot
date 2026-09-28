import requests
import json
import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'cb8db854-3ede-42e7-af5a-8d896d8c7cb2'
url = 'https://backboard.railway.app/graphql/v2'
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
q = '''
query GetVars($projId: String!, $envId: String!, $svcId: String!) {
  variables(projectId: $projId, environmentId: $envId, serviceId: $svcId)
}
'''
r = requests.post(url, json={'query': q, 'variables': {
    'projId': '5fa77867-f818-4da3-b9d9-702529879e6f',
    'envId': '6ea40a3d-d7cc-4675-a593-29f6db038de1',
    'svcId': '2cc6c23b-25e3-4d37-9cf0-8db3575eca1f'
}}, headers=headers)
vars_data = r.json().get('data', {}).get('variables', {})

api_id = int(vars_data.get('TELEGRAM_API_ID', 31076280))
api_hash = vars_data.get('TELEGRAM_API_HASH', '7ba4072dcf0a05a7ccf80e570866b6d8')

accounts = [
    ('Froxy', vars_data.get('AD_STRING_SESSION_FROXY')),
    ('KeyVadi', vars_data.get('AD_STRING_SESSION_KEYVADI')),
    ('LisansArena', vars_data.get('AD_STRING_SESSION_LISANSARENA')),
    ('Jarvis', vars_data.get('AD_STRING_SESSION_JARVIS')),
]

async def check_account(name, session_str):
    print(f"\n=================== Checking {name} ===================")
    if not session_str:
        print(f"ERROR: No session string for {name}!")
        return
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"FAILED: Session for {name} is NOT authorized!")
            return
        me = await client.get_me()
        print(f"User: {me.first_name} (@{me.username}) ID={me.id} Phone=+{me.phone}")
        
        # Check SpamBot
        try:
            async with client.conversation("@SpamBot", timeout=8) as conv:
                await conv.send_message("/start")
                resp = await conv.get_response()
                clean_reply = resp.raw_text.replace('\n', ' ')
                print(f"SpamBot reply: {clean_reply[:140]}")
        except Exception as e:
            print(f"SpamBot error: {e}")
            
    except Exception as exc:
        print(f"Connection error: {exc}")
    finally:
        if client.is_connected():
            await client.disconnect()

async def main():
    for name, s_str in accounts:
        await check_account(name, s_str)

if __name__ == "__main__":
    asyncio.run(main())
