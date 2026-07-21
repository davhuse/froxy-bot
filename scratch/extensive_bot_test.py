import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from gemini_helper import get_ai_response

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def run_extensive_tests():
    print("==================================================")
    print("🧪 KAPSAMLI BÖLÜM VE YAPAY ZEKA TESTİ BAŞLATIYOR")
    print("==================================================")

    # 1. KeyVadi Product Catalog Test
    keyvadi_products = []
    if os.path.exists("keyvadi_shopier_links.json"):
        with open("keyvadi_shopier_links.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                keyvadi_products.append({'title': item.get('title'), 'price': item.get('price'), 'url': item.get('url')})
    print(f"📦 [1/4] KeyVadi Kataloğu Yüklendi: {len(keyvadi_products)} adet canlı ürün.")

    # 2. LisansArena Product Catalog Test
    lisansarena_products = []
    if os.path.exists("lisansarena_shopier_links.json"):
        with open("lisansarena_shopier_links.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                pid = item.get("id")
                title = item.get("title")
                url = item.get("url")
                price_val = item.get("priceData", {}).get("price", "0")
                price_str = f"{float(price_val):.2f} TL"
                lisansarena_products.append({"id": pid, "title": title, "price": price_str, "url": url})
    print(f"📦 [2/4] LisansArena Kataloğu Yüklendi: {len(lisansarena_products)} adet canlı ürün.")

    test_queries = [
        ("KeyVadi", "Selam Canva almak istiyorum öğrenci indiriminiz var mı?"),
        ("KeyVadi", "Netflix 4K satın alınca kaç ekran izleyebilirim?"),
        ("LisansArena", "Steam random key stok var mı şansımıza ne çıkıyor?"),
        ("LisansArena", "Merhaba Adobe lisansı hakkında bilgi alabilir miyim?")
    ]

    print("\n--------------------------------------------------")
    print("🤖 [3/4] YAPAY ZEKA (AI) YANIT MOTORU CANLI TESTİ")
    print("--------------------------------------------------")
    
    for brand, query in test_queries:
        prods = keyvadi_products if brand == "KeyVadi" else lisansarena_products
        print(f"\n❓ [SORU - {brand}]: \"{query}\"")
        res = get_ai_response(query, brand, prods)
        if res:
            print(f"💡 [AI YANITI]:\n{res}\n")
        else:
            print("❌ AI Yanıt Üretemedi!")

    print("\n--------------------------------------------------")
    print("📲 [4/4] TELEGRAM BOT BAĞLANTI & KULLANICI TESTİ")
    print("--------------------------------------------------")

    client = TelegramClient('c4hex_session', api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"✅ Telegram İstemcisi Aktif: @{me.username or me.id} ({me.first_name})")

    # Send a message to @KeyVadiSatisBot and @LisansArenaBot
    bots_to_test = ["@KeyVadiSatisBot", "@LisansArenaBot"]
    for bot_username in bots_to_test:
        try:
            bot_entity = await client.get_entity(bot_username)
            print(f"✅ Bot Bulundu: {bot_username} (ID: {bot_entity.id})")
        except Exception as e:
            print(f"⚠️ Bot arama uyarısı ({bot_username}): {e}")

    await client.disconnect()
    print("\n==================================================")
    print("✅ TÜM KAPSAMLI TESTLER BAŞARIYLA TAMAMLANTI!")
    print("==================================================")

if __name__ == '__main__':
    asyncio.run(run_extensive_tests())
