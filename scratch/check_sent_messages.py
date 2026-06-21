import asyncio
import sys
import json
import os
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def check_account(session_key, name):
    if not session_key:
        print(f"⚠️ {name} anahtarı yapılandırılmamış.")
        return
        
    client = TelegramClient(StringSession(session_key), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ {name}: Yetkisiz oturum (Giriş yapılmamış).")
            return
            
        me = await client.get_me()
        print(f"\n🔍 {name} (@{me.username or me.first_name}) için son gönderilen mesajlar taranıyor...")
        
        limit_date = datetime.now(timezone.utc) - timedelta(hours=24)
        sent_messages = []
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                try:
                    # Get last 5 messages from this chat
                    async for msg in client.iter_messages(dialog.entity, limit=5):
                        if msg.sender_id == me.id:
                            msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                            if msg_date > limit_date:
                                sent_messages.append({
                                    "chat": dialog.name,
                                    "username": getattr(dialog.entity, 'username', '-'),
                                    "date": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                                    "text": (msg.text or "")[:60] + "..."
                                })
                except Exception:
                    pass
                    
        if sent_messages:
            print(f"✅ Son 24 saatte gönderilen {len(sent_messages)} mesaj bulundu:")
            for m in sent_messages[:10]: # Print top 10
                print(f"  • [{m['date']}] @{m['username']} ({m['chat']}): {m['text']}")
            if len(sent_messages) > 10:
                print(f"  ...ve {len(sent_messages) - 10} mesaj daha.")
        else:
            print("ℹ️ Son 24 saatte gönderilmiş mesaj bulunamadı.")
            
    except Exception as e:
        print(f"❌ {name} hata: {type(e).__name__} - {e}")
    finally:
        await client.disconnect()

async def main():
    if not os.path.exists("bot_config.json"):
        print("❌ bot_config.json bulunamadı.")
        return
        
    with open("bot_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    s1 = cfg.get("ad_string_session", "")
    s2 = cfg.get("ad_string_session_2", "")
    
    await check_account(s1, "Hesap #1 (Froxy)")
    await check_account(s2, "Hesap #2 (KeyVadi)")

if __name__ == "__main__":
    asyncio.run(main())
