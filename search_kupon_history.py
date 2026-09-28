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

TARGET_IDS = {8791896048, 8825645102, 8797763469, 8387947754}

async def search_messages():
    client = TelegramClient(StringSession(vars['AD_STRING_SESSION_FROXY']), api_id, api_hash)
    await client.connect()
    entity = await client.get_entity('kuponhesapsatis')
    
    print("Fetching last 300 messages from kuponhesapsatis...")
    messages = await client.get_messages(entity, limit=300)
    found = 0
    service_deletes = 0
    bot_warnings = []
    
    for m in messages:
        sender_id = m.sender_id
        if sender_id in TARGET_IDS or (m.text and any(k in m.text.lower() for k in ['keyvadi', 'lisansarena', 'jarviscraft', 'froxy'])):
            found += 1
            sender = await m.get_sender()
            sname = getattr(sender, 'first_name', str(sender_id))
            print(f"  FOUND: [{m.date}] {sname} (ID: {sender_id}): {m.text[:60] if m.text else '[Media]'}")
        if sender_id in [162726413, 609517172]: # GroupHelpBot, MissRose_bot
            if m.text:
                bot_warnings.append(f"[{m.date}] {m.text.replace(chr(10), ' ')[:80]}")

    print(f"Total matching messages found: {found}")
    print(f"Recent bot warnings/actions ({len(bot_warnings)}):")
    for w in bot_warnings[:10]:
        print(f"  {w.encode('ascii', 'replace').decode('ascii')}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(search_messages())
