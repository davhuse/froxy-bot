import time
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def get_main_version():
    try:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            if version: return int(version.split(".")[0])
        except:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome")
            version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            if version: return int(version.split(".")[0])
    except:
        pass
    return None

def main():
    print("Shopier urunleri taranıyor... Tarayici baslatiliyor...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    
    version = get_main_version()
    try:
        driver = uc.Chrome(options=options, version_main=version)
    except:
        try:
            driver = uc.Chrome(options=options, version_main=149)
        except:
            driver = uc.Chrome(options=options)
            
    driver.get("https://www.shopier.com/m/listproduct.php")
    
    print("\n>>> LUTFEN ACILAN PENCEREDEN SHOPIER'E GIRIS YAPIN <<<")
    while True:
        url = driver.current_url
        if "login" not in url and "index.php" not in url:
            break
        time.sleep(2)
        
    print("Giris basarili! Sayfa tam yuklenene kadar bekleniyor...")
    time.sleep(5)
    
    # Scroll down multiple times to trigger lazy loading if any
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
    html = driver.page_source
    with open("shopier_listproduct_source.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Urun listesi basariyla kopyalandi! Tarayici kapaniyor...")
    driver.quit()

if __name__ == "__main__":
    main()
