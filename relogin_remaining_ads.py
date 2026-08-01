import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession


API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
ACCOUNTS = {
    "froxy": "+905015291021",
}


async def wait_for_value(path, seconds=180):
    if os.path.exists(path):
        os.remove(path)
    for _ in range(seconds):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                return value
        await asyncio.sleep(1)
    return ""


async def login(label, phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        print(f"CODE_SENT:{label.upper()}", flush=True)
        code = await wait_for_value(f"code_input_{label}.txt")
        if not code:
            print(f"CODE_TIMEOUT:{label.upper()}", flush=True)
            return

        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=sent.phone_code_hash,
            )
        except SessionPasswordNeededError:
            print(f"PASSWORD_REQUIRED:{label.upper()}", flush=True)
            password = await wait_for_value(f"password_input_{label}.txt")
            if not password:
                print(f"PASSWORD_TIMEOUT:{label.upper()}", flush=True)
                return
            await client.sign_in(password=password)

        me = await client.get_me()
        session = client.session.save()
        with open(f"{label}_session_output.txt", "w", encoding="utf-8") as handle:
            handle.write(session)
        print(f"LOGIN_SUCCESS:{label.upper()}:{me.id}", flush=True)
    except Exception as exc:
        print(f"LOGIN_ERROR:{label.upper()}:{type(exc).__name__}:{exc}", flush=True)
    finally:
        await client.disconnect()


async def main():
    await asyncio.gather(*(login(label, phone) for label, phone in ACCOUNTS.items()))


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    asyncio.run(main())
