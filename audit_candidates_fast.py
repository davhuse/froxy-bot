import asyncio
import sys
import json
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

CANDIDATES = {
    "sohbet": [
        "kcksohbet", "TurkSohbet", "sohbetvadisi", "muhabbetkosesi",
        "universite_sohbet", "ogrencisohbet", "yardimlasmatr", "yardimlasmavepaylasim",
        "turkiyegenclik", "dostlarkahvesitr", "turkiyediyalogu", "turkceyardim",
        "turkcesohbetgrubuu", "sohbetdostlugu", "muhabbethanetr", "turkiyemuhabbeti"
    ],
    "borsa": [
        "kriptoturkiye", "coinsohbettr", "kriptoturkce", "kriptopara",
        "trbinance", "bybitturkiye", "gateioturkey", "mexc_turkiye",
        "bitgetturkiye", "coinex_turkiye", "btcturksohbet", "kriptotradetr"
    ],
    "haber": [
        "yazilimtoplulugu", "pythontr", "pythonturkiye", "javascript_tr",
        "flutterturkiye", "reactturkiye", "linux_tr", "siberguvenliktr",
        "yazilimgelistiricileri", "turkiyeyazilim"
    ]
}

BAD_WORDS = ["sikil", "sex", "escort", "kumar", "bahis", "porn", "sabaha kadar", "ifsa", "gay", "+18"]

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    approved = {}
    
    for cat, list_unames in CANDIDATES.items():
        approved[cat] = []
        print(f"\n--- {cat.upper()} KONTROL EDİLİYOR ---")
        for u in list_unames:
            try:
                entity = await client.get_entity(u)
                if getattr(entity, 'bot', False):
                    continue
                if getattr(entity, 'broadcast', False) and not getattr(entity, 'megagroup', False):
                    continue
                if not getattr(entity, 'megagroup', False):
                    continue
                    
                banned = getattr(entity, 'default_banned_rights', None)
                if banned and banned.send_messages:
                    continue
                    
                title = getattr(entity, 'title', '')
                if any(bw in title.lower() for bw in BAD_WORDS) or any(bw in u.lower() for bw in BAD_WORDS):
                    continue
                    
                try:
                    full = await client(GetFullChannelRequest(entity))
                    members = full.full_chat.participants_count
                except Exception:
                    members = getattr(entity, 'participants_count', 0) or 0
                    
                if members < 50:
                    continue
                    
                msgs = await client.get_messages(entity, limit=3)
                if not msgs:
                    continue
                    
                print(f"  ✅ [ONAYLANDI] @{u:<22} | {members:<6} üye | {title}")
                approved[cat].append({
                    "username": u,
                    "title": title,
                    "members": members
                })
            except Exception as e:
                pass
            await asyncio.sleep(0.3)
            
    await client.disconnect()
    
    with open("audited_clean_groups.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print("\n✅ Denetim tamamlandı! 'audited_clean_groups.json' kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())
