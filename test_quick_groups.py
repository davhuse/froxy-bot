import asyncio
import sys
from telethon import TelegramClient, functions, types, errors
from telethon.sessions import StringSession

API_ID = 20857997
API_HASH = "ca29bc78298c92a2a09c25bb34586f1e"

with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
    SESSION = f.read().strip()

sys.stdout.reconfigure(encoding='utf-8')

# Let's test groups from gruplar.txt (ticaret), and known sohbet/borsa/teknoloji groups
groups_to_test = [
    # Ticaret from gruplar.txt
    ("ticaret", "satcek"),
    ("ticaret", "kupongrupta"),
    ("ticaret", "alimsatimmerkezii"),
    ("ticaret", "kuponhesapsatis"),
    ("ticaret", "kuponsat"),
    ("ticaret", "tichubtr"),
    ("ticaret", "ceksat"),
    # Sohbet candidates
    ("sohbet", "TurkceSohbetler"),
    ("sohbet", "universite_sohbet"),
    ("sohbet", "turkcesohbet"),
    ("sohbet", "sohbetgrubutr"),
    ("sohbet", "sohbetmuhabbettr"),
    ("sohbet", "turkiyediyalog"),
    # Borsa candidates
    ("borsa", "KriptoTurkiye"),
    ("borsa", "CoinSohbetTR"),
    ("borsa", "KriptoSozlukTVPiyasaMuhabbeti"),
    ("borsa", "bitgetturkiye"),
    # Teknoloji candidates
    ("haber", "yazilimtoplulugu"),
    ("haber", "linux_tr"),
    ("haber", "yazilim0"),
    ("haber", "yazilimogreniyorumorg"),
]

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    me = await client.get_me()
    print(f"Logged in as @{me.username} ({me.id})", flush=True)

    results = {}

    for cat, g in groups_to_test:
        if cat not in results:
            results[cat] = []
        try:
            entity = await client.get_entity(g)
            if getattr(entity, 'broadcast', False):
                print(f"[{cat}] @{g}: FAIL (Broadcast Channel)", flush=True)
                continue
            
            # Join channel if not already in
            try:
                await client(functions.channels.JoinChannelRequest(channel=entity))
                await asyncio.sleep(1.5)
            except errors.UserAlreadyParticipantError:
                pass
            except Exception as je:
                print(f"[{cat}] @{g}: FAIL (Join error: {type(je).__name__})", flush=True)
                continue

            # Try to send a simple greeting
            msg = await client.send_message(entity, "Selamlar herkese")
            print(f"[{cat}] @{g}: SUCCESS (Message ID: {msg.id})", flush=True)
            results[cat].append(g)
            await asyncio.sleep(2)
            # Delete our test message
            try:
                await client.delete_messages(entity, [msg.id])
            except Exception:
                pass
        except errors.FloodWaitError as fwe:
            print(f"[{cat}] @{g}: FLOODWAIT ({fwe.seconds}s)", flush=True)
            break
        except Exception as e:
            print(f"[{cat}] @{g}: FAIL ({type(e).__name__}: {e})", flush=True)

        await asyncio.sleep(2)

    print("\n=== SUMMARY OF VERIFIED WORKING GROUPS ===", flush=True)
    import json
    print(json.dumps(results, indent=2), flush=True)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
