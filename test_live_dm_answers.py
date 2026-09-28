import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 26500645
API_HASH = "ca29cb773b400938f3869b2d8e484a0c"
SESSION = "1AZWarzQBuyWtsQgpjidYIjcpvAltCNtIcGqZKozRBwERfmfTokqlcs-7-Hzfui4OUwjNHGldD17naL63mHZwNHpezALDayddc9Oijpl-AraFkFhUIGduHoDFlT14Oi-l3rn2QF67SaRLo5heKlqIKNql43SSo9mJY92hz3SYwBp5RHcsRJRWi1m9ZBXLhI_4i0Ai9g5-a_TDGuk6hHnd_zosrZbH-Y6TuOLMSMO3aLloFuLjH6AoVBdx2T3sdrUhG93l7Igo53XSBBNpxDgs-cMn6r_av--OvXfy30J1dQYashtig2hv1RoVmfD9AT2sB_Dn2SvqKS66Nqr9BO3wRs7LneidBsY="

async def test_dm():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    
    # 1. Test question to KeyVadiDestek
    dest_kv = await client.get_input_entity("KeyVadiDestek")
    print("Sending pre-sales question to KeyVadiDestek: 'Windows 11 omur boyu mu?'")
    await client.send_message(dest_kv, "Windows 11 omur boyu mu?")
    await asyncio.sleep(5)
    msgs = await client.get_messages(dest_kv, limit=3)
    for m in msgs:
        if m.sender_id != 8777291796:
            print("Reply from KeyVadiDestek:")
            print(m.text)
            break

    # 2. Test question to JarvisCraft
    dest_jc = await client.get_input_entity("JarvisCraft")
    print("\nSending pre-sales question to JarvisCraft: 'Telegram botu satisi var mi?'")
    await client.send_message(dest_jc, "Telegram botu satisi var mi?")
    await asyncio.sleep(5)
    msgs = await client.get_messages(dest_jc, limit=3)
    for m in msgs:
        if m.sender_id != 8777291796:
            print("Reply from JarvisCraft:")
            print(m.text)
            break

    await client.disconnect()

asyncio.run(test_dm())
