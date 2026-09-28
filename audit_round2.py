import asyncio
import sys
import json
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

MORE_CANDIDATES = {
    "sohbet": [
        "universite_sohbet", "yks_sohbet", "kampus_sohbet", "kpss_sohbet",
        "dizifilmsohbet", "oyunsohbet", "oyuncutoplulugu", "filmsohbet",
        "kitapsohbet", "gencliktoplulugu", "turkiyegencligi", "turkiyediyalog",
        "dostluksohbet", "sohbetalani", "kampuschat", "turkcechatgrubu"
    ],
    "borsa": [
        "kriptoturkiye", "bitgetturkiye", "coinsohbettr", "kriptoist",
        "kriptodunyasi_tr", "borsatradingtr", "kriptoalimsatimtr",
        "btcturkiyesohbet", "kriptotradeturkiye", "kriptosinyal_sohbet"
    ],
    "haber": [
        "yazilimtoplulugu", "linux_tr", "bilgisayarmuhendisleritoplulugu",
        "yapayzekatr", "yapayzekatoplulugu", "yazilimvadisitr",
        "webgelistiricileri", "kodlamatoplulugu", "teknolojidunyasi_sohbet"
    ]
}

BAD_WORDS = ["sikil", "sex", "escort", "kumar", "bahis", "porn", "sabaha kadar", "ifsa", "gay", "+18"]

async def main():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    approved = {}
    
    for cat, list_unames in MORE_CANDIDATES.items():
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
            except Exception:
                pass
            await asyncio.sleep(0.2)
            
    await client.disconnect()
    
    with open("audited_clean_groups_v2.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    print("\n✅ Denetim tamamlandı! 'audited_clean_groups_v2.json' kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())
