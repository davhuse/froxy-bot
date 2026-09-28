import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

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
vars = r.json().get('data', {}).get('variables', {})

api_id = int(vars['TELEGRAM_API_ID'])
api_hash = vars['TELEGRAM_API_HASH']

sessions = {
    'KEYVADI': vars.get('AD_STRING_SESSION_KEYVADI'),
    'LISANSARENA': vars.get('AD_STRING_SESSION_LISANSARENA'),
    'FROXY': vars.get('AD_STRING_SESSION_FROXY'),
    'JARVIS': vars.get('AD_STRING_SESSION_JARVIS'),
}

async def test_spambot_and_group():
    for name, s_str in sessions.items():
        if not s_str:
            continue
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        me = await client.get_me()
        print(f"\n==========================================")
        print(f"ACCOUNT: {name} | Name: {me.first_name} | Phone: {me.phone} | ID: {me.id}")
        
        # 1. Check SpamBot status
        try:
            spambot = await client.get_entity('SpamBot')
            await client.send_message(spambot, '/start')
            await asyncio.sleep(2)
            msgs = await client.get_messages(spambot, limit=1)
            if msgs:
                txt = msgs[0].text.replace('\n', ' ')
                print(f"  SpamBot: {txt[:120]}")
        except Exception as se:
            print(f"  SpamBot error: {se}")

        # 2. Check kuponhesapsatis slowmode & test send capability
        try:
            entity = await client.get_entity('kuponhesapsatis')
            from telethon.tl.functions.channels import GetFullChannelRequest
            full = await client(GetFullChannelRequest(entity))
            slowmode = full.full_chat.slowmode_seconds
            next_date = full.full_chat.slowmode_next_send_date
            print(f"  Group kuponhesapsatis:")
            print(f"    Slowmode: {slowmode} seconds ({slowmode // 60} minutes)")
            print(f"    Next send allowed: {next_date}")
        except Exception as ge:
            print(f"  Group check error: {ge}")

        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_spambot_and_group())
