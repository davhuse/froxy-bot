import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel

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

async def inspect():
    for name, s_str in sessions.items():
        if not s_str:
            print(f'[{name}] NO SESSION STR')
            continue
        client = TelegramClient(StringSession(s_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            print(f'[{name}] NOT AUTHORIZED')
            await client.disconnect()
            continue
        me = await client.get_me()
        print(f'=== [{name}] Me: {me.first_name} (@{me.username}) ID: {me.id} Phone: {me.phone} ===')
        try:
            entity = await client.get_entity('kuponhesapsatis')
            print(f'  Entity: {getattr(entity, "title", "")} (@{getattr(entity, "username", "")})')
            print(f'  Entity type: {type(entity).__name__}')
            if isinstance(entity, Channel):
                print(f'  broadcast (channel): {entity.broadcast}, megagroup: {entity.megagroup}')
                print(f'  restricted: {entity.restricted}, restriction_reason: {entity.restriction_reason}')
                print(f'  default_banned_rights: {entity.default_banned_rights}')
            
            try:
                full = await client(GetFullChannelRequest(entity))
                print(f'  Slowmode seconds: {full.full_chat.slowmode_seconds}')
                print(f'  Slowmode next send date: {full.full_chat.slowmode_next_send_date}')
            except Exception as fe:
                print(f'  FullChannel error: {fe}')

            try:
                from telethon.tl.functions.channels import GetParticipantRequest
                p = await client(GetParticipantRequest(entity, 'me'))
                participant = p.participant
                print(f'  Participant type: {type(participant).__name__}')
                if hasattr(participant, 'banned_rights') and participant.banned_rights:
                    print(f'  User banned_rights: {participant.banned_rights}')
                if hasattr(participant, 'admin_rights') and participant.admin_rights:
                    print(f'  User admin_rights: {participant.admin_rights}')
            except Exception as pe:
                print(f'  GetParticipant error: {pe}')

            try:
                messages = await client.get_messages(entity, limit=10)
                print(f'  Recent messages count: {len(messages)}')
                for m in messages:
                    sender = await m.get_sender()
                    sender_name = getattr(sender, "first_name", "") if sender else "Unknown"
                    txt = (m.text or "[Media]").replace("\n", " ")[:80]
                    print(f'    [{m.date}] {sender_name}: {txt.encode("ascii", "replace").decode("ascii")}')
            except Exception as me_err:
                print(f'  GetMessages error: {me_err}')
        except Exception as e:
            print(f'  Error: {type(e).__name__}: {e}')
        finally:
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(inspect())
