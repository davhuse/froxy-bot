# -*- coding: utf-8 -*-
import asyncio
import os
import sys
from telethon import TelegramClient

API_ID = int(os.environ.get("TELEGRAM_API_ID", 31076280))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "7ba4072dcf0a05a7ccf80e570866b6d8")
BOT_TOKEN = os.environ.get("JARVIS_BOT_TOKEN", "8940174381:AAE5M4yFbIZ8F5W8dsINCD3tQipHCYgOlzg").strip()
CHANNEL_USERNAME = "JarvisCraftDuyuru"

ANNOUNCEMENT_TEXT = """JARVISCRAFT // RESMI MAGAZA VE OTOMASYON SISTEMI SATISA ACILDI

Degerli kullanicilarimiz ve gelistiriciler,
JarvisCraft dijital urun, yapay zeka asistan ve bot otomasyon ekosistemi resmi olarak satisa acilmistir.

Magazamizda yer alan ana urun ve hizmetler:

1. J.A.R.V.I.S. Sesli Masaustu AI Asistani
Windows bilgisayarinizda sifir kurulumla (.exe) calisan, dogal Turkce sesle yanit veren, Esc tusuyla aninda susturulabilen ve canli web taramasi yapabilen kisisel masaustu asistani.
Ucretsiz PC Demosu: https://bot-service-production-9d74.up.railway.app/static/JARVIS_MUSTERI_DEMO_PAKETI.zip
Lisans Fiyati: 350.00 TL

2. Telegram Oto-Reklam ve Mesaj Botu
65+ onayli ticaret ve sohbet grubunda 7/24 dongulu mesaj motoru. Coklu hesap rotasyonu, akilli anti-flood korumasi ve canli bildirim altyapisi.
Script Paketi: 450.00 TL
Haftalik VIP Uyelik: 150.00 TL
Aylik Sinirsiz VIP Uyelik: 350.00 TL

3. E-Ticaret & Fiyat Takip Scraper Botu
Trendyol, Yemeksepeti ve pazaryerlerinden anlik indirim, kupon ve stok alarmi toplayan scraper seti.
Paket Fiyati: 300.00 TL

4. Full-Stack Mini App + Shopier Kiti
Telegram Mini App magazanizi 10 dakikada kurmanizi saglayan eksiksiz sablon kiti (Flask backend, Vite frontend, Shopier entegrasyonu).
Kit Fiyati: 400.00 TL

5. Ozel Web Sitesi Gelistirme & Kodlama
Kurumsal tanitim, e-ticaret veya landing page projeleriniz icin uctan uca anahtar teslim web yazilim hizmeti.
Taban Baslangic Fiyati: 799.90 TL (Proje kapsamina ve site gereksinimlerine gore degisebilir).

6. Ozel Telegram Bot Yazilimi & Kodlama
Ihtiyaciniza ozel gelistirilen otomasyon, odeme, kanal yonetim veya scraper botu gelistirme hizmeti.
Taban Baslangic Fiyati: 499.90 TL (Islev ve API entegrasyonlarina gore degisebilir).

Guvenli Odeme ve Hizli Teslimat:
Tum siparisler Shopier 3D Secure altyapisi ile guvence altindadir. Satin alim sonrasinda siparis numaranizi botumuz uzerinden girerek uyeliklerinizi aninda aktif edebilirsiniz.

Resmi Telegram Botu: @JarvisCraftsBot
Resmi Shopier Magazasi: https://www.shopier.com/JarvisStore
Resmi Destek Hesabi: @JarvisCraft
Duyuru Kanali: @JarvisCraftDuyuru"""

async def post_announcement():
    print("Connecting bot client...")
    client = TelegramClient("sessions/announcement_sender", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    target = f"@{CHANNEL_USERNAME}"
    print(f"Sending announcement to {target}...")
    try:
        msg = await client.send_message(target, ANNOUNCEMENT_TEXT)
        print(f"Announcement posted successfully! Message ID: {msg.id}")
    except Exception as e:
        print(f"Bot failed to send to channel: {e}")
        print("Attempting with user test session fallback...")
        await client.disconnect()
        
        from telethon.sessions import StringSession
        session_file = "test_account_session_string.txt"
        session_str = None
        if os.path.exists(session_file):
            with open(session_file, "r", encoding="utf-8") as f:
                session_str = f.read().strip()
        if session_str:
            user_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await user_client.connect()
            if await user_client.is_user_authorized():
                msg = await user_client.send_message(target, ANNOUNCEMENT_TEXT)
                print(f"Announcement posted via user session! Message ID: {msg.id}")
            await user_client.disconnect()
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(post_announcement())
