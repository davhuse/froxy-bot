import urllib.request
import json
import os
import random

OPENROUTER_KEYS = [
    key.strip()
    for key in os.environ.get("OPENROUTER_API_KEYS", "").split(",")
    if key.strip()
]

def call_openrouter_api(system_prompt, user_prompt):
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
            with urllib.request.urlopen(req, timeout=8) as resp:
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
            "Kart ve Shopier ödemesi yoktur. Ürün fiyatını katalogdan ver; ödeme öncesinde stok teyidi gerektiğini söyle. "
            "IBAN ve müşteriye özel sipariş kodu yalnız botun ürün ödeme ekranında gösterilir. "
            "Dekont banka hareketi manuel kontrol edilmeden ödeme onaylanmaz ve otomatik teslimat yapılmaz."
        )
    else:
        brand_prompt = "Sen yardımsever bir satış asistanısın."

    purchase_task = (
        "GÖREV: Kullanıcının sorusuna doğrudan ve nazikçe cevap ver, listeden uygun ürünü ve fiyatını öner; "
        "ödeme için botun ürün ödeme ekranını kullanmasını söyle. Shopier bağlantısı yazma.\n"
        if brand == "LisansArena" else
        "GÖREV: Kullanıcının sorusuna doğrudan ve nazikçe cevap ver, listeden uygun ürünü öner ve Shopier satın alma linkini ekle.\n"
    )
    product_rule = (
        "2. Listedeki en uygun ürünü ve fiyatını öner; ödeme bağlantısı uydurma."
        if brand == "LisansArena" else
        "2. Listedeki en uygun ürünü öner, fiyatını ve satın alma linkini ekle."
    )
    system_instruction = (
        f"{brand_prompt}\n"
        f"{purchase_task}"
        "ÜRÜN KATALOĞU:\n"
        f"{products_context}\n\n"
        "KURALLAR:\n"
        "1. Müşterinin sorusuna samimi ve doğrudan yanıt ver.\n"
        f"{product_rule}\n"
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
