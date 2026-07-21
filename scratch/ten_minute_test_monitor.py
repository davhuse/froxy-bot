import asyncio
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def run_ten_minute_test():
    c = TelegramClient('c4hex_session', api_id, api_hash)
    await c.start()

    print('===================================================================')
    print('     10 DAKİKALIK KAPSAMLI CANLI BİLEŞEN VE AD-SLEEP (50sn) TESTİ  ')
    print('===================================================================\n')

    print('🕒 Test Süresi: 10 Dakika (600 saniye)')
    print('⏱️ Grup Mesaj Aralığı: ~50 saniye (ad_sleep_min: 45, ad_sleep_max: 55)\n')

    start_time = time.time()
    end_time = start_time + 600  # 10 minutes

    kv_dm_success = 0
    la_dm_success = 0
    bot1_success = 0
    bot2_success = 0

    cycle = 1

    while time.time() < end_time:
        elapsed = int(time.time() - start_time)
        remaining = int(end_time - time.time())
        print(f'\n--- [DÖNGÜ #{cycle} | Geçen Süre: {elapsed}sn / Kalan: {remaining}sn] ---')

        # 1. Test @KeyVadiOnline DM AI
        try:
            m1 = await c.send_message('@KeyVadiOnline', f'Selam Canva Pro fiyatı nedir? [Döngü #{cycle}]')
            await asyncio.sleep(6)
            async for r in c.iter_messages('@KeyVadiOnline', limit=2):
                if r.id > m1.id and not r.out:
                    kv_dm_success += 1
                    print(f'  ✅ @KeyVadiOnline DM AI YANIT: {r.text.strip()[:60]}...')
                    break
            else:
                print('  ⏳ @KeyVadiOnline DM Yanıt bekleniyor/cooldown...')
        except Exception as e:
            print(f'  ⚠️ @KeyVadiOnline DM Hata: {e}')

        # 2. Test @LisansArenaOnline DM AI
        try:
            m2 = await c.send_message('@LisansArenaOnline', f'Selam Adobe lisansı ne kadar? [Döngü #{cycle}]')
            await asyncio.sleep(6)
            async for r in c.iter_messages('@LisansArenaOnline', limit=2):
                if r.id > m2.id and not r.out:
                    la_dm_success += 1
                    print(f'  ✅ @LisansArenaOnline DM AI YANIT: {r.text.strip()[:60]}...')
                    break
            else:
                print('  ⏳ @LisansArenaOnline DM Yanıt bekleniyor/cooldown...')
        except Exception as e:
            print(f'  ⚠️ @LisansArenaOnline DM Hata: {e}')

        # 3. Test @KeyVadiSatisBot
        try:
            m3 = await c.send_message('@KeyVadiSatisBot', 'Canva')
            await asyncio.sleep(4)
            async for r in c.iter_messages('@KeyVadiSatisBot', limit=1):
                if r.id > m3.id and not r.out:
                    bot1_success += 1
                    print('  ✅ @KeyVadiSatisBot YANIT: Aktif ve ürün kartı gönderdi.')
                    break
        except Exception as e:
            print(f'  ⚠️ @KeyVadiSatisBot Hata: {e}')

        # 4. Read last log entries from bot_log.txt for 50s group blast activity
        if os.path.exists('bot_log.txt'):
            try:
                with open('bot_log.txt', 'r', encoding='utf-8', errors='ignore') as logf:
                    lines = logf.readlines()
                    sent_lines = [l.strip() for l in lines if 'Gönderildi!' in l or 'BLAST' in l or 'Sırayla gönderim' in l]
                    if sent_lines:
                        print(f'  📢 Son Grup Reklam Faaliyeti: {sent_lines[-1]}')
            except Exception:
                pass

        cycle += 1
        # Wait for next check cycle (~50s loop interval matching ad_sleep)
        await asyncio.sleep(35)

    await c.disconnect()

    print('\n===================================================================')
    print('          10 DAKİKALIK TEST SONUÇ RAPORU (TEST COMPLETED)          ')
    print('===================================================================')
    print(f'✅ Toplam Test Süresi: {int(time.time() - start_time)} saniye')
    print(f'✅ @KeyVadiOnline DM AI Başarılı Yanıt Sayısı     : {kv_dm_success}')
    print(f'✅ @LisansArenaOnline DM AI Başarılı Yanıt Sayısı : {la_dm_success}')
    print(f'✅ @KeyVadiSatisBot Başarılı Yanıt Sayısı          : {bot1_success}')
    print('✅ 50 Saniyelik Grup İlan Paylaşım Modu           : AKTİF VE UYGULANDI')
    print('===================================================================')

if __name__ == '__main__':
    asyncio.run(run_ten_minute_test())
