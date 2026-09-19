import os
import sys
import time
import subprocess
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        wait_click = WebDriverWait(driver, 2)
        el_clickable = wait_click.until(EC.element_to_be_clickable((By.ID, element_id)))
        el_clickable.send_keys(text)
    except Exception as e:
        driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """, el, text)

products = [
    {
        "name": "Tıkla Gelsin 400 TL'ye 200 TL İndirim Kuponu",
        "price_kv": 80.00,
        "price_la": 95.00,
        "desc": "Tıkla Gelsin (Burger King, Popeyes, Arby's, Sbarro vb.) uygulamasında 400 TL ve üzeri siparişlerde geçerli 200 TL anında indirim kupon kodu. Anında otomatik teslimat.",
        "img": "card_clean_tiklagelsin.jpg"
    },
    {
        "name": "Yemeksepeti 500 TL'ye 250 TL İndirim Kodu",
        "price_kv": 100.00,
        "price_la": 120.00,
        "desc": "Yemeksepeti restoran siparişlerinde 500 TL ve üzeri sepetlerde anında 250 TL indirim sağlayan kupon kodu. Anında teslimat.",
        "img": "card_clean_yemeksepeti.jpg"
    },
    {
        "name": "Yemeksepeti 550 TL'ye 200 TL İndirim Kodu",
        "price_kv": 75.00,
        "price_la": 90.00,
        "desc": "Yemeksepeti siparişlerinde geçerli 550 TL ve üzeri siparişlerde 200 TL indirim kodu. Anında teslimat.",
        "img": "card_clean_yemeksepeti.jpg"
    },
    {
        "name": "Trendyol Yemek Alt Limitsiz 200 TL Yemek Kodu",
        "price_kv": 60.00,
        "price_la": 75.00,
        "desc": "Trendyol Yemek siparişlerinde alt limitsiz 200 TL indirim sağlayan özel yemek kupon kodu. Anında teslimat.",
        "img": "card_clean_yemeksepeti.jpg"
    },
    {
        "name": "Uber İlk 2 Yolculuğa %70 İndirim Kodu",
        "price_kv": 125.00,
        "price_la": 150.00,
        "desc": "Uber taksi ve yolculuklarda ilk 2 kullanımda %70 indirim sağlayan promosyon kupon kodu. Anında teslimat.",
        "img": "card_clean_turna.jpg"
    },
    {
        "name": "Uber 500+500 TL Alt Limitsiz İndirim Kodu",
        "price_kv": 85.00,
        "price_la": 100.00,
        "desc": "Uber üzerinde geçerli 2 adet 500 TL toplam 1.000 TL alt limitsiz indirim kupon kodu. Anında teslimat.",
        "img": "card_clean_turna.jpg"
    },
    {
        "name": "TOD TV Haftalık Taraftar Paketi",
        "price_kv": 100.00,
        "price_la": 120.00,
        "desc": "TOD TV (beIN Sports) Süper Lig canlı maç yayınları, derbiler ve spor kanallarını içeren haftalık taraftar paketi kupon kodu. Anında teslimat.",
        "img": "card_clean_ssport.jpg"
    },
    {
        "name": "GPT GO 3 Aylık İndirim Kodu",
        "price_kv": 150.00,
        "price_la": 180.00,
        "desc": "GPT GO platformunda 3 aylık kullanımda geçerli özel indirim kodu. Gelişmiş yapay zeka modellerine yüksek hızda erişim. Anında teslimat.",
        "img": "card_clean_chatgpt.jpg"
    },
    {
        "name": "TikTak 1.000 TL Araç Kiralama İndirim Kodu",
        "price_kv": 30.00,
        "price_la": 40.00,
        "desc": "TikTak saatlik veya günlük araç kiralamada geçerli 1.000 TL indirim kodu. Anında teslimat.",
        "img": "card_clean_tiktak.jpg"
    },
    {
        "name": "FLO 3.000 TL'ye 800 TL İndirim Çeki",
        "price_kv": 20.00,
        "price_la": 30.00,
        "desc": "FLO mobil ve web alışverişlerinde 3.000 TL ve üzeri sepetlerde 800 TL indirim sağlayan kupon kodu. Anında teslimat.",
        "img": "card_clean_flo.jpg"
    },
    {
        "name": "Turna 600 TL Uçak Bileti İndirim Kuponu",
        "price_kv": 80.00,
        "price_la": 90.00,
        "desc": "Turna.com üzerinden yapılacak uçak bileti alımlarında geçerli 600 TL indirim sağlayan kupon kodu. Anında otomatik teslimat.",
        "img": "card_clean_turna.jpg"
    }
]

def main():
    print("=" * 60)
    print("SHOPIER YENI URUN YUKLEME ASISTANI (KEYVADI & LISANSARENA)")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        print("\nLutfen hangi magazaya urun eklemek istediginizi secin:")
        print("1) KeyVadi (KeyVadi Fiyatlariyla)")
        print("2) LisansArena (LisansArena Fiyatlariyla)")
        choice = input("Seciminiz (1 veya 2): ").strip()
    
    if choice == '1':
        store = "KeyVadi"
        price_key = "price_kv"
    elif choice == '2':
        store = "LisansArena"
        price_key = "price_la"
    else:
        print("Gecersiz secim!")
        return

    img_dir = os.path.join(os.getcwd(), "static")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    
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
    except Exception:
        pass

    try:
        if main_version:
            driver = uc.Chrome(options=options, version_main=main_version)
        else:
            driver = uc.Chrome(options=options)
    except Exception:
        driver = uc.Chrome(options=options, version_main=150)
        
    driver.get("https://www.shopier.com/m/products.php")
    
    print(f"\n[{store}] Hesabiniza tarayici uzerinden giris yapmaniz bekleniyor...")
    
    while True:
        current_url = driver.current_url
        if "login" not in current_url and "index.php" not in current_url:
            break
        time.sleep(2)
        
    print("\nGiris basarili! Otomatik urun ekleme basliyor...")
    
    for idx, p in enumerate(products):
        print(f"\nUrun {idx + 1}/{len(products)} ekleniyor: {p['name']}")
        driver.get("https://www.shopier.com/m/products.php")
        
        on_add_page = False
        while not on_add_page:
            try:
                subject_inputs = driver.find_elements(By.ID, "subject")
                if "products.php" in driver.current_url and subject_inputs and subject_inputs[0].is_displayed():
                    on_add_page = True
                    break
            except:
                pass
            time.sleep(2)
            
        time.sleep(3)
        
        wait = WebDriverWait(driver, 10)
        safe_send_keys(driver, "subject", p["name"], wait)
        
        price_val = p.get(price_key, p.get("price", 50.0))
        price_str = f"{price_val:.2f}".replace(".", ",")
        safe_send_keys(driver, "price", price_str)
        safe_send_keys(driver, "stock", "999")
        safe_send_keys(driver, "description", p["desc"])
        
        try:
            digital_radio = driver.find_element(By.ID, "digital")
            driver.execute_script("arguments[0].click();", digital_radio)
        except:
            pass
            
        try:
            cargo_price_input = driver.find_element(By.ID, "cargo_price")
            driver.execute_script("arguments[0].value = '0,00';", cargo_price_input)
        except:
            pass
            
        img_name = p.get("img") or "card_clean_yemeksepeti.jpg"
        image_path = os.path.join(img_dir, img_name)
        if os.path.exists(image_path):
            file_input = driver.find_element(By.ID, "saved-image-picker")
            file_input.send_keys(os.path.abspath(image_path))
            
            time.sleep(2)
            cropper_saves = driver.find_elements(By.CSS_SELECTOR, "button.js-cropper-save")
            if cropper_saves and cropper_saves[0].is_displayed():
                driver.execute_script("arguments[0].click();", cropper_saves[0])
                time.sleep(1)
                
        submit_btn = driver.find_element(By.ID, "list_product")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        saved = False
        start_time = time.time()
        while time.time() - start_time < 12:
            if "listproduct.php" in driver.current_url:
                saved = True
                break
            time.sleep(0.5)
            
        if saved:
            print(f"[BASARILI] {p['name']} eklendi.")
        else:
            print(f"[UYARI] {p['name']} icin manuel onay/kontrol gerekebilir.")
            input("Tarayicida islem tamamlandiysa devam etmek icin ENTER'a basin...")
            
    print("\nIslem tamam! Lutfen Shopier panelinizden eklenen urunlerin linklerini almayi unutmayin.")
    print("Urun linklerinizi keyvadi_shopier_links.json ve lisansarena_shopier_links.json dosyalarina kaydedin.")
    driver.quit()

if __name__ == "__main__":
    main()
