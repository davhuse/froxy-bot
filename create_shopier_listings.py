import os
import sys
import time
import subprocess
import psutil
import urllib.request
import ssl
import re
import html

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import builtins
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    msg = " ".join(str(a) for a in args)
    builtins.print(*args, **kwargs)
    try:
        with open("shopier_upload_log.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass



def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"[{package}] bulunamadi, yukleniyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Gerekli kutuphaneleri kontrol et ve yukle
install_and_import("selenium")
install_and_import("webdriver_manager")
install_and_import("pillow")
install_and_import("undetected-chromedriver")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from PIL import Image, ImageDraw, ImageFont

# 33 Products list from database
products = [
    # EGLENCE & MUZIK
    {"name": "YouTube Premium (3 Aylık Kod)", "price": 44.99, "category": "Entertainment", "desc": "YouTube Premium 3 Aylık Aktivasyon Kodu. Reklamsız video izleme ve YouTube Music Premium dahildir. UYARI: Yeni hesaplarda veya daha önce Premium alınmamış hesaplarda aktifleştirilmelidir."},
    {"name": "Spotify Premium (4 Aylık Kod)", "price": 34.99, "category": "Entertainment", "desc": "Spotify Premium 4 Aylık Aktivasyon Kodu. Kendi kişisel hesabınıza tanımlanır. Reklamsız ve yüksek kaliteli müzik keyfi. UYARI: Daha önce Premium üyeliği aktif edilmemiş (yeni/bireysel) hesaplarda geçerlidir."},
    {"name": "Netflix 4K Ultra HD (Kişisel Profil)", "price": 89.99, "category": "Entertainment", "desc": "Kişisel Netflix 4K Ultra HD Profili. Ortak hesapta size ait özel profil ve şifreleme ile full garanti sağlanır."},
    {"name": "Exxen Reklamsız (3 Aylık)", "price": 34.99, "category": "Entertainment", "desc": "Exxen Reklamsız 3 Aylık Üyelik. Giriş bilgileri sipariş sonrasında teslim edilir."},
    {"name": "Crunchyroll Premium (3 Aylık)", "price": 99.00, "category": "Entertainment", "desc": "Crunchyroll Premium 3 Aylık Üyelik."},

    # YAPAY ZEKA (AI)
    {"name": "ChatGPT Plus (1 Aylık Hesap)", "price": 199.99, "category": "AI", "desc": "ChatGPT Plus 1 Aylık Kullanım Hesabı. Gelişmiş GPT-4o ve DALL-E görsel üretim özellikleri aktiftir. Giriş garantisi ve 3 gün garanti sağlanır."},
    {"name": "Gemini Pro (1 Yıllık Hesap)", "price": 299.99, "category": "AI", "desc": "Gemini Pro 1 Yıllık Kullanım Hesabı. Gelişmiş Google AI asistanına kesintisiz erişim. Giriş garantilidir."},
    {"name": "Gemini Pro (Davet Linki)", "price": 124.99, "category": "AI", "desc": "Gemini Pro Davet Linki ile kendi hesabınızı aktifleştirme. Giriş garantilidir."},
    {"name": "Gemini Ultra (Davet Linki)", "price": 399.99, "category": "AI", "desc": "Gemini Ultra Davet Linki. Google'ın en gelişmiş yapay zeka modeli. Full kullanım garantisi sağlanır."},
    {"name": "Gemini Ultra (2.5k Kredili Hesap)", "price": 599.99, "category": "AI", "desc": "Gemini Ultra 2500 Kredili Kullanım Hesabı. Full kullanım garantisi sağlanır."},
    {"name": "Super Grok (1 Aylık Hesap)", "price": 449.99, "category": "AI", "desc": "Super Grok 1 Aylık Kullanım Hesabı. Giriş garantilidir."},
    {"name": "Super Grok (3 Aylık Hesap)", "price": 949.99, "category": "AI", "desc": "Super Grok 3 Aylık Kullanım Hesabı. 15 gün kullanım garantisi sağlanır."},
    {"name": "Super Grok (6 Aylık Hesap)", "price": 1499.99, "category": "AI", "desc": "Super Grok 6 Aylık Kullanım Hesabı. 3 hafta kullanım garantisi sağlanır."},
    {"name": "Super Grok (12 Aylık Hesap)", "price": 2299.99, "category": "AI", "desc": "Super Grok 12 Aylık Kullanım Hesabı. 3 ay kullanım garantisi sağlanır."},
    {"name": "Gamma Ultra (1 Aylık Hesap)", "price": 449.99, "category": "AI", "desc": "Gamma Ultra 1 Aylık Kullanım Hesabı. Yapay zeka ile sunum ve döküman oluşturma."},
    {"name": "Gamma Pro (1 Aylık Hesap)", "price": 299.99, "category": "AI", "desc": "Gamma Pro 1 Aylık Kullanım Hesabı."},

    # DIJITAL ARACLAR & YAZILIMLAR
    {"name": "Canva Pro (1 Yıllık Yetki)", "price": 79.99, "category": "Design", "desc": "Canva Pro 1 Yıllık Yetkilendirme. Kendi kişisel hesabınıza Pro özellikleri tanımlanır."},
    {"name": "Adobe Express (3 Aylık)", "price": 99.99, "category": "Design", "desc": "Adobe Express 3 Aylık Pro Üyelik. Kendi hesabınıza tanımlanır. 1 hafta garanti sağlanır."},
    {"name": "Adobe Creative Cloud (1 Haftalık)", "price": 69.99, "category": "Design", "desc": "Adobe Creative Cloud Tüm Uygulamalar 1 Haftalık Üyelik. 1 hafta garanti sağlanır."},
    {"name": "Adobe Creative Cloud (1 Aylık)", "price": 119.99, "category": "Design", "desc": "Adobe Creative Cloud Tüm Uygulamalar 1 Aylık Üyelik. 1 hafta garanti sağlanır."},
    {"name": "Adobe Creative Cloud (4 Aylık)", "price": 249.99, "category": "Design", "desc": "Adobe Creative Cloud Tüm Uygulamalar 4 Aylık Üyelik. 1 hafta garanti sağlanır."},
    {"name": "CapCut Pro (1 Haftalık Hesap)", "price": 99.99, "category": "Design", "desc": "CapCut Pro 1 Haftalık Kullanım Hesabı. 3 gün kullanım garantisi sağlanır."},
    {"name": "Kiro (10k Kredili Hesap)", "price": 499.99, "category": "Design", "desc": "Kiro 10.000 Kredili Görsel ve Video Üretim Hesabı. Giriş garantilidir."},
    {"name": "Duolingo Super Sınırsız", "price": 69.99, "category": "Design", "desc": "Duolingo Super Sınırsız Dil Eğitimi."},
    {"name": "Scribd Premium (3 Aylık)", "price": 99.99, "category": "Design", "desc": "Scribd Premium 3 Aylık Üyelik."},
    {"name": "TradingView Premium (3 Aylık)", "price": 349.99, "category": "Design", "desc": "TradingView Premium 3 Aylık Erişim. Sınırsız grafik ve indikatör yerleşimi."},

    # ONAYLI NUMARA & MAIL
    {"name": "ABD / Kanada Karma WhatsApp Numarası", "price": 149.99, "category": "Numbers", "desc": "ABD / Kanada Karma WhatsApp Onaylı Numara."},
    {"name": "Türk Apple ID (iCloud Etkin)", "price": 149.99, "category": "Numbers", "desc": "Türk Apple ID iCloud Etkinleştirilmiş Hesap. Giriş garantilidir."},
    {"name": "Eski Tarihli Gmail (2022-2024 Kurulu)", "price": 59.99, "category": "Numbers", "desc": "Eski Tarihli Kurulmuş Gmail Hesabı. Giriş garantilidir."},

    # KUPON & INDIRIMLER
    {"name": "Trendyol Go Yemek İndirim Kuponu (700 TL'ye 250 TL)", "price": 49.99, "category": "Coupons", "desc": "Trendyol Go Yemek siparişinde 700 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon."},
    {"name": "Trendyol Go Market İndirim Kuponu (900 TL'ye 250 TL)", "price": 49.99, "category": "Coupons", "desc": "Trendyol Go Market siparişinde 900 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon."},
    {"name": "Uber Eats Yemek İndirim Kuponu (700 TL'ye 250 TL)", "price": 49.99, "category": "Coupons", "desc": "Uber Eats Yemek siparişinde 700 TL'ye 250 TL Net indirim sağlayan tek kullanımlık kupon."},
    {"name": "Shell 75 TL Akaryakıt Puanı", "price": 14.99, "category": "Coupons", "desc": "Shell istasyonlarında geçerli 75 TL değerinde akaryakıt puanı."},

    # LISANSLAR, AI & PROGRAMLAR (YENI EKLENENLER)
    {"name": "Windows 10/11 Pro Lisans Anahtarı (Key)", "price": 70.00, "category": "Design", "desc": "Windows 10/11 Professional işletim sistemi için %100 orijinal ve süresiz aktivasyon lisans anahtarı. 7/24 anında otomatik teslimat."},
    {"name": "Microsoft Office 365 (1 Yıllık Hesap)", "price": 70.00, "category": "Design", "desc": "Word, Excel, PowerPoint ve tüm Office uygulamalarını içeren 1 Yıllık lisanslı Microsoft Office 365 hesabı. 7/24 anında teslimat."},
    {"name": "Semrush Pro (14 Günlük Hesap)", "price": 150.00, "category": "AI", "desc": "Semrush Pro özellikleri aktif 14 günlük profesyonel SEO ve arama motoru analiz hesabı. Giriş garantili."},
    {"name": "Steam İstediğiniz Oyun (Hediye/Hesap)", "price": 60.00, "category": "Entertainment", "desc": "Steam platformundaki dilediğiniz 60 TL değerindeki oyunu hediye olarak veya özel hesap şeklinde teslim alabilirsiniz."},
    {"name": "XBOX Game Pass Ultimate (3 Aylık Üyelik)", "price": 80.00, "category": "Entertainment", "desc": "3 Aylık XBOX Game Pass Ultimate üyeliği aktif ortak hesap. PC ve konsolda yüzlerce oyuna ücretsiz erişim sağlar. UYARI: Ortak hesaptır."},
    {"name": "NordVPN Premium (1 Aylık Hesap)", "price": 49.99, "category": "Design", "desc": "NordVPN Premium 1 aylık yüksek hızlı ve güvenli VPN hesabı. Giriş garantilidir."},
    {"name": "Kaspersky Total Security (1 Yıllık Lisans)", "price": 79.99, "category": "Design", "desc": "Kaspersky Total Security en üst düzey koruma sağlayan 1 yıllık orijinal antivirüs lisansı."},
    {"name": "Envato Elements (1 Aylık Premium Hesap)", "price": 149.99, "category": "Design", "desc": "Envato Elements üzerinden sınırsız şablon, görsel ve kod kütüphanesine erişebileceğiniz 1 aylık Premium hesap."},
    {"name": "Freepik Premium (1 Aylık Hesap)", "price": 99.99, "category": "Design", "desc": "Freepik Premium özellikli 1 aylık tasarım ve vektör indirme hesabı."},
    {"name": "Autodesk AutoCAD (1 Yıllık Öğrenci Lisansı)", "price": 199.99, "category": "Design", "desc": "Autodesk AutoCAD 1 yıllık orijinal lisans anahtarı. Kendi hesabınıza tanımlanabilir."},
    {"name": "Figma Professional (1 Yıllık Yetkilendirme)", "price": 129.99, "category": "Design", "desc": "Figma Professional sürümüne sahip 1 yıllık yetki daveti. Kendi hesabınızda sınırsız proje alanı açar."},
    {"name": "WordPress Elementor Pro (1 Yıllık Lisans)", "price": 99.99, "category": "Design", "desc": "WordPress için Elementor Pro sayfa oluşturucu eklentisinin 1 yıllık orijinal lisans anahtarı."},
    {"name": "Grammarly Premium (1 Aylık Hesap)", "price": 69.99, "category": "Design", "desc": "Yazım ve dilbilgisi kontrolü için Grammarly Premium 1 aylık kullanım hesabı."},
    {"name": "DeepL Pro Çeviri (1 Aylık Hesap)", "price": 89.99, "category": "AI", "desc": "DeepL Pro çeviri servisi için 1 aylık premium erişim hesabı. Belgelerinizi sınırsız çevirin."},
    {"name": "Ideogram AI Premium (1 Aylık Hesap)", "price": 119.99, "category": "AI", "desc": "Gelişmiş metinli görsel üretici Ideogram AI premium özellikli 1 aylık kullanım hesabı."},
    {"name": "Quillbot Premium (1 Aylık Hesap)", "price": 49.99, "category": "AI", "desc": "Metin yeniden yazma ve özetleme aracı Quillbot Premium 1 aylık kullanım hesabı."},
    {"name": "HBO Max 1 Aylık Profil", "price": 39.90, "category": "Entertainment", "desc": "HBO Max 1 Aylık Premium Profil. Size özel profil ismi ve şifreleme sağlanır."},
    {"name": "Prime Video (1 Aylık) - Özel Profil", "price": 29.90, "category": "Entertainment", "desc": "Amazon Prime Video 1 Aylık Kişisel Profil. Özel şifreli profil ile kesintisiz izleme."},
    {"name": "Prime Video (1 Aylık) - Ortak Profil", "price": 19.90, "category": "Entertainment", "desc": "Amazon Prime Video 1 Aylık Ortak Kullanım Hesabı. Giriş garantilidir."}
]

def create_gradient_image(title, category, filename):
    w, h = 800, 800
    
    if category == "AI":
        c1, c2 = (24, 18, 59), (89, 56, 172)
        cat_turkish = "YAPAY ZEKA (AI)"
    elif category == "Entertainment":
        c1, c2 = (60, 6, 6), (180, 20, 20)
        cat_turkish = "EGELENCE & MUZIK"
    elif category == "Design":
        c1, c2 = (10, 48, 70), (25, 120, 160)
        cat_turkish = "TASARIM & YAZILIM"
    elif category == "Numbers":
        c1, c2 = (15, 60, 40), (45, 150, 90)
        cat_turkish = "ONAYLI NUMARA & MAIL"
    elif category == "Coupons":
        c1, c2 = (80, 45, 10), (190, 120, 30)
        cat_turkish = "KUPON & INDIRIM"
    else:
        c1, c2 = (30, 30, 30), (80, 80, 80)
        cat_turkish = "DIJITAL URUN"
        
    base = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(base)
    
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
        
    card_margin = 85
    draw.rounded_rectangle(
        [(card_margin, card_margin), (w - card_margin, h - card_margin)],
        radius=35,
        fill=(0, 0, 0, 110),
        outline=(255, 255, 255, 35),
        width=3
    )
    
    font_path = "arial.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 38)
        font_sub = ImageFont.truetype(font_path, 23)
        font_badge = ImageFont.truetype(font_path, 17)
    except IOError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    draw.text((w/2, 170), cat_turkish, font=font_badge, fill=(200, 220, 255), anchor="mm")
    
    words = title.split()
    lines = []
    current_line = []
    for word in words:
        if len(" ".join(current_line + [word])) * 17 < (w - card_margin * 3.5):
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_text = 360 - (len(lines) - 1) * 25
    for line in lines[:3]:
        draw.text((w/2, y_text), line, font=font_title, fill=(255, 255, 255), anchor="mm")
        y_text += 55
        
    draw.text((w/2, 595), "ANINDA DIJITAL TESLIMAT", font=font_sub, fill=(160, 255, 160), anchor="mm")
    draw.text((w/2, 635), "GUVENLI ODEME | %100 GARANTILI", font=font_sub, fill=(225, 225, 225), anchor="mm")
    
    base.save(filename, "JPEG", quality=90)

def get_existing_products_selenium(driver):
    print("Mevcut Shopier urunleri tarayicidan taranıyor (https://www.shopier.com/keyvadi)...")
    existing_titles = set()
    try:
        # Save current URL
        original_url = driver.current_url
        
        # Navigate to the public showroom inside the active session
        driver.get("https://www.shopier.com/keyvadi")
        time.sleep(4) # Wait for page load
        
        elements = driver.find_elements(By.CLASS_NAME, "shopier-store--store-product-card-title")
        for el in elements:
            title = el.text.strip()
            if title:
                existing_titles.add(title.lower().strip())
                
        print(f"Dukkaninizda toplam {len(existing_titles)} adet mevcut urun tespit edildi.")
        
        # Restore URL
        driver.get(original_url)
    except Exception as e:
        print(f"Mevcut urunleri tararken hata olustu (atlanıyor): {e}")
    return existing_titles

def safe_send_keys(driver, element_id, text, wait=None):
    if wait:
        el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    else:
        el = driver.find_element(By.ID, element_id)
        
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    time.sleep(0.3)
    driver.execute_script("arguments[0].value = '';", el)
    time.sleep(0.2)
    
    try:
        # First try normal send_keys
        wait_click = WebDriverWait(driver, 2)
        el_clickable = wait_click.until(EC.element_to_be_clickable((By.ID, element_id)))
        el_clickable.send_keys(text)
    except Exception as e:
        print(f"Normal typing failed for {element_id}, trying JS fallback...")
        driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """, el, text)

def main():
    print("=" * 60)
    print("SHOPIER OTOMATIK ILAN YUKLEME BOTU (AI GORSELLER)")
    print("=" * 60)
    
    img_dir = os.path.join(os.getcwd(), "shopier_ai_images")
    if not os.path.exists(img_dir):
        print(f"Hata: {img_dir} klasoru bulunamadi! Lutfen once gorselleri uretin.")
        sys.exit(1)
        
    print("\n[1] AI uretimi gorseller hazir olarak algilandi.")
    
    print("\n[2] Tarayici baslatiliyor...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    
    # Auto-detect Chrome version on Windows
    main_version = None
    try:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            if version:
                main_version = int(version.split(".")[0])
        except Exception:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome")
            version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            if version:
                main_version = int(version.split(".")[0])
    except Exception as ev:
        print(f"Chrome surumu kayit defterinden okunamadi: {ev}")

    if main_version:
        print(f"Tespit edilen Chrome Ana Surumu: {main_version}")
    else:
        print("Chrome ana surumu tespit edilemedi, varsayilan kullanilacak.")
    
    try:
        if main_version:
            driver = uc.Chrome(options=options, version_main=main_version)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        print(f"Hata: Tarayici baslatilamadi! Hata: {e}")
        # Try fallback to hardcoded version 149 if it fails
        if main_version != 149:
            print("149. surum ile tekrar deneniyor...")
            try:
                driver = uc.Chrome(options=options, version_main=149)
            except Exception as e2:
                print(f"Yedek deneme de basarisiz oldu: {e2}")
                sys.exit(1)
        else:
            sys.exit(1)

        
    print("Basarili: Chrome baglantisi kuruldu.")
    
    # Go to shopier immediately to let user log in
    driver.get("https://www.shopier.com/m/products.php")
    
    print("Lutfen acilan tarayici penceresinde Shopier hesabiniza giris yapin...")
    
    # Wait for user login
    while True:
        current_url = driver.current_url
        if "login" not in current_url and "index.php" not in current_url:
            break
        time.sleep(2)
        
    print("Giris yapildi! Dukkaninizdaki mevcut urunler taranıyor...")
    
    # Get existing products to prevent duplicates
    existing_titles = get_existing_products_selenium(driver)
    
    # Filter products
    filtered_products = []
    for orig_idx, p in enumerate(products):
        if p["name"].lower().strip() in existing_titles:
            print(f"[-] Urun zaten dukkaninizda var, yuklenmeyecek: {p['name']}")
        else:
            p_copy = p.copy()
            p_copy["orig_idx"] = orig_idx
            filtered_products.append(p_copy)
            
    if not filtered_products:
        print("Yuklenecek yeni urun bulunmadi. Tum urunler zaten dukkaninizda mevcut!")
        driver.quit()
        return
        
    print(f"\n[+] Toplam {len(filtered_products)} adet yeni urun yuklenecek.")
    total_products = len(filtered_products)
    
    for idx, p in enumerate(filtered_products):
        print("\n" + "-" * 50)
        print(f"Urun Yukleniyor [{idx + 1}/{total_products}]: {p['name']}")
        print("-" * 50)
        
        # Navigate to product add page in mobile directory
        driver.get("https://www.shopier.com/m/products.php")
        
        # --- SMART DETECTION & WAIT LOOP ---
        on_add_page = False
        wait_msg_sent = False
        while not on_add_page:
            current_url = driver.current_url
            try:
                # Check if subject element exists and is editable, and we are on products.php page
                subject_inputs = driver.find_elements(By.ID, "subject")
                if "products.php" in current_url and subject_inputs and subject_inputs[0].is_displayed():
                    on_add_page = True
                    break
            except Exception:
                pass
                
            if "login" in current_url or "index.php" in current_url:
                print("Lutfen acilan tarayici penceresinde Shopier hesabiniza giris yapin...")
                time.sleep(4)
            else:
                if not wait_msg_sent:
                    print(f"Urun ekleme formu bekleniyor... (Mevcut URL: {current_url})")
                    wait_msg_sent = True
                
                # If they are logged in but on a different page, force redirect to products.php
                if "products.php" not in current_url:
                    try:
                        driver.get("https://www.shopier.com/m/products.php")
                    except Exception:
                        pass
                time.sleep(2)
        # --- END OF DETECTOR LOOP ---
        time.sleep(3.5) # Give the page overlay/js time to completely load and hide loading screens
        
        try:
            wait = WebDriverWait(driver, 10)
            
            # Title
            safe_send_keys(driver, "subject", p["name"], wait)
            
            # Price
            price_str = f"{p['price']:.2f}".replace(".", ",")
            safe_send_keys(driver, "price", price_str)
            
            # Stock
            safe_send_keys(driver, "stock", "999")
            
            # Description
            safe_send_keys(driver, "description", p["desc"])
            
            # Digital Product Type
            digital_radio = driver.find_element(By.ID, "digital")
            driver.execute_script("arguments[0].click();", digital_radio)
            
            # Cargo Price (0,00)
            cargo_price_input = driver.find_element(By.ID, "cargo_price")
            driver.execute_script("arguments[0].value = '0,00';", cargo_price_input)
            
            # Upload cover image
            image_path = os.path.join(img_dir, f"product_{p['orig_idx']}.jpg")
            file_input = driver.find_element(By.ID, "saved-image-picker")
            file_input.send_keys(os.path.abspath(image_path))
            
            # Handle cropper save button if visible
            time.sleep(2)
            cropper_saves = driver.find_elements(By.CSS_SELECTOR, "button.js-cropper-save")
            if cropper_saves and cropper_saves[0].is_displayed():
                driver.execute_script("arguments[0].click();", cropper_saves[0])
                print("Basarili: Cropper gorseli onaylandi.")
                time.sleep(1)
                
            # Submit form
            submit_btn = driver.find_element(By.ID, "list_product")
            driver.execute_script("arguments[0].click();", submit_btn)
            print("Basarili: Kaydet butonuna tiklandi. Yonlendirme bekleniyor...")
            
            # Wait for redirect indicating success
            saved = False
            start_time = time.time()
            while time.time() - start_time < 12:
                if "listproduct.php" in driver.current_url:
                    saved = True
                    break
                time.sleep(0.5)
                
            if saved:
                print(f"Basarili: Urun eklendi: {p['name']}")
            else:
                print(f"Uyari: Urun otomatik yonlendirme alamadi. Lutfen kontrol edin.")
                input("Eger urun kaydedildiyse devam etmek icin ENTER tusuna basin (Atlamak icin tarayiciyi kontrol edin)...")
                
        except Exception as e:
            print(f"Hata: Urun eklenirken sorun olustu: {e}")
            input("Sorunu tarayicidan cozup urunu kaydettiyseniz devam etmek icin ENTER tusuna basin...")
            
    print("\n" + "=" * 60)
    print("TEBRIKLER! Tum urunler basariyla yuklendi.")
    print("=" * 60)

if __name__ == "__main__":
    main()
