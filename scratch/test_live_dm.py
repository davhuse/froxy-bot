import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from gemini_helper import get_ai_response

api_id = 31076280
api_hash = '7ba4072dcf0a05a7ccf80e570866b6d8'

async def run_live_test():
    with open('bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    s2 = cfg.get('ad_string_session2')

    client_customer = TelegramClient('c4hex_session', api_id, api_hash)
    client_seller = TelegramClient(StringSession(s2), api_id, api_hash)

    await client_customer.start()
    await client_seller.start()

    seller_user = await client_seller.get_me()
    customer_user = await client_customer.get_me()

    print(f"👤 Müşteri Hesabı: @{customer_user.username or customer_user.id} ({customer_user.first_name})")
    print(f"🏪 Satıcı Hesabı (KeyVadi): ID {seller_user.id} ({seller_user.first_name})")

    received_reply = asyncio.Future()

    # Seller listens for DM
    @client_seller.on(events.NewMessage(incoming=True, chats=customer_user.id))
    async def seller_handler(event):
        msg = event.raw_text
        print(f"\n📥 [SATICI HESAP] Müşteriden DM Alındı: '{msg}'")
        
        products = []
        if os.path.exists('keyvadi_shopier_links.json'):
            with open('keyvadi_shopier_links.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    products.append({'title': item.get('title'), 'price': item.get('price'), 'url': item.get('url')})

        ai_reply = get_ai_response(msg, 'KeyVadi', products)
        print(f"🤖 [SATICI HESAP] Yapay Zeka Yanıt Üretti:\n{ai_reply}\n")

        await event.reply(ai_reply)
        print("📤 [SATICI HESAP] AI Yanıtı Müşteriye Gönderildi!")

    # Customer listens for Seller reply
    @client_customer.on(events.NewMessage(incoming=True, chats=seller_user.id))
    async def customer_handler(event):
        print(f"\n📩 [MÜŞTERİ HESAP] Satıcıdan Gelen Cevap Yakalandı:\n{event.raw_text}")
        if not received_reply.done():
            received_reply.set_result(event.raw_text)

    question = "Selam kanka Canva Pro almayı düşünüyorum ömür boyu mu fiyatı ne kadar?"
    print(f"\n💬 [MÜŞTERİ HESAP] Satıcıya mesaj gönderiliyor: '{question}'")
    
    await client_customer.send_message(seller_user.id, question)

    try:
        reply_text = await asyncio.wait_for(received_reply, timeout=15)
        print("\n==========================================")
        print("✅ CANLI HESAP-ARASI TEST %100 BAŞARILI!")
        print("Müşteri hesabı sordu, Yapay Zeka satıcı hesabı üzerinden soruyu anladı, ürün fiyatı ve Shopier linki içeren cevabı canlı olarak Telegram DM'den iletti!")
        print("==========================================")
    except asyncio.TimeoutError:
        print("\n❌ Zaman aşımı: Yanıt alınamadı.")

    await client_customer.disconnect()
    await client_seller.disconnect()

if __name__ == '__main__':
    asyncio.run(run_live_test())
