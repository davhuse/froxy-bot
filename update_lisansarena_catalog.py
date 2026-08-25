#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena Ürün Veritabanı Güncelleyici
Kullanıcının talep ettiği tüm yeni ürünleri, fiyatları, açıklamaları ve
AI ile üretilen özel ürün kartı görsellerini `products_db.json` dosyasına işler.
"""

import json
import os

products = [
    # 1. Netflix & Sinema
    {
        "id": "la_netflix_ortak",
        "title": "Netflix 4K UHD (Ortak Profil)",
        "price": "59,90 TL",
        "price_num": 59.90,
        "category": "cinema",
        "image": "assets/products/la_ai_netflix_4k.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Netflix 4K Ultra HD Ortak Profil. 1 Aylık kesintisiz izleme, anında teslimat.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_netflix_ozel",
        "title": "Netflix 4K UHD (Özel Profil)",
        "price": "84,90 TL",
        "price_num": 84.90,
        "category": "cinema",
        "image": "assets/products/la_ai_netflix_4k.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Netflix 4K Ultra HD Özel Profil. Size özel PIN korumalı profil, 1 Aylık tam garanti.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_prime_ozel",
        "title": "Amazon Prime Video 4K (Özel Profil)",
        "price": "29,90 TL",
        "price_num": 29.90,
        "category": "cinema",
        "image": "assets/products/la_ai_prime_video.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Amazon Prime Video 1 Aylık 4K Ultra HD Özel Profil. Size özel PIN koruması, kesintisiz 1 ay garanti.",
        "showcase": False,
        "is_vitrin": False
    },
    {
        "id": "la_hbo_ozel",
        "title": "HBO Max Özel Plan (1 Aylık Profil)",
        "price": "39,90 TL",
        "price_num": 39.90,
        "category": "cinema",
        "image": "assets/products/la_ai_hbo_max.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "HBO Max Özel Plan 1 Aylık Özel Profil. 4K HDR yayın ve kesintisiz izleme garantisi.",
        "showcase": False,
        "is_vitrin": False
    },
    {
        "id": "la_exxen_3m",
        "title": "Exxen Reklamsız (3 Aylık Kod)",
        "price": "29,90 TL",
        "price_num": 29.90,
        "category": "cinema",
        "image": "assets/products/la_ai_exxen_reklamsiz.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Exxen 3 Aylık Reklamsız Üyelik Kodu. Dizi, film ve özel içerikler. Daha önce üyelik/kod kullanılmamış hesaplarda geçerlidir.",
        "showcase": True,
        "is_vitrin": True
    },

    # 2. Spotify & YouTube (Müzik / Medya)
    {
        "id": "la_spotify_3m",
        "title": "Spotify Premium (3 Aylık Kod)",
        "price": "19,90 TL",
        "price_num": 19.90,
        "category": "social",
        "image": "assets/products/la_ai_spotify_premium.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Spotify sizin insan olduğunuzu doğrulama amaçlı kartınızdan 1 aylık ücreti çekip 3 Ay kullanım süresi sunmaktadır.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_spotify_4m",
        "title": "Spotify Premium (4 Aylık Kod)",
        "price": "39,90 TL",
        "price_num": 39.90,
        "category": "social",
        "image": "assets/products/la_ai_spotify_premium.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Spotify 4 Aylık Bireysel Premium Aktivasyon Kodu. Daha önce premium alınmamış (yeni) hesaplarda geçerlidir.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_youtube_3m",
        "title": "YouTube Premium (3 Aylık Kod)",
        "price": "39,90 TL",
        "price_num": 39.90,
        "category": "social",
        "image": "assets/products/la_ai_youtube_premium.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "YouTube Premium 3 Aylık Aktivasyon Kodu. Reklamsız video ve YouTube Music. Daha önce premium alınmamış hesaplarda geçerlidir.",
        "showcase": True,
        "is_vitrin": True
    },

    # 3. Steam Random Keys & Gaming
    {
        "id": "la_steam_200",
        "title": "Steam 200$ Değerinde Random Key",
        "price": "39,90 TL",
        "price_num": 39.90,
        "category": "gaming",
        "image": "assets/products/la_ai_steam_random.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Steam mağaza değeri en az 200$ (Dolar) olan garantili oyun anahtarı. Global ve süresiz.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_steam_45",
        "title": "Steam 45$ Değerinde Random Key",
        "price": "19,90 TL",
        "price_num": 19.90,
        "category": "gaming",
        "image": "assets/products/la_ai_steam_random.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Steam mağaza değeri en az 45$ (Dolar) olan garantili oyun anahtarı. Global ve anında teslim.",
        "showcase": True,
        "is_vitrin": True
    },

    # 4. Minecraft Pelerinleri (Capes)
    {
        "id": "la_mc_builder",
        "title": "Minecraft Builder Pelerini Keyi",
        "price": "8,00 TL",
        "price_num": 8.00,
        "category": "gaming",
        "image": "assets/products/la_ai_minecraft_capes.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Minecraft Resmi Builder Cape Aktivasyon Kodu. Microsoft / Minecraft hesabınızda kalıcı olarak aktif olur.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_mc_home",
        "title": "Minecraft Home Pelerini Keyi",
        "price": "10,00 TL",
        "price_num": 10.00,
        "category": "gaming",
        "image": "assets/products/la_ai_minecraft_capes.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Minecraft Resmi Home Cape Aktivasyon Kodu. Kalıcı pelerin, anında teslimat.",
        "showcase": False,
        "is_vitrin": False
    },
    {
        "id": "la_mc_copper",
        "title": "Minecraft Copper Pelerini Keyi",
        "price": "15,00 TL",
        "price_num": 15.00,
        "category": "gaming",
        "image": "assets/products/la_ai_minecraft_capes.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Minecraft Resmi Copper (Bakır) Cape Aktivasyon Kodu. Hesabınıza özel kalıcı pelerin.",
        "showcase": False,
        "is_vitrin": False
    },
    {
        "id": "la_mc_purple_heart",
        "title": "Minecraft Purple Heart Cape Key",
        "price": "315,00 TL",
        "price_num": 315.00,
        "category": "gaming",
        "image": "assets/products/la_ai_minecraft_capes.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Nadir Minecraft Purple Heart Cape (Twitch Özel Koleksiyon) Aktivasyon Kodu. Hesabınızda kalıcı.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_roblox_5offsale",
        "title": "5 Adet Offsale Roblox Hesap Paketi",
        "price": "29,90 TL",
        "price_num": 29.90,
        "category": "gaming",
        "image": "assets/products/la_ai_roblox_offsale.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "5 Adet Nadir Offsale ve Vintage Eşyalı Roblox Hesap Paketi. 7 Gün Değişim Garantilidir.",
        "showcase": True,
        "is_vitrin": True
    },

    # 5. Tasarım & Edit (CapCut, Envato, Freepik, Adobe, Canva)
    {
        "id": "la_capcut_kisisel",
        "title": "CapCut Pro (1 Aylık Kişisel)",
        "price": "179,90 TL",
        "price_num": 179.90,
        "category": "design",
        "image": "assets/products/la_ai_capcut_pro.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "CapCut Pro 1 Aylık Kişisel Hesap / Yetkilendirme. Tüm Pro video efektleri, 4K render ve yapay zeka araçları aktif.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_capcut_ortak",
        "title": "CapCut Pro (1 Aylık Ortak)",
        "price": "69,90 TL",
        "price_num": 69.90,
        "category": "design",
        "image": "assets/products/la_ai_capcut_pro.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "CapCut Pro 1 Aylık Ortak Kullanım. Pro şablonlar, efektler ve AI düzenleme özellikleri.",
        "showcase": False,
        "is_vitrin": False
    },
    {
        "id": "la_envato_kisisel",
        "title": "Envato Elements (1 Aylık Kişisel)",
        "price": "89,90 TL",
        "price_num": 89.90,
        "category": "design",
        "image": "assets/products/la_ai_envato_elements.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Envato Elements 1 Aylık Kişisel Hesap. Milyonlarca tema, grafik, video, ses ve şablonu sınırsız indirin.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_freepik_kisisel",
        "title": "Freepik Premium (1 Aylık Kişisel)",
        "price": "89,90 TL",
        "price_num": 89.90,
        "category": "design",
        "image": "assets/products/la_ai_freepik_premium.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Freepik Premium 1 Aylık Kişisel Hesap. Sınırsız vektör, PSD, stok fotoğraf ve yapay zeka görsel araçları.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_adobe_cc_1m",
        "title": "Adobe Creative Cloud (1 Aylık)",
        "price": "149,90 TL",
        "price_num": 149.90,
        "category": "design",
        "image": "assets/products/la_ai_adobe_creative.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Adobe Creative Cloud 1 Aylık Tüm Uygulamalar. Promosyon linki iletilir.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_canva_ogretmen",
        "title": "Canva Pro Öğretmen (1 Yıllık)",
        "price": "99,90 TL",
        "price_num": 99.90,
        "category": "design",
        "image": "assets/products/la_ai_canva_pro.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Canva Pro Öğretmen 1 Yıllık Lisans. Kendi mailinize tanımlanır, sınıf açma ve öğrenci davet yetkisi içerir.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_canva_ogrenci",
        "title": "Canva Pro Öğrenci (1 Yıllık)",
        "price": "49,90 TL",
        "price_num": 49.90,
        "category": "design",
        "image": "assets/products/la_ai_canva_pro.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Canva Pro 1 Yıllık Öğrenci Üyeliği. Kişisel hesabınıza tanımlanır, tüm Pro şablon ve tasarım araçları açıktır.",
        "showcase": False,
        "is_vitrin": False
    },

    # 6. Yazılım & Lisans (Office 365, Windows)
    {
        "id": "la_office365",
        "title": "Office 365 Pro Plus Kişisel Hesap",
        "price": "69,90 TL",
        "price_num": 69.90,
        "category": "software",
        "image": "assets/products/la_ai_office365.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Microsoft Office 365 Pro Plus Kişisel Hesap. 1TB OneDrive Cloud Depolama, Word, Excel, PowerPoint. 5 Cihaz destekli.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_windows_pro",
        "title": "Windows 10 / 11 Pro Orijinal Lisans Key",
        "price": "49,90 TL",
        "price_num": 49.90,
        "category": "software",
        "image": "assets/products/la_ai_windows_pro.jpg",
        "badge": "💎 Arena VIP",
        "url": "",
        "description": "Etkinleştirilmemiş cihazları etkinleştirir. 1 Ay Garantili. 32/64 Bit tüm sürümlerle tam uyumlu orijinal dijital anahtar.",
        "showcase": True,
        "is_vitrin": True
    },

    # 7. Sosyal Medya & Hesaplar
    {
        "id": "la_ig_1000",
        "title": "Instagram 1000 Takipçi (30 Gün Garanti)",
        "price": "49,90 TL",
        "price_num": 49.90,
        "category": "social",
        "image": "assets/products/la_ai_instagram_followers.jpg",
        "badge": "🚀 Popüler",
        "url": "",
        "description": "Instagram 1000 Takipçi Gönderimi. 30 Gün Düşüş Garantili ve Otomatik Telafili. Şifresiz, sadece kullanıcı adı gereklidir.",
        "showcase": True,
        "is_vitrin": True
    },
    {
        "id": "la_gmail_garantili",
        "title": "Gmail Hesap (3 Gün Garantili)",
        "price": "49,90 TL",
        "price_num": 49.90,
        "category": "social",
        "image": "assets/products/la_ai_gmail_account.jpg",
        "badge": "⚡ Orijinal",
        "url": "",
        "description": "Onaylı ve kaliteli Gmail hesabı. 3 Gün Telafi ve Giriş Garantisi mevcuttur.",
        "showcase": False,
        "is_vitrin": False
    }
]

target_file = "miniapp_lisansarena/products_db.json"
with open(target_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"Toplam {len(products)} adet LisansArena ürünü '{target_file}' dosyasına başarıyla kaydedildi.")
