import asyncio
import os
import sys
import time
import psutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from telethon import TelegramClient

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def run_30min_monitor():
    tester = TelegramClient('c4hex_session', api_id, api_hash)
    await tester.start()

    print('===================================================================')
    print('      30 DAKİKALIK (HER 1 DAKİKADA BİR KONTROL) CANLI TEST          ')
    print('===================================================================\n')
    print('🕒 Toplam Süre: 30 Dakika (1800 Saniye)')
    print('⏱️ Kontrol Sıklığı: Her 60 Saniyede Bir Tam Sistem Kontrolü\n')

    start_time = time.time()
    end_time = start_time + 1800  # 30 minutes

    minute_count = 1

    while time.time() < end_time:
        elapsed_min = int((time.time() - start_time) // 60)
        remaining_min = 30 - elapsed_min

        print(f'\n==================== [DAKİKA #{minute_count} | Geçen: {elapsed_min}dk / Kalan: {remaining_min}dk] ====================')

        # 1. Process Check
        active_bots = []
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = ' '.join(p.info['cmdline'] or [])
                if 'python' in p.info['name'].lower():
                    for b in ['otomatik_katil.py', 'froxy_bot.py', 'lisansarena_bot.py', 'froxy_destek_bot.py', 'watchdog_service.py']:
                        if b in cmd:
                            active_bots.append(b)
            except Exception:
                pass
        unique_active = sorted(list(set(active_bots)))
        print(f'1️⃣ Aktif Servisler ({len(unique_active)}/5): {", ".join(unique_active)}')

        # 2. Latest Log Check from otomatik_katil.py
        recent_log_activity = "N/A"
        try:
            # find latest log from task or bot_log.txt
            if os.path.exists('bot_log.txt'):
                with open('bot_log.txt', 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    sent_lines = [l.strip() for l in lines if 'Gönderildi!' in l or 'DM Alındı' in l or 'Kalan' in l]
                    if sent_lines:
                        recent_log_activity = sent_lines[-1]
        except Exception as e:
            recent_log_activity = str(e)
        print(f'2️⃣ Son Reklam / Log Aktivitesi: {recent_log_activity}')

        # 3. Live Quick DM Test (@KeyVadiOnline)
        try:
            m1 = await tester.send_message('@KeyVadiOnline', f'Selam Canva Pro fiyatı nedir? [Dakika #{minute_count}]')
            await asyncio.sleep(4)
            kv_reply = False
            async for r in tester.iter_messages('@KeyVadiOnline', limit=2):
                if r.id > m1.id and not r.out:
                    print(f'3️⃣ @KeyVadiOnline DM AI YANIT   : BAŞARILI ({r.text.strip()[:60]}...)')
                    kv_reply = True
                    break
            if not kv_reply:
                print('3️⃣ @KeyVadiOnline DM AI YANIT   : Beklemede / Cooldown')
        except Exception as e:
            print(f'3️⃣ @KeyVadiOnline DM Hata       : {e}')

        # 4. Live Quick DM Test (@LisansArenaOnline)
        try:
            m2 = await tester.send_message('@LisansArenaOnline', f'Selam Adobe lisansı ne kadar? [Dakika #{minute_count}]')
            await asyncio.sleep(4)
            la_reply = False
            async for r in tester.iter_messages('@LisansArenaOnline', limit=2):
                if r.id > m2.id and not r.out:
                    print(f'4️⃣ @LisansArenaOnline DM AI YANIT: BAŞARILI ({r.text.strip()[:60]}...)')
                    la_reply = True
                    break
            if not la_reply:
                print('4️⃣ @LisansArenaOnline DM AI YANIT: Beklemede / Cooldown')
        except Exception as e:
            print(f'4️⃣ @LisansArenaOnline DM Hata   : {e}')

        minute_count += 1
        # Sleep for 60 seconds (1 minute interval)
        await asyncio.sleep(60)

    await tester.disconnect()

    print('\n===================================================================')
    print('          30 DAKİKALIK TEST SONUÇ RAPORU (TEST COMPLETED)          ')
    print('===================================================================')
    print(f'✅ Toplam Geçen Süre: {int((time.time() - start_time) // 60)} Dakika')
    print('✅ Tüm Servisler & Botlar 30 Dakika Boyunca 1 dakikalık aralıklarla denetlendi.')
    print('===================================================================')

if __name__ == '__main__':
    asyncio.run(run_30min_monitor())
