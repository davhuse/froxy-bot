import asyncio
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 31076280
api_hash = "7ba4072dcf0a05a7ccf80e570866b6d8"

old_accounts = [
    {
        "name": "Hesap #2 (KeyVadiSatis - Eski)",
        "session": "1AZWarzgBu3nimycUJcGiTa-gMRXl1a_RG4dWoVJZpu3qchcjgH4zR5x2FnS8OFbRCXlZ1dTLjeCBP0rCepRDoLRLCbzoJBgMqAdMUb9EABFMzL8o2TNZxrnIFNQUI4m-pbdT3cHO5t9O7Ts4y4tZLEu9m9VmCh5g4K0vkqL0ezBs4H4OmiKq1pQUoE8Pxubh4X-NTe_rTlk76iaI524KXbuvxLiGnRqnqPIyjibvsMfGWFPBTb9WgoNynaMijjQAorNmHJl0nGpmwQIkCclvOk6iP0cMVlSqm6VBoluBnQ7DJMBmCHOZffyW-r2j6X_VepeJQCjNpTPuEgHMBLIZCYOfn0McO9g=",
    },
    {
        "name": "Hesap #3 (LisansArena - Eski)",
        "session": "1AZWarzMBuxf5pi0qnDE4m_X3vtvYy-Y_a-RRROPx3YfavIpQeDlhKerJ_RRcl1le7CJYwXNPWwJWWMxgE08cSwSxqvcDts_PhqsJeXjQvWo17xdzc5k11mY4_O99DA8VjufYYTMDd5Dhc4v6t3mR_dU1vHM_eEQGvWms4JkX6BcpwZz8Bp5MtXGUEGX8FpD3inFg12hkQt-HOOtoeXKqT096lTPN4Bo9qAfQmkVcTSqL4nMQY8W45sZP_VmoUcnNhhkNvaqD2PQaMleRKFNGx4Zlisbhp36TQQGJCKI28FuNLZ7WT85lijOypQ9XHtsCn0xx771kuqrcjnX7jkK3kC2Gdukl11g=",
    }
]

async def clean_account_messages(acc):
    name = acc["name"]
    print(f"\n[START] [{name}] Baglaniyor...")
    client = TelegramClient(StringSession(acc["session"]), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print(f"[ERR] [{name}] YETKISIZ! Oturum gecersiz.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"[OK] [{name}] Giris basarili. ID: {me.id} | Name: {me.first_name}")

    print(f"[{name}] Gruplar taranıyor, bu islem biraz surebilir...")
    dialogs = await client.get_dialogs()
    
    total_deleted = 0
    for d in dialogs:
        if d.is_group or d.is_channel:
            print(f"[SRC] [{name}] '{d.name}' grubu taranıyor...")
            try:
                # Find all messages sent by "me" in this chat
                msg_ids = []
                async for message in client.iter_messages(d.entity, from_user='me', limit=200):
                    msg_ids.append(message.id)
                
                if msg_ids:
                    print(f"[DEL] [{name}] '{d.name}' grubundan {len(msg_ids)} mesaj siliniyor...")
                    await client.delete_messages(d.entity, msg_ids)
                    total_deleted += len(msg_ids)
            except Exception as e:
                print(f"[WARN] [{name}] '{d.name}' grubunda silme hatası: {e}")
                
    print(f"[PRT] [{name}] Temizlik tamamlandı! Toplam silinen mesaj: {total_deleted}")
    await client.disconnect()

async def main():
    print("=" * 80)
    print("ESKI HESAPLARIN ATTIGI MESAJLARI TEMIZLEME ISLEMI")
    print("=" * 80)
    for acc in old_accounts:
        await clean_account_messages(acc)
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main())
