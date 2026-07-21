import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def run_live_anti_spam_test():
    c = TelegramClient('c4hex_session', api_id, api_hash)
    await c.start()
    me = await c.get_me()

    print('====================================================')
    print('   CANLI SPAM VE MÜKERRER MESAJ ENGELİ TESTİ        ')
    print('====================================================\n')

    # TEST 1: @KeyVadiOnline
    print('1️⃣  @KeyVadiOnline HESABINA 0.5 SANİYEDE PEŞ PEŞE 4 MESAJ GÖNDERİLİYOR...')
    m1_start = await c.send_message('@KeyVadiOnline', 'Selam Canva fiyatı ne kadar?')
    await c.send_message('@KeyVadiOnline', 'Orada mısınız?')
    await c.send_message('@KeyVadiOnline', 'Canva var mı?')
    await c.send_message('@KeyVadiOnline', 'Fiyat yazın lütfen')

    print('⏳ 8 Saniye Yanıtlar Bekleniyor...')
    await asyncio.sleep(8)

    replies_kv = []
    async for r in c.iter_messages('@KeyVadiOnline', limit=10):
        if r.id > m1_start.id and r.sender_id != me.id:
            replies_kv.append(r.text)

    print(f'📊 @KeyVadiOnline Tarafından Gelen Bot Yanıt Sayısı: {len(replies_kv)} (Hedef: Tam 1 Yanıt!)')
    for idx, txt in enumerate(replies_kv, 1):
        print(f'   BOT YANITI {idx}: {txt.strip()[:80]}...')

    print('\n----------------------------------------------------\n')

    # TEST 2: @LisansArenaOnline
    print('2️⃣  @LisansArenaOnline HESABINA 0.5 SANİYEDE PEŞ PEŞE 4 MESAJ GÖNDERİLİYOR...')
    m2_start = await c.send_message('@LisansArenaOnline', 'Selam Adobe lisansı ne kadar?')
    await c.send_message('@LisansArenaOnline', 'Fiyat nedir?')
    await c.send_message('@LisansArenaOnline', 'Hemen alacağım')
    await c.send_message('@LisansArenaOnline', 'Cevap var mı?')

    print('⏳ 8 Saniye Yanıtlar Bekleniyor...')
    await asyncio.sleep(8)

    replies_la = []
    async for r in c.iter_messages('@LisansArenaOnline', limit=10):
        if r.id > m2_start.id and r.sender_id != me.id:
            replies_la.append(r.text)

    print(f'📊 @LisansArenaOnline Tarafından Gelen Bot Yanıt Sayısı: {len(replies_la)} (Hedef: Tam 1 Yanıt!)')
    for idx, txt in enumerate(replies_la, 1):
        print(f'   BOT YANITI {idx}: {txt.strip()[:80]}...')

    await c.disconnect()

    print('\n====================================================')
    if len(replies_kv) == 1 and len(replies_la) == 1:
        print('🎉 TEST SONUCU: BAŞARILI! Mükerrer yanıt engeli %100 doğrulandı.')
    else:
        print(f'📊 TEST SONUCU: KeyVadi={len(replies_kv)} yanıt, LisansArena={len(replies_la)} yanıt')
    print('====================================================')

if __name__ == '__main__':
    asyncio.run(run_live_anti_spam_test())
