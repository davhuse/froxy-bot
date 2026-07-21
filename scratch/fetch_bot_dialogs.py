import asyncio
import sys
import json
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'

# Read bot_config.json to get tokens
with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

kv_token = cfg.get("bot_token")
la_token = cfg.get("lisansarena_bot_token")

async def search_bot_dialogs(bot_token, bot_name):
    print(f"\n🔍 {bot_name} için dialoglar sorgulanıyor...")
    client = TelegramClient(f'scratch/{bot_name.lower()}_temp_session', API_ID, API_HASH)
    try:
        await client.start(bot_token=bot_token)
        print(f"✅ Bot olarak bağlanıldı.")
        
        dialogs = await client.get_dialogs(limit=50)
        print(f"Son {len(dialogs)} aktif dialog tarandı:")
        found = False
        for dialog in dialogs:
            title = dialog.title
            username = getattr(dialog.entity, 'username', 'yok')
            entity_id = dialog.id
            
            # Print recent messages from this user to check context if they match
            if "islamix" in title.lower() or "islamix" in username.lower():
                print(f"🎯 HEDEF KULLANICI BULUNDU: {title} (@{username}) | ID: {entity_id}")
                found = True
                
                # Fetch recent messages in this chat
                print("   Son 10 mesaj:")
                async for msg in client.iter_messages(dialog.entity, limit=10):
                    sender_name = "Bot" if msg.out else "Kullanıcı"
                    print(f"     [{msg.date.strftime('%Y-%m-%d %H:%M:%S')}] {sender_name}: {repr(msg.text)}")
            else:
                # print a summary list just to see who chatted
                pass
        if not found:
            print("❌ Bu botta 'islamix' kullanıcı adına veya adına sahip kimse bulunamadı.")
            print("Aktif son 15 sohbet:")
            for d in dialogs[:15]:
                print(f"  - {d.title} (@{getattr(d.entity, 'username', 'yok')})")
    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        await client.disconnect()

async def main():
    if kv_token:
        await search_bot_dialogs(kv_token, "KeyVadi")
    print("=" * 50)
    if la_token:
        await search_bot_dialogs(la_token, "LisansArena")

if __name__ == "__main__":
    asyncio.run(main())
