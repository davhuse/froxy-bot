import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def main():
    print("🔑 Froxy AI - StringSession Olusturucu")
    print("--------------------------------------")
    print("Bu arac, botu Render/Koyeb gibi bulut sunucularda sifresiz calistirmak icin oturum kodu üretir.")
    
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()
    
    session_str = client.session.save()
    print("\n✅ Giris basarili!")
    print("--------------------------------------")
    print("🔑 SIZIN STRINGSESSION ANAHTARINIZ (Asagidaki yazinin tamamini kopyalayin):\n")
    print(session_str)
    print("\n--------------------------------------")
    print("Bu anahtari web panelinizdeki ilgili alana yapistirip kaydedin.")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
