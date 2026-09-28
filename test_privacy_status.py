import asyncio
import sys
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import GetPrivacyRequest
from telethon.tl.types import InputPrivacyKeyStatusTimestamp

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

API_ID = int(vars_data.get('TELEGRAM_API_ID', 31076280))
API_HASH = vars_data.get('TELEGRAM_API_HASH', "7ba4072dcf0a05a7ccf80e570866b6d8")

async def test_privacy():
    session_str = vars_data['AD_STRING_SESSION_JARVIS']
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    privacy = await client(GetPrivacyRequest(key=InputPrivacyKeyStatusTimestamp()))
    print("Current StatusTimestamp privacy rules:", privacy.rules)
    await client.disconnect()

asyncio.run(test_privacy())
