import asyncio
import sys
import json
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

CANDIDATE_POOLS = {
    "sohbet": [
        "turkcesohbetler", "chat_turkiye", "turksohbetgrubu", "sohbetodalari",
        "gencliksohbet", "turkiyediyalog", "turkcechat", "sohbetzamani",
        "muhabbetkulubu", "sohbetdunyasi", "turkiyemuhabbet", "sohbethane",
        "sohbetgrubu", "turkiyediyaloggrubu", "sohbetturkiye"
    ],
    "borsa": [
        "kriptosohbet", "kriptoparatr", "kriptoturkiye", "coinsohbettr",
        "borsasohbet", "kriptoturk", "traderlartr", "kriptoanaliztr",
        "borsatartisma", "coinmuhabbet"
    ],
    "haber": [
        "yazilimtoplulugu", "yazilimcilar", "teknolojisohbet", "yazilimsohbet",
        "turkiyeyazilimcilar", "teknolojigrup", "bilisimsohbet", "yazilimdunyasi"
    ]
}

BAD_WORDS = ["sikil", "sex", "escort", "kumar", "bahis", "porn", "sabaha kadar"]

async def audit():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    print("🔍 GRUP HAVUZLARI DERİN KALİTE DENETİMİ BAŞLADI...\n")
    
    vetted_pools = {}
    
    for category, candidates in CANDIDATE_POOLS.items():
        print(f"━━━━━━━━━━ [{category.upper()}] DENETLENİYOR ━━━━━━━━━━")
        vetted_pools[category] = []
        
        for username in candidates:
            try:
                entity = await client.get_entity(username)
                
                # 1. Must be a channel or supergroup, NOT a private user or bot
                if getattr(entity, 'bot', False):
                    continue
                
                # 2. Must NOT be a read-only broadcast channel
                is_broadcast = getattr(entity, 'broadcast', False)
                is_megagroup = getattr(entity, 'megagroup', False)
                if is_broadcast and not is_megagroup:
                    print(f"  ❌ @{username:<22} -> Yalnızca Duyuru Kanalı (Mesaj yazılamaz)")
                    continue
                
                # 3. Check Default Banned Rights (Can members write?)
                banned_rights = getattr(entity, 'default_banned_rights', None)
                if banned_rights and banned_rights.send_messages:
                    print(f"  ❌ @{username:<22} -> Üye Mesaj Gönderimi Kapalı")
                    continue
                
                # 4. Check Title cleanliness
                title = getattr(entity, 'title', '')
                if any(bw in title.lower() for bw in BAD_WORDS) or any(bw in username.lower() for bw in BAD_WORDS):
                    print(f"  ❌ @{username:<22} -> Uygunsuz/Kalitesiz Başlık: '{title}'")
                    continue
                    
                # 5. Get full info for members count
                try:
                    full = await client(GetFullChannelRequest(entity))
                    members = full.full_chat.participants_count
                except Exception:
                    members = getattr(entity, 'participants_count', 0) or 0
                
                if members < 100:
                    print(f"  ❌ @{username:<22} -> Yetersiz Üye Sayısı: {members}")
                    continue
                
                # 6. Check last 5 messages for recency and activity
                messages = await client.get_messages(entity, limit=5)
                if not messages:
                    print(f"  ❌ @{username:<22} -> Mesaj Geçmişi Yok / Kapalı")
                    continue
                
                print(f"  ✅ @{username:<22} | Üye: {members:<6} | Başlık: {title}")
                vetted_pools[category].append({
                    "username": username,
                    "title": title,
                    "members": members
                })
                
            except Exception as e:
                print(f"  ❌ @{username:<22} -> Hata: {type(e).__name__}")
                
            await asyncio.sleep(0.4)
            
        print()
        
    await client.disconnect()
    
    print("\n═══════════════════════════════════════════════════")
    print("🏆 ONAYLANMIŞ YÜKSEK KALİTELİ GRUP LİSTESİ:")
    print("═══════════════════════════════════════════════════")
    for cat, items in vetted_pools.items():
        print(f"\n📁 Kategori: {cat} ({len(items)} grup)")
        for it in items:
            print(f"   • @{it['username']} ({it['members']} üye) - {it['title']}")
            
    with open("jarvis_vetted_categories.json", "w", encoding="utf-8") as f:
        json.dump(vetted_pools, f, ensure_ascii=False, indent=2)
    print("\n✅ Sonuçlar 'jarvis_vetted_categories.json' dosyasına kaydedildi!")

if __name__ == "__main__":
    asyncio.run(audit())
