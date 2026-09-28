import asyncio
import sys
from telethon import TelegramClient, functions, types, errors
from telethon.sessions import StringSession

API_ID = 20857997
API_HASH = "ca29bc78298c92a2a09c25bb34586f1e"

with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
    SESSION = f.read().strip()

sys.stdout.reconfigure(encoding='utf-8')

candidates = {
    "sohbet": [
        "TurkceSohbetler", "universite_sohbet", "turkcesohbet", "sohbetgrubutr",
        "sohbetmuhabbettr", "sohbetru", "turkiyediyalog", "trsohbetevi",
        "turkcechat", "sohbetturkiye", "istanbulsohbettr", "ankarasohbet",
        "gencsohbet", "turkiyegencligi", "dostluksohbet", "arkadasliksohbet"
    ],
    "borsa": [
        "KriptoTurkiye", "CoinSohbetTR", "KriptoSozlukTVPiyasaMuhabbeti",
        "bitgetturkiye", "turkiyeborsa", "borsaistanbulchat", "kriptoanaliztr",
        "binanceturkiyegrup", "kriptosohbeti"
    ],
    "teknoloji": [
        "yazilimtoplulugu", "linux_tr", "yazilim0", "yazilimogreniyorumorg",
        "pythonturkiye", "turkiyepython", "kodlama", "yazilimcilar"
    ]
}

async def test_group(client, me, g_name):
    try:
        entity = await client.get_entity(g_name)
        if getattr(entity, 'broadcast', False):
            return False, "Broadcast Channel (Read Only)"

        # Check if we can join or already joined
        try:
            await client(functions.channels.JoinChannelRequest(channel=entity))
            await asyncio.sleep(1.5)
        except errors.UserAlreadyParticipantError:
            pass
        except Exception as je:
            return False, f"Join failed: {type(je).__name__}: {je}"

        # Check permissions
        try:
            perms = await client.get_permissions(entity, me)
            if not perms.send_messages:
                return False, "send_messages=False"
        except Exception as pe:
            # could be standard chat or error
            pass

        # Try sending a test message
        test_msg = await client.send_message(entity, "Selamlar")
        # Immediately delete the test message to keep chat clean
        try:
            await client.delete_messages(entity, [test_msg.id])
        except Exception:
            pass
        return True, "OK"

    except errors.FloodWaitError as fwe:
        return False, f"FloodWait: {fwe.seconds}s"
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {e}"

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Logged in as @{me.username} ({me.id})")

    results = {}
    for cat, g_list in candidates.items():
        print(f"\n--- Testing Category: {cat} ---")
        results[cat] = []
        for g in g_list:
            ok, reason = await test_group(client, me, g)
            print(f"@{g}: {'SUCCESS' if ok else 'FAILED'} ({reason})")
            if ok:
                results[cat].append(g)
            await asyncio.sleep(3)

    print("\n--- FINAL WORKING GROUPS ---")
    for cat, working in results.items():
        print(f"{cat}: {working}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
