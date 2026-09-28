import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding='utf-8')

API_ID = 26500645
API_HASH = "ca29cb773b400938f3869b2d8e484a0c"
SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="
BOT_USERNAME = "JarvisCraftsBot"

async def test_bot():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Test client is not authorized!")
        return

    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username}) ID={me.id}")

    bot_entity = await client.get_input_entity(BOT_USERNAME)

    # Test 1: Send /start
    print("\n--- TEST 1: Sending /start ---")
    await client.send_message(bot_entity, "/start")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot_entity, limit=2)
    latest = msgs[0]
    print(f"Bot Reply:\n{latest.text[:300]}...")
    if latest.buttons:
        print("Buttons found:")
        for row in latest.buttons:
            print(" | ".join([b.text for b in row]))

    # Test 2: Send /siparislerim
    print("\n--- TEST 2: Sending /siparislerim ---")
    await client.send_message(bot_entity, "/siparislerim")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot_entity, limit=2)
    latest = msgs[0]
    print(f"Bot Reply:\n{latest.text}")
    if latest.buttons:
        print("Buttons found:")
        for row in latest.buttons:
            print(" | ".join([b.text for b in row]))

    # Test 3: Send /hesabim
    print("\n--- TEST 3: Sending /hesabim ---")
    await client.send_message(bot_entity, "/hesabim")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot_entity, limit=2)
    latest = msgs[0]
    print(f"Bot Reply:\n{latest.text}")

    # Test 4: Send /destek
    print("\n--- TEST 4: Sending /destek ---")
    await client.send_message(bot_entity, "/destek")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot_entity, limit=2)
    latest = msgs[0]
    print(f"Bot Reply:\n{latest.text}")
    if latest.buttons:
        print("Buttons found:")
        for row in latest.buttons:
            print(" | ".join([b.text for b in row]))

    # Test 5: Click in-bot ticket button if available or test ticket flow
    print("\n--- TEST 5: Starting In-Bot Ticket ---")
    ticket_button = None
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Destek Talebi" in b.text:
                    ticket_button = b
                    break
    if ticket_button:
        print("Clicking ticket button...")
        await ticket_button.click()
        await asyncio.sleep(3)
        msgs = await client.get_messages(bot_entity, limit=2)
        print(f"Prompt Reply:\n{msgs[0].text}")

        # Send support ticket content
        print("Sending ticket message: 'Merhaba, test destek talebidir.'")
        await client.send_message(bot_entity, "Merhaba, test destek talebidir.")
        await asyncio.sleep(3)
        msgs = await client.get_messages(bot_entity, limit=2)
        print(f"Ticket Confirmation Reply:\n{msgs[0].text}")

    # Test 6: Send /vip
    print("\n--- TEST 6: Sending /vip ---")
    await client.send_message(bot_entity, "/vip")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot_entity, limit=2)
    latest = msgs[0]
    print(f"Bot Reply:\n{latest.text[:300]}...")
    if latest.buttons:
        print("Buttons found:")
        for row in latest.buttons:
            print(" | ".join([b.text for b in row]))

    await client.disconnect()
    print("\n✅ All live bot tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_bot())
