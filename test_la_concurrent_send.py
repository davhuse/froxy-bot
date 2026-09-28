import requests
import asyncio
import time
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    SlowModeWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    PeerFloodError
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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
session_str = vars.get('AD_STRING_SESSION_LISANSARENA', '')
API_ID = int(vars.get('TELEGRAM_API_ID') or 31076280)
API_HASH = vars.get('TELEGRAM_API_HASH') or '7ba4072dcf0a05a7ccf80e570866b6d8'

TARGET_GROUPS = ['zeroticaret', 'ticaretgruptr', 'wishx_2']

with open('messages/lisansarena_8.txt', 'r', encoding='utf-8') as f:
    MESSAGE_TEXT = f.read().strip()

async def send_to_one(client, group_name):
    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] [ISTEK BASLADI] -> @{group_name}")
    try:
        entity = await client.get_input_entity(group_name)
        msg = await client.send_message(entity, MESSAGE_TEXT)
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [BASARILI] -> @{group_name} (Mesaj ID: {msg.id}, Sure: {dt:.2f}s)")
        return {'group': group_name, 'status': 'success', 'message_id': msg.id, 'duration': dt}
    except FloodWaitError as e:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [FLOOD_WAIT] -> @{group_name}: {e.seconds} saniye bekleme zorunlu! (Sure: {dt:.2f}s)")
        return {'group': group_name, 'status': 'flood_wait', 'seconds': e.seconds}
    except SlowModeWaitError as e:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [SLOW_MODE] -> @{group_name}: Grup yavas modu {e.seconds}s bekletiyor. (Sure: {dt:.2f}s)")
        return {'group': group_name, 'status': 'slow_mode', 'seconds': e.seconds}
    except PeerFloodError as e:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [PEER_FLOOD] -> @{group_name}: Hesap kısıtlandı! {e}")
        return {'group': group_name, 'status': 'peer_flood', 'error': str(e)}
    except ChatWriteForbiddenError:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [YAZMA YASAK] -> @{group_name}: Grupta yazma izni yok.")
        return {'group': group_name, 'status': 'write_forbidden'}
    except UserBannedInChannelError:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [BAN] -> @{group_name}: Kullanici gruptan banlanmis.")
        return {'group': group_name, 'status': 'banned'}
    except Exception as e:
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] [HATA] -> @{group_name}: {type(e).__name__}: {e}")
        return {'group': group_name, 'status': 'error', 'error': str(e)}

async def main():
    print(f"=== LISANSARENA CANLI ESZAMANLI (SIMULTANEOUS) BLAST TESTI ===")
    print(f"Hedef Gruplar: {TARGET_GROUPS}")
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("LisansArena oturumu yetkili degil!")
        return
    me = await client.get_me()
    print(f"Baglanan Hesap: {me.first_name} (@{me.username}) ID={me.id}")
    
    print("\n[BILGI] 3 gruba ayni anda (asyncio.gather) istek gonderiliyor...")
    t_start = time.time()
    results = await asyncio.gather(*[send_to_one(client, g) for g in TARGET_GROUPS])
    total_dt = time.time() - t_start
    print(f"\n=== TEST SONUCU (Toplam Sure: {total_dt:.2f}s) ===")
    for r in results:
        print(f"  Grup: @{r['group']} -> Durum: {r['status']}")
    
    # Check messages 10 seconds later to verify if group bot deleted them
    print("\n[BILGI] 10 saniye sonra moderasyon botu kontrolu yapiliyor...")
    await asyncio.sleep(10)
    for r in results:
        if r.get('status') == 'success':
            try:
                entity = await client.get_input_entity(r['group'])
                check_msg = await client.get_messages(entity, ids=r['message_id'])
                if check_msg and not getattr(check_msg, 'empty', False):
                    print(f"  [GÖZLEM] @{r['group']} mesaji hala yayinda (silinmedi).")
                else:
                    print(f"  [UYARI] @{r['group']} mesaji moderasyon botu tarafindan SILINDI!")
            except Exception as e:
                print(f"  [KONTROL HATASI] @{r['group']}: {e}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
