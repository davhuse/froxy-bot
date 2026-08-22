#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi Telegram Mini App — Bot Entegrasyon Modülü & Rehberi
Bu dosya BotFather üzerinden Mini App menü butonunu ve /start komutundaki WebApp butonlarını yönetir.
"""

# ==========================================
# 1. BOTFATHER ÜZERİNDEN MİNİ APP TANIMLAMA
# ==========================================
# BotFather'a gidip (@BotFather):
# 1. /mybots -> @KeyVadiSatisBot seçin
# 2. "Bot Settings" -> "Menu Button" -> "Configure menu button"
# 3. Mini App URL'nizi girin (Örn: https://keyvadi.onrender.com veya Cloudflare Tünel linki)
# 4. Buton başlığını belirleyin: "🛍️ KeyVadi Mağaza"

# ==========================================
# 2. TELEGRAM BOTU İÇERİSİNDEN WEBAPP BUTONU
# ==========================================

from telethon import Button

def get_keyvadi_miniapp_buttons(web_app_url="https://keyvadi.onrender.com"):
    """
    Kullanıcıya gönderilecek WebApp açılış butonları
    """
    return [
        [
            # WebApp Inline Butonu (Telegram destekleyen istemciler için)
            Button.url("🛍️ KeyVadi Mağazasını Aç (Mini App)", web_app_url)
        ],
        [
            Button.url("💳 Shopier Mağazası", "https://www.shopier.com/keyvadi"),
            Button.url("💬 Canlı Destek", "https://t.me/KeyVadiDestek")
        ]
    ]

START_MESSAGE_MINIAPP = """
🔑 **KeyVadi Premium Hesap & Lisans Mağazasına Hoş Geldiniz!**

Aşağıdaki **"🛍️ KeyVadi Mağazasını Aç"** butonuna basarak tüm ürünlerimizi doğrudan Telegram içindeki modern arayüzden inceleyebilir, bakiye yükleyebilir ve sipariş verebilirsiniz.

⚡ **Özellikler:**
• 7/24 Otomatik Anında Teslimat
• Shopier 3D Secure Güvenli Ödeme
• Arkadaşını Davet Et, Her Siparişten %10 Nakit Kazan!
"""
