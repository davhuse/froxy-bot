import asyncio
import sys
import json
from telethon import TelegramClient, functions
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

TEST_CANDIDATES = [
    # Sohbet
    {"cat": "sohbet", "username": "turkcesohbetler", "title": "Türkçe Sohbet"},
    {"cat": "sohbet", "username": "Kocaeli_sohbet_muhabbet", "title": "SOHBET DEVRİ"},
    {"cat": "sohbet", "username": "sohbetimi", "title": "Sohbet-Muhabbet"},
    {"cat": "sohbet", "username": "universite_sohbet", "title": "Üniversiteliler Sohbet"},
    
    # Kripto & Borsa
    {"cat": "borsa", "username": "coinsohbettr", "title": "Coin Sohbet 🇹🇷"},
    {"cat": "borsa", "username": "kriptoturkiye", "title": "Kripto Türkiye"},
    {"cat": "borsa", "username": "kripto1", "title": "Kripto Analiz"},
    
    # Haber & Yazılım
    {"cat": "haber", "username": "yazilimtoplulugu", "title": "Yazılım Topluluğu"},
    {"cat": "haber", "username": "linux_tr", "title": "Linux Türkiye"},
    {"cat": "haber", "username": "yazilim0", "title": "Yazılım Grubu"},
    {"cat": "haber", "username": "yazilimogreniyorumorg", "title": "Yazılım Öğreniyorum"},
    
    # Ticaret Örnekleri
    {"cat": "ticaret", "username": "satcek", "title": "Çek Satış"},
    {"cat": "ticaret", "username": "ceksat", "title": "Çek Satış 2"},
    {"cat": "ticaret", "username": "kuponindirimsatis", "title": "Kupon İndirim"},
    {"cat": "ticaret", "username": "ticaretcanavari", "title": "Ticaret Canavarı"},
    {"cat": "ticaret", "username": "alsatticarettz", "title": "Al Sat Ticaret"},
]

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    verified_working = []
    
    print("🚀 CANLI MESAJ GÖNDERİM & İZİN TESTİ BAŞLADI...\n")
    
    for item in TEST_CANDIDATES:
        u = item["username"]
        cat = item["cat"]
        title = item["title"]
        try:
            entity = await asyncio.wait_for(client.get_entity(u), timeout=5.0)
            
            # Join channel
            try:
                await asyncio.wait_for(client(functions.channels.JoinChannelRequest(channel=entity)), timeout=5.0)
            except Exception:
                pass
                
            # Send sample test text
            msg = await asyncio.wait_for(client.send_message(entity, "Selamlar herkese, iyi günler"), timeout=6.0)
            print(f"  ✅ [BAŞARILI] @{u:<26} ({cat.upper()}) | Mesaj ID: {msg.id}")
            verified_working.append(item)
            
            # Delete our test greeting so we don't clutter the group
            try:
                await client.delete_messages(entity, [msg.id])
            except Exception:
                pass
                
        except Exception as e:
            print(f"  ❌ [YAZMA ENGELİ] @{u:<26} ({cat.upper()}) -> {type(e).__name__}: {e}")
            
        await asyncio.sleep(2)  # safe delay between sends
        
    await client.disconnect()
    
    print(f"\n🏆 Testi Geçen Kesin Çalışan Grup Sayısı: {len(verified_working)}")
    with open("live_tested_working_groups.json", "w", encoding="utf-8") as f:
        json.dump(verified_working, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
