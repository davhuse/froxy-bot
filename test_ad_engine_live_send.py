import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 26500645
API_HASH = "ca29cb773b400938f3869b2d8e484a0c"
SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="
BOT_USERNAME = "JarvisCraftsBot"

async def run_test():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Unauthorized session!")
        return

    bot = await client.get_input_entity(BOT_USERNAME)

    print("--- STEP 1: Opening Ad Engine Menu ---")
    await client.send_message(bot, "/start")
    await asyncio.sleep(2)
    msgs = await client.get_messages(bot, limit=1)
    
    ad_button = None
    for row in msgs[0].buttons:
        for b in row:
            if "Oto-Reklam Motoru" in b.text:
                ad_button = b
                break
    if not ad_button:
        print("Ad button not found!")
        return
    await ad_button.click()
    await asyncio.sleep(2)

    msgs = await client.get_messages(bot, limit=1)
    print("Ad Engine Menu Text:\n" + msgs[0].text)

    # Check if we need to bind test account
    bind_button = None
    start_button = None
    stop_button = None

    for row in msgs[0].buttons:
        for b in row:
            if "Hızlı Test Hesabı Bağla" in b.text:
                bind_button = b
            elif "Gönderimi Başlat" in b.text:
                start_button = b
            elif "Gönderimi Durdur" in b.text:
                stop_button = b

    if bind_button:
        print("--- STEP 2: Binding Test Account (+1386) ---")
        await bind_button.click()
        await asyncio.sleep(2)
        msgs = await client.get_messages(bot, limit=1)
        print("After bind menu:\n" + msgs[0].text)
        for row in msgs[0].buttons:
            for b in row:
                if "Gönderimi Başlat" in b.text:
                    start_button = b

    if start_button:
        print("--- STEP 3: Starting Ad Dispatch ---")
        await start_button.click()
        await asyncio.sleep(3)
        msgs = await client.get_messages(bot, limit=1)
        print("Engine started state:\n" + msgs[0].text)
    else:
        print("Engine was already running or start button not found")

    print("\n--- STEP 4: Waiting 25 seconds for background worker to join group and dispatch message ---")
    await asyncio.sleep(25)

    # Fetch recent messages to verify delivery notification
    print("\n--- STEP 5: Checking for DM Notification ---")
    recent_msgs = await client.get_messages(bot, limit=5)
    for m in recent_msgs:
        if "Mesaj Başarıyla İletildi" in m.text or "Oto-Mesaj Motoru" in m.text:
            print(f"\n🎉 FOUND DELIVERY NOTIFICATION:\n{m.text}\n")
            break
    else:
        print("Recent message text: " + recent_msgs[0].text)

    # Check /hesabim to verify updated quota
    print("\n--- STEP 6: Checking /hesabim for Quota and Sent Stats ---")
    await client.send_message(bot, "/hesabim")
    await asyncio.sleep(2)
    hesap_msg = await client.get_messages(bot, limit=1)
    print(hesap_msg[0].text)

    # Step 7: Stop the engine so it doesn't keep running in loop
    print("\n--- STEP 7: Stopping Ad Engine ---")
    await client.send_message(bot, "/start")
    await asyncio.sleep(2)
    msgs = await client.get_messages(bot, limit=1)
    for row in msgs[0].buttons:
        for b in row:
            if "Oto-Reklam Motoru" in b.text:
                await b.click()
                break
    await asyncio.sleep(2)
    msgs = await client.get_messages(bot, limit=1)
    for row in msgs[0].buttons:
        for b in row:
            if "Gönderimi Durdur" in b.text:
                await b.click()
                print("Ad engine successfully paused.")
                break

    await client.disconnect()
    print("\n✅ Ad Engine Live Dispatch Test Completed!")

if __name__ == "__main__":
    asyncio.run(run_test())
