import requests
import json
import os

# Clean version without emojis to avoid terminal encoding errors
API_KEY = "AIzaSyCZz54GBF4nCgP84DsTSwwMyPq70Lb_Mjo"
PROJECT_ID = "bot-2-63772"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
CONFIG_FILE = "bot_config.json"
BLACKLIST_FILE = "blacklist.txt"

gruplar = [
    "kuponceking", "kuponsatislari0", "sosyalmedyaalimsatimticaret", "ticaretguvenilir",
    "kuponsatisgrup", "dijitalilan", "kuponceksatis", "ticaretsaha", "IWEfTGD7OCBjY2I8",
    "satilikilanlar", "diyarbakirikincielarac", "smmpanelgrup", "kuponhesapsatis",
    "YuceKuponSatis", "ticaretforumofficial", "referansreklam1", "Nightsatis",
    "kuponsat", "indirimkodusatis", "dolapdestek0"
]
target_set = set(g.lower() for g in gruplar)

def main():
    print("Firestore'dan kara liste yukleniyor...")
    url = f"{BASE_URL}/reklam/state?key={API_KEY}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print(f"HATA: Firestore baglantisi basarisiz ({r.status_code}): {r.text}")
        return

    data = r.json()
    fields = data.get("fields", {})
    blacklist_str = fields.get("blacklist_list", {}).get("stringValue", "")
    progress_str = fields.get("progress_list", {}).get("stringValue", "")
    auto_groups_str = fields.get("auto_groups_list", {}).get("stringValue", "")

    blacklist_lines = [line.strip() for line in blacklist_str.splitlines() if line.strip()]
    print(f"Mevcut Kara Liste Uye Sayisi: {len(blacklist_lines)}")

    # Hedef grupları kara listeden çıkar
    cleaned_lines = []
    removed_groups = []
    for g in blacklist_lines:
        if g.lower() in target_set:
            removed_groups.append(g)
        else:
            cleaned_lines.append(g)

    print(f"Kara listeden cikarilan hedef gruplar ({len(removed_groups)} adet): {removed_groups}")
    print(f"Yeni Kara Liste Uye Sayisi: {len(cleaned_lines)}")

    # Firestore'u güncelle
    new_blacklist_str = "\n".join(cleaned_lines) + "\n" if cleaned_lines else ""
    
    update_fields = {
        "progress_list": {"stringValue": progress_str},
        "blacklist_list": {"stringValue": new_blacklist_str},
        "auto_groups_list": {"stringValue": auto_groups_str}
    }
    
    print("Firestore guncelleniyor...")
    patch_r = requests.patch(url, json={"fields": update_fields}, timeout=10)
    if patch_r.status_code == 200:
        print("Firestore basariyla guncellendi!")
    else:
        print(f"HATA: Firestore guncellenemedi: {patch_r.text}")
        return

    # Yerel dosyayı güncelle
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        f.write(new_blacklist_str)
    print(f"Yerel {BLACKLIST_FILE} dosyasi guncellendi.")

if __name__ == "__main__":
    main()
