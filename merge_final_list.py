import json

with open('yeni_birebir_hedef_gruplar.json', 'r', encoding='utf-8') as f:
    current = json.load(f)

current_unames = {g['username'].lower() for g in current}

extra_verified = [
    {
        'username': 'me7alimsatim',
        'title': '💸Hesap Alım-Satım-Takas❤️',
        'category': 'Premium Hesap & Dijital Ürün Satışı',
        'members': 248,
        'online': 14,
        'relevance_score': 12,
        'matched_keywords': ['hesap', 'satım', 'alım', 'fiyat', 'dm'],
        'about_description': 'Hesap Alım Satım ve Takas Pazarı',
        't_me_link': 'https://t.me/me7alimsatim'
    },
    {
        'username': 'ticaretsaha',
        'title': 'Revenge Ticaret Grubu',
        'category': 'Dijital Pazar & Alım-Satım Ticareti',
        'members': 592,
        'online': 38,
        'relevance_score': 8,
        'matched_keywords': ['ticaret', 'satış', 'fiyat', 'al sat'],
        'about_description': 'Ticaret ve Alım Satım Pazarı',
        't_me_link': 'https://t.me/ticaretsaha'
    },
    {
        'username': 'hesapaccount1',
        'title': 'ACCOUNT SALES / HESAP SATIŞLARI',
        'category': 'Premium Hesap & Dijital Ürün Satışı',
        'members': 89,
        'online': 7,
        'relevance_score': 10,
        'matched_keywords': ['hesap', 'account', 'satış', 'stok'],
        'about_description': 'Dijital Hesap Alım Satım',
        't_me_link': 'https://t.me/hesapaccount1'
    },
    {
        'username': 'tiktokjdcjsp',
        'title': 'SOSYAL MEDYA HESAP ALIM SATIM',
        'category': 'Premium Hesap & Dijital Ürün Satışı',
        'members': 86,
        'online': 4,
        'relevance_score': 9,
        'matched_keywords': ['sosyal medya', 'hesap', 'alım', 'satım'],
        'about_description': 'TikTok ve Sosyal Medya Hesap Pazarı',
        't_me_link': 'https://t.me/tiktokjdcjsp'
    }
]

for item in extra_verified:
    if item['username'].lower() not in current_unames:
        current.append(item)

current.sort(key=lambda x: (-x['online'], -x['members']))

with open('yeni_birebir_hedef_gruplar.json', 'w', encoding='utf-8') as f:
    json.dump(current, f, ensure_ascii=False, indent=2)

with open('yeni_birebir_hedef_gruplar.txt', 'w', encoding='utf-8') as f:
    for g in current:
        f.write(f"{g['username']}\n")

print(f"Final Toplam Doğrulanmış Grup Sayısı: {len(current)}")
