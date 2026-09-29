"""Refresh the active long KeyVadi rotation from the local product catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "messages"
products = json.loads((ROOT / "miniapp" / "products_db.json").read_text(encoding="utf-8"))

# These local prices conflict with the Shopier link cache. Keep the products in
# the full catalogue but leave the amount to the live product detail.
PRICE_PENDING = {"47669105", "47669159"}
GROUPS = [
    ("full_keyvadi_1.txt", "YAPAY ZEKÂ", {"ai"},
     "Davet, ortak hesap ve kişisel seçenekleri ürün adından karşılaştırın. İlgilendiğiniz ürünün detayında süre ve teslimat koşullarını inceleyin."),
    ("full_keyvadi_2.txt", "TASARIM VE FIRSATLAR", {"design", "deals"},
     "Tasarım araçları ve seçili fırsatlar bir arada. Kendi hesabına aktivasyon ile hazır hesabı ayırarak seçim yapın."),
    ("full_keyvadi_3.txt", "İŞ VE GÜVENLİK", {"tools", "security"},
     "İş araçlarında lisans, davet ve hesap türünü kontrol edin. Garanti veya teslimat bilgisi için ilgili ilana bakın."),
    ("full_keyvadi_4.txt", "OYUN VE KUPONLAR", {"gaming", "coupons"},
     "Oyun üyelikleri ve indirim kodlarında kullanım koşulları ürün bazında değişir. Kodun tutarını ve alt limitini ilanda inceleyin."),
    ("full_keyvadi_5.txt", "EĞLENCE VE ÜYELİKLER", {"entertainment"},
     "Dizi, spor, müzik ve eğitim üyeliklerini süre ve hesap türüne göre karşılaştırın. Siparişten önce ürün detayını açın."),
]

covered = set()
for name, heading, categories, intro in GROUPS:
    path = MESSAGES / name
    original_size = len(path.read_text(encoding="utf-8"))
    group = [item for item in products if item.get("category") in categories]
    covered.update(str(item["id"]) for item in group)
    lines = [
        f"[ KEYVADİ | {heading} ]", "", intro, "",
        "SEÇİLİ ÜRÜNLER:",
    ]
    for item in group:
        price = item["price"] if str(item["id"]) not in PRICE_PENDING else "Fiyatı ilanda doğrulayın"
        lines.append(f"• {item['title']} — {price}")
    lines += [
        "", "Teslimat yöntemi, stok ve varsa garanti süresi ilgili ürün ilanında yazılıdır.",
        "Ödeme öncesinde ürün türünü ve kullanım koşullarını kontrol edin.",
        "", f"Öne çıkan ilan: {group[0]['url']}",
        "Mağaza ve destek: @KeyVadiSatisBot",
    ]
    result = "\n".join(lines) + "\n"
    if not 0.75 * original_size <= len(result) <= 1.35 * original_size:
        raise ValueError(f"{name}: {len(result)} chars vs {original_size} original")
    path.write_text(result, encoding="utf-8")
    print(f"{name}: {len(group)} products, {len(result)} chars")

assert covered == {str(item["id"]) for item in products}
