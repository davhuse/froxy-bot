import asyncio
import sys
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = '7ba4072dcf0a05a7ccf80e570866b6d8'
c4hex_session_path = r"c:\Users\habil\.gemini\antigravity\scratch\tg-bot-reklam\c4hex_session.session"

async def test_cooldown():
    client = TelegramClient(c4hex_session_path, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Client yetkilendirilmemiş.")
            return
            
        bot_entity = await client.get_input_entity("@KeyVadiSatisBot")
        
        print("💬 1. Mesaj gönderiliyor: 'selam'")
        sent1 = await client.send_message(bot_entity, "selam")
        
        await asyncio.sleep(1.5)
        
        print("💬 2. Mesaj gönderiliyor: 'nasıl alabilirim?' (cooldown tetiklemeli)")
        sent2 = await client.send_message(bot_entity, "nasıl alabilirim?")
        
        print("⏳ Cevaplar için bekleniyor...")
        await asyncio.sleep(12)
        
        replies = []
        async for msg in client.iter_messages(bot_entity, limit=10):
            if msg.id > sent1.id and not msg.out:
                replies.append(msg.text)
                
        print(f"\n📩 Alınan cevap sayısı: {len(replies)}")
        for idx, r in enumerate(reversed(replies), 1):
            print(f"   Cevap #{idx}: {r[:100].replace(chr(10), ' ')}...")
            
        if len(replies) == 1:
            print("\n🌟 TEST BAŞARILI! 15 saniyelik global AI cooldown çalışıyor ve mükerrer spam engelleniyor!")
        elif len(replies) > 1:
            print("\n⚠️ TEST UYARISI: Birden fazla cevap geldi. (Sunucudaki eski versiyon aktif olabilir, yeni versiyonun deploy olmasını beklemek gerekir.)")
        else:
            print("\n❌ Hiç cevap gelmedi.")
            
    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_cooldown())
