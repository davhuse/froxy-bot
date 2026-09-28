import asyncio
import sys
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

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
vars = r.json().get('data', {}).get('variables', {})

api_id = int(vars['TELEGRAM_API_ID'])
api_hash = vars['TELEGRAM_API_HASH']
tester_session = vars['AD_STRING_SESSION_FROXY']

BOTS_TO_TEST = [
    ("KeyVadiSatisBot", "keyvadi"),
    ("LisansArenaBot", "lisansarena"),
    ("JarvisCraftsBot", "jarvis"),
]

async def verify_bots():
    client = TelegramClient(StringSession(tester_session), api_id, api_hash)
    await client.connect()
    me = await client.get_me()
    print(f"Tester logged in as: {me.first_name} (@{me.username}) ID={me.id}")

    for bot_username, brand in BOTS_TO_TEST:
        print(f"\n==========================================")
        print(f"TESTING BOT: @{bot_username} ({brand})")
        print(f"==========================================")
        bot_entity = await client.get_input_entity(bot_username)

        # Test A: Send /start
        print(f"  [1] Sending /start to @{bot_username}...")
        await client.send_message(bot_entity, "/start")
        await asyncio.sleep(2.5)
        msgs = await client.get_messages(bot_entity, limit=1)
        if msgs and msgs[0].sender_id != me.id:
            txt = msgs[0].text.replace('\n', ' ')[:100]
            print(f"    Reply to /start: {txt}")
        else:
            print("    No direct text reply or replied with media/buttons.")

        # Test B: Send Order Inquiry "siparişim nerede kod gelmedi"
        print(f"  [2] Sending order inquiry: 'siparişim nerede kod gelmedi'...")
        await client.send_message(bot_entity, "siparişim nerede kod gelmedi")
        await asyncio.sleep(2.5)
        msgs = await client.get_messages(bot_entity, limit=1)
        if msgs and msgs[0].sender_id != me.id:
            reply_text = msgs[0].text
            print(f"    Order Inquiry Reply:")
            for line in reply_text.splitlines()[:5]:
                print(f"      {line}")
        else:
            print("    No reply received!")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(verify_bots())
