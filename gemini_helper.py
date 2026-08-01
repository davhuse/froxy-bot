import urllib.request
import json
import os
import ssl
import random

OPENROUTER_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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"
]

def call_openrouter_api(system_prompt, user_prompt):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5
    }
    
    shuffled_keys = OPENROUTER_KEYS.copy()
    random.shuffle(shuffled_keys)
    
    for key in shuffled_keys:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {key}',
                'HTTP-Referer': 'https://keyvadi.com',
                'X-Title': 'KeyVadi Sales Assistant'
            }
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'choices' in data and data['choices']:
                    text = data['choices'][0]['message']['content'].strip()
                    if text:
                        return text
        except Exception as e:
            pass
            
    return None

def call_pollinations_api(system_prompt, user_prompt):
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "openai"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            res_text = resp.read().decode('utf-8').strip()
            if res_text:
                return res_text
    except Exception as e:
        pass
    return None

def get_ai_response(user_msg, brand, products, api_key=""):
    # Check if AI chat response is enabled in bot_config.json
    try:
        if os.path.exists("bot_config.json"):
            with open("bot_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if not cfg.get("ai_response_enabled", False):
                    return None
    except Exception:
        pass

    prod_lines = []
    for p in products:
        prod_lines.append(f"- Ürün: {p.get('title')}, Fiyat: {p.get('price')}, Link: {p.get('url')}")
    products_context = "\n".join(prod_lines)
    
    brand_prompt = ""
    if brand == "KeyVadi":
        brand_prompt = (
            "Sen KeyVadi markasının yardımsever ve profesyonel satış asistanısın. "
            "Kullanıcıya samimi ama profesyonelce hitap et. Emojileri (🔑, ⚡, ⭐, 💎) dozunda kullan. "
        )
    elif brand == "LisansArena":
        brand_prompt = (
            "Sen LisansArena markasının satış asistanısın. LisansArena'da ödemeler doğrudan IBAN (Havale/EFT) ile alınmaktadır.\n"
            "IBAN: TR570008291009491531109206 | Alıcı: Mahmut Rençber.\n"
            "🔴 ÖNEMLİ KURALLAR: Havale/EFT yapılırken AÇIKLAMA alanı KESİNLİKLE BOŞ BIRAKILMALIDIR!\n"
            "Müşteriye ürün fiyatını ver, ödemeyi bu IBAN'a yapıp dekont fotoğrafını/ekran görüntüsünü bot sohbetine göndermesini söyle."
        )
    else:
        brand_prompt = "Sen yardımsever bir satış asistanısın."

    system_instruction = (
        f"{brand_prompt}\n"
        "GÖREV: Kullanıcının sorusuna doğrudan ve nazikçe cevap ver, listeden uygun ürünü öner ve Shopier satın alma linkini ekle.\n"
        "ÜRÜN KATALOĞU:\n"
        f"{products_context}\n\n"
        "KURALLAR:\n"
        "1. Müşterinin sorusuna samimi ve doğrudan yanıt ver.\n"
        "2. Listedeki en uygun ürünü öner, fiyatını ve satın alma linkini ekle.\n"
        "3. Kendi kendine sistem/güvenlik açıklaması yazma, doğrudan kullanıcıya giden mesajı oluştur."
    )
    
    # Primary: OpenRouter AI (Multi-key auto rotation)
    res = call_openrouter_api(system_instruction, user_msg)
    if res:
        return res
        
    # Secondary Fallback: Pollinations AI
    res2 = call_pollinations_api(system_instruction, user_msg)
    if res2:
        return res2
        
    return None

def get_ad_variation(ad_text, brand, api_key=""):
    system_instruction = (
        f"Sen {brand} markası için Telegram gruplarında yayınlanacak reklam metinlerini düzenleyen bir yapay zekasın.\n"
        "Sana verilen reklam metnini, anlamını, satılan ürünleri, fiyatları ve en önemlisi bot linklerini/kullanıcı adlarını (örn: @KeyVadiSatisBot veya @LisansArenaBot) KESİNLİKLE değiştirmeden, sadece kelime dizilimlerini, cümle yapılarını ve emojileri hafifçe değiştirerek yeniden yaz.\n"
        "Amaç: Telegram'ın spam filtrelerine yakalanmamak için metni çeşitlendirmek.\n"
        "KURALLAR:\n"
        "1. Fiyatları, ürün adlarını ve Telegram bot adreslerini (@...) asla değiştirme veya silme.\n"
        "2. Metni boşluksuz (gereksiz boş satır eklemeden) yap.\n"
        "3. Orijinal metindeki tüm temel bilgileri koru.\n"
        "4. Sadece yeniden yazılmış reklam metnini döndür, açıklama veya ekstra metin ekleme."
    )
    
    res = call_openrouter_api(system_instruction, ad_text)
    if res:
        return res
        
    res2 = call_pollinations_api(system_instruction, ad_text)
    return res2 if res2 else ad_text
