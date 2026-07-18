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
    {"name": "Steam 200 Dolar Random Key", "price": 30.00, "desc": "Steam platformunda gecerli random key. Aninda teslimat.", "img_kv": "keyvadi_steam_random.png", "img_la": "lisansarena_steam_random.png"},
    {"name": "Netflix 4K UHD Ortak Profil", "price": 39.99, "desc": "Kisisel Netflix 4K Ultra HD Profili. Ortak hesapta size ait ozel profil.", "img_kv": "keyvadi_netflix_4k.png", "img_la": "lisansarena_netflix_4k.png"},
    {"name": "Zula Random Hesap", "price": 5.00, "desc": "En az 0, en cok 250 skin cikmaktadir.\nEn az 1, en cok 155 level cikmaktadir.\nHesaplarda minumum 1000-3000 Zula altini cikmaktadir.\nYeni acilmis hesap cikma ihtimali vardir.\nAktif olmasak bile satin alim islemi gerceklestirebilirsiniz. Otomatik teslimattir.\nHer hesap tek bir kisiye satilir.", "img_kv": "keyvadi_zula_random.png", "img_la": "lisansarena_zula_random.png"},
    {"name": "FC26 + Online Her Seyi Degisen Hesap", "price": 299.99, "desc": "FC26 ve Online dahil her seyi degisen Steam hesabi. Aninda teslim.", "img_kv": "keyvadi_fc26_hesap.png", "img_la": "lisansarena_fc26_hesap.png"}
]

def main():
    print("=" * 60)
    print("SHOPIER YENI URUN YUKLEME ASISTANI (KEYVADI & LISANSARENA)")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        print("\nLutfen hangi magazaya urun eklemek istediginizi secin:")
        print("1) KeyVadi (Mavi/Mor Konsept Gorsellerle)")
        print("2) LisansArena (Kirmizi/Siyah Konsept Gorsellerle)")
        choice = input("Seciminiz (1 veya 2): ").strip()
    
    if choice == '1':
        store = "KeyVadi"
        img_key = "img_kv"
    elif choice == '2':
        store = "LisansArena"
        img_key = "img_la"
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
        print(f"\nUrun {idx + 1}/4 ekleniyor: {p['name']}")
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
        
        price_str = f"{p['price']:.2f}".replace(".", ",")
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
            
        image_path = os.path.join(img_dir, p[img_key])
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
