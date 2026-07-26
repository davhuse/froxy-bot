"""KeyVadi reklam hesabi icin yeni StringSession uretir.

Eski anahtarlarin hepsi AuthKeyDuplicatedError ile olmus durumda: ayni anahtar
lokalden ve Render'dan ayni anda kullanilinca Telegram onu kaliciolarak iptal
ediyor.  Bu script yeni anahtari uretir, dogru hesaba ait oldugunu dogrular ve
bot_config.json'a YAZMAZ -- boylece anahtar yanlislikla lokalde de calisip
tekrar iptal edilmez.

Kullanim:
    python keyvadi_oturum_yenile.py                  # numarayi sorar
    python keyvadi_oturum_yenile.py +905xxxxxxxxx    # numarayi arguman olarak alir

Telefon numarasi bilerek dosyaya gomulmedi; repo herkese acik oldugu icin
numara komut satirindan veriliyor.

Sonrasinda cikan anahtari Render > Environment > AD_STRING_SESSION_KEYVADI
degerine yapistirip deploy edin.
"""

import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

# Reklam botunun allowlist'i (otomatik_katil.py ACTIVE_ACCOUNT_USERNAMES) bu
# kullanici adini bekliyor; farkli bir hesaba giris yapilirsa bot session'i
# baglamadan kapatir, o yuzden burada pesinen uyariyoruz.
BEKLENEN_KULLANICI_ADI = 'keyvadionline'
ENV_DEGISKENI = 'AD_STRING_SESSION_KEYVADI'


async def main():
    print("KeyVadi Reklam Hesabi - Yeni Oturum Anahtari")
    print("=" * 60)
    print("Bu anahtar SADECE Render'da kullanilmalidir.")
    print("Ayni anahtari lokalde de calistirirsaniz Telegram iptal eder.")
    print("=" * 60)

    phone = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    if phone:
        print(f"Telefon (argumandan): {phone}")
    else:
        phone = input("KeyVadiOnline telefon numarasi (ornek +905xxxxxxxxx): ").strip()
    if not phone:
        print("Telefon numarasi bos, cikiliyor.")
        return

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    try:
        sent = await client.send_code_request(phone)
        code = input("Telegram'dan gelen dogrulama kodu: ").strip()
        try:
            await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            pw = input("Iki adimli dogrulama (2FA) sifresi: ").strip()
            await client.sign_in(password=pw)

        me = await client.get_me()
        username = (getattr(me, 'username', '') or '').lower()
        session_str = client.session.save()

        print()
        print("Giris basarili.")
        print(f"  Hesap : {me.first_name} (@{me.username})")
        print(f"  ID    : {me.id}")

        if username != BEKLENEN_KULLANICI_ADI:
            print()
            print(f"  !! UYARI: Beklenen kullanici adi @{BEKLENEN_KULLANICI_ADI}, ")
            print(f"     giris yapilan hesap @{username or 'bilinmiyor'}.")
            print("     Reklam botu bu hesabi allowlist disinda sayip baglantiyi kapatir.")
            print("     Dogru numarayla tekrar deneyin.")

        print()
        print("-" * 60)
        print(f"{ENV_DEGISKENI} degerine yapistirilacak anahtar:")
        print()
        print(session_str)
        print()
        print("-" * 60)
        print("Adimlar:")
        print("  1) Render > froxy-bot > Environment")
        print(f"  2) {ENV_DEGISKENI} degiskenini olusturun/guncelleyin")
        print("  3) Save changes -> otomatik deploy")
        print("  4) https://froxy-bot.onrender.com/api/status adresinde")
        print("     ad_accounts icinde KeyVadiOnline gorunmeli")
        print()
        print("Anahtar bilerek bot_config.json'a yazilmadi; lokalde kullanmayin.")

    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
