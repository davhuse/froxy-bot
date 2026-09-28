import asyncio
import sys
import json
from telethon import TelegramClient, functions
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.sessions import StringSession

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = 31076280
API_HASH = "7ba4072dcf0a05a7ccf80e570866b6d8"

SEARCH_QUERIES = {
    "sohbet": ["sohbet", "muhabbet", "turkce sohbet", "turkiye sohbet", "tanisma sohbet", "sohbet grubu"],
    "borsa": ["kripto sohbet", "borsa sohbet", "kripto turkiye", "kripto yardim", "borsa turkiye"],
    "haber": ["yazilim sohbet", "teknoloji sohbet", "yazilim turkiye", "python turkiye"]
}

BAD_WORDS = ["sikil", "sex", "escort", "kumar", "bahis", "porn", "sabaha kadar", "ifsa", "gay", "+18", "vip grup", "kazan"]

async def find_groups():
    with open("test_account_session_string.txt", "r", encoding="utf-8") as f:
        session_str = f.read().strip()
        
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    print("🚀 TELEGRAM GLOBAL ARAMA & KALİTELİ SÜPERGRUP KEŞFİ BAŞLADI...\n")
    
    discovered = {"sohbet": {}, "borsa": {}, "haber": {}}
    
    for category, queries in SEARCH_QUERIES.items():
        print(f"=== {category.upper()} ARAMALARI ===")
        for q in queries:
            try:
                res = await client(functions.contacts.SearchRequest(q=q, limit=30))
                for chat in res.chats:
                    uname = getattr(chat, 'username', None)
                    if not uname or uname in discovered[category]:
                        continue
                        
                    # Must be megagroup (supergroup), NOT broadcast
                    if getattr(chat, 'broadcast', False) and not getattr(chat, 'megagroup', False):
                        continue
                    if not getattr(chat, 'megagroup', False):
                        continue
                        
                    # Check write permissions
                    banned = getattr(chat, 'default_banned_rights', None)
                    if banned and banned.send_messages:
                        continue
                        
                    title = getattr(chat, 'title', '')
                    if any(bw in title.lower() for bw in BAD_WORDS) or any(bw in uname.lower() for bw in BAD_WORDS):
                        continue
                        
                    # Get member count
                    try:
                        full = await client(GetFullChannelRequest(chat))
                        members = full.full_chat.participants_count
                    except Exception:
                        members = getattr(chat, 'participants_count', 0) or 0
                        
                    if members < 200:  # Minimum 200 members for quality!
                        continue
                        
                    # Check recent messages
                    try:
                        msgs = await client.get_messages(chat, limit=3)
                        if not msgs:
                            continue
                    except Exception:
                        continue
                        
                    print(f"  [{category}] 🌟 @{uname:<22} | Üye: {members:<6} | Başlık: {title}")
                    discovered[category][uname] = {
                        "username": uname,
                        "title": title,
                        "members": members
                    }
                    
            except Exception as se:
                print(f"  Search error for '{q}': {se}")
            await asyncio.sleep(1)
            
    await client.disconnect()
    
    print("\n═══════════════════════════════════════════════════")
    print("🏆 ONAYLANAN KALİTELİ GRUPLAR:")
    print("═══════════════════════════════════════════════════")
    
    final_output = {}
    for cat, group_dict in discovered.items():
        sorted_groups = sorted(group_dict.values(), key=lambda x: x["members"], reverse=True)
        final_output[cat] = sorted_groups
        print(f"\n📂 Kategori: {cat} ({len(sorted_groups)} kaliteli grup)")
        for g in sorted_groups[:15]:
            print(f"   • @{g['username']:<22} | {g['members']:<6} üye | {g['title']}")
            
    with open("high_quality_vetted_groups.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    print("\n✅ 'high_quality_vetted_groups.json' dosyasına kaydedildi!")

if __name__ == "__main__":
    asyncio.run(find_groups())
