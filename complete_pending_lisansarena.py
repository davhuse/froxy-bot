"""Complete the pending Telegram login without echoing the 2FA password."""
import asyncio
import getpass
import json
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"
PENDING = Path("pending_login_lisansarena.json")
OUTPUT = Path("session_lisansarena_new.txt")


async def main():
    if not PENDING.exists():
        raise SystemExit("Bekleyen giriş dosyası bulunamadı.")
    data = json.loads(PENDING.read_text(encoding="utf-8"))
    client = TelegramClient(StringSession(data["session_string"]), API_ID, API_HASH)
    await client.connect()
    try:
        password = getpass.getpass("Telegram 2FA parolası (ekranda görünmez): ")
        await client.sign_in(password=password)
        me = await client.get_me()
        OUTPUT.write_text(StringSession.save(client.session), encoding="utf-8")
        print("LOGIN_SUCCESS")
        print("ACCOUNT_ID", me.id)
        print("USERNAME", ("@" + me.username) if me.username else "(yok)")
        print("NAME", ((me.first_name or "") + " " + (me.last_name or "")).strip())
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
