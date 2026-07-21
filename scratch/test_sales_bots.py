import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def test_official_sales_bots():
    c = TelegramClient('c4hex_session', api_id, api_hash)
    await c.start()

    print('====================================================')
    print('   SATIŞ BOTLARI CANLI TEST RAPORU                  ')
    print('====================================================\n')

    # TEST 1: @KeyVadiSatisBot
    print('1️⃣  @KeyVadiSatisBot TEST EDİLİYOR...')
    m1 = await c.send_message('@KeyVadiSatisBot', 'Canva')
    await asyncio.sleep(4)
    bot1_ok = False
    async for r in c.iter_messages('@KeyVadiSatisBot', limit=1):
        if r.id > m1.id and not r.out:
            print('   ✅ @KeyVadiSatisBot YANIT VERDİ:')
            print(f'   {r.text.strip()[:150]}...\n')
            bot1_ok = True
            break
    if not bot1_ok:
        print('   ❌ @KeyVadiSatisBot YANIT VERMEDİ!\n')

    # TEST 2: @LisansArenaBot
    print('2️⃣  @LisansArenaBot TEST EDİLİYOR...')
    m2 = await c.send_message('@LisansArenaBot', 'Adobe')
    await asyncio.sleep(4)
    bot2_ok = False
    async for r in c.iter_messages('@LisansArenaBot', limit=1):
        if r.id > m2.id and not r.out:
            print('   ✅ @LisansArenaBot YANIT VERDİ:')
            print(f'   {r.text.strip()[:150]}...\n')
            bot2_ok = True
            break
    if not bot2_ok:
        print('   ❌ @LisansArenaBot YANIT VERMEDİ!\n')

    await c.disconnect()

    print('====================================================')
    if bot1_ok and bot2_ok:
        print('🎉 TEST SONUCU: HER İKİ SATIŞ BOTU DA CANLIDA %100 AKTİF VE YANIT VERİYOR!')
    else:
        print('⚠️ TEST SONUCU: Botlardan biri yanıt vermedi.')
    print('====================================================')

if __name__ == '__main__':
    asyncio.run(test_official_sales_bots())
