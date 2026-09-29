"""Refresh KeyVadi/Jarvis ad copy from the current local product catalogs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "messages"
KV = json.loads((ROOT / "miniapp" / "products_db.json").read_text(encoding="utf-8"))
KV_BY_ID = {str(item["id"]): item for item in KV}
JARVIS = json.loads((ROOT / "jarvis_subscriptions.json").read_text(encoding="utf-8"))
JARVIS_BY_KEY = {item["key"]: item for item in JARVIS}

# These two prices disagree between the Mini App and link cache. Keep them out
# of the new advertising rotation until the live Shopier price is confirmed.
EXCLUDED_KV_IDS = {"47669105", "47669159"}


def kv_line(product_id: str) -> str:
    item = KV_BY_ID[product_id]
    return f"• {item['title']} — {item['price']}"


def keyvadi(name: str, heading: str, intro: str, product_ids: list[str], hero_id: str) -> None:
    original = (MESSAGES / name).read_text(encoding="utf-8")
    original_size = len(original)
    products = [product_id for product_id in product_ids if product_id not in EXCLUDED_KV_IDS]
    if hero_id in EXCLUDED_KV_IDS or hero_id not in KV_BY_ID:
        raise ValueError(f"Invalid hero product: {hero_id}")
    lines = [
        f"[ KEYVADİ | {heading} ]", "", intro, "",
        "Ürün türünü karşılaştırın; davet, ortak hesap, kod ve kendi hesabına aktivasyon birbirinden farklıdır.",
        "", "SEÇİLİ ÜRÜNLER:",
    ]
    seen = set()
    for product_id in products:
        if product_id not in seen and product_id in KV_BY_ID:
            lines.append(kv_line(product_id))
            seen.add(product_id)
    lines += [
        "", "Teslimat yöntemi ve varsa garanti süresi, ilgili ürün ilanında yazılıdır.",
        "Ödeme öncesinde ürün türünü ve kullanım koşullarını kontrol edin.",
        "", f"Öne çıkan ilan: {KV_BY_ID[hero_id]['url']}",
        "Mağaza ve destek: @KeyVadiSatisBot",
    ]
    result = "\n".join(lines) + "\n"
    if not 0.75 * original_size <= len(result) <= 1.3 * original_size:
        raise ValueError(f"{name}: {len(result)} chars vs {original_size} original")
    (MESSAGES / name).write_text(result, encoding="utf-8")


def jarvis_line(key: str) -> str:
    item = JARVIS_BY_KEY[key]
    amount = item["price"].replace(".", ",")
    warranty = f" | {item['warranty']} garanti" if item["warranty"] else ""
    return f"• {item['title']} — {amount} TL{warranty}"


def jarvis(name: str, heading: str, intro: str, keys: list[str], old_offer: str = "") -> None:
    original_size = len((MESSAGES / name).read_text(encoding="utf-8"))
    lines = [f"[ JARVISCRAFT | {heading} ]", "", intro, ""]
    if old_offer:
        lines += [old_offer, ""]
    lines.extend(jarvis_line(key) for key in keys)
    lines += [
        "", "Dijital üyeliklerin tamamı destek ekibi tarafından manuel teslim edilir.",
        "Davet, promosyon bağlantısı, ortak hesap ve kendi hesabına aktivasyon farklı ürünlerdir.",
        "Garanti süresi yalnızca ilgili ürün ilanında belirtilen seçenekler için geçerlidir.",
        "", "Ürün detayı ve sipariş: @JarvisCraftsBot → Dijital Üyelikler",
        "Destek: @JarvisCraft",
    ]
    result = "\n".join(lines) + "\n"
    if not 0.75 * original_size <= len(result) <= 1.35 * original_size:
        raise ValueError(f"{name}: {len(result)} chars vs {original_size} original")
    (MESSAGES / name).write_text(result, encoding="utf-8")


def main() -> None:
    general = ["51051020", "49362861", "51025109", "51051022", "47669321", "49467632", "50857983", "48943136", "47669117", "50857984", "50857985", "50857986", "50857987", "50857988", "50857990", "50858094", "50576029", "50460191", "49078921", "48114789", "48114785", "49467735", "47669109", "49002145", "50460466", "48943139"]
    ai = ["51025109", "49362861", "48943136", "50857983", "47669321", "49467632", "51051022", "48943139", "48943151", "48114789", "49078921", "50460458", "50460461", "48114785", "51051020", "47669390", "49467735"]
    food = ["50857984", "50857985", "50857986", "50858094", "50857987", "50857990", "50857988", "47669117", "50576029", "49002145", "49002144", "47669109", "47669125", "50460191", "50460461", "47669390"]
    learning = ["51051020", "47669390", "47669321", "49078921", "51051022", "50857983", "49362861", "48943136", "48943151", "48114789", "48114785", "49467632", "50460458", "48943139", "51025109"]
    design = ["51051022", "47669321", "49078921", "49467632", "50460458", "48114789", "48114785", "48943151", "48943139", "50857983", "49362861", "51025109", "51051020"]
    coupons = ["50857984", "50857985", "50857986", "50858094", "50857987", "50857990", "50857988", "47669390", "49002145", "47669117", "50576029", "49002144", "50460466", "47669109"]
    keyvadi("keyvadi_1.txt", "NET FİYATLI DİJİTAL ÜRÜNLER", "Yapay zekâ, eğitim, tasarım ve günlük fırsatları tek mağazada inceleyin. Uzun listede kaybolmadan önce ürün türüne bakın; doğru seçeneğe doğrudan gidebilirsiniz.", general, "51051020")
    keyvadi("keyvadi_2.txt", "YAPAY ZEKÂ VE ÜRETKENLİK", "Kendi hesabınıza aktivasyon mu, davet mi, ortak hesap mı? İhtiyacınıza uyan teslimat türünü ürün adında görün. Fiyat ve kullanım koşulları her ilanın detayında açıkça yer alır.", ai, "49362861")
    keyvadi("keyvadi_3.txt", "EĞLENCE VE GÜNLÜK FIRSATLAR", "Dizi, spor, oyun ve yemek seçeneklerini karşılaştırın. Kuponların alt limitini ve hesapların kullanım türünü siparişten önce kontrol edin. Turna 600 TL Uçak Kuponu: 80₺", food, "50857984")
    keyvadi("keyvadi_4.txt", "EĞİTİM VE İŞ ARAÇLARI", "Dil öğrenimi, üretkenlik ve tasarım için ürünün kendi hesabınıza mı tanımlandığını veya hazır hesap mı verildiğini ilk bakışta görün.", learning, "51051020")
    keyvadi("keyvadi_5.txt", "KUPON VE ULAŞIM", "Yemek ve ulaşım kodları için tutarı, alt limiti ve geçerlilik şartlarını ilan detayından inceleyin. Doğru kuponu seçtikten sonra doğrudan ilgili ilana geçin.", coupons, "50857984")
    keyvadi("keyvadi_6.txt", "ÖNE ÇIKAN SEÇENEKLER", "En çok sorulan dijital ürünler ve kuponlar burada. Hesap paylaşımı, davet ve kişisel aktivasyon arasındaki farkı ürün detayında görebilirsiniz.", general[:18], "49362861")
    keyvadi("keyvadi_7.txt", "TASARIM VE YAPAY ZEKÂ", "İçerik üretimi için Adobe, Canva, CapCut ve yapay zekâ seçenekleri. Hangi ürünün kendi hesabınıza tanımlandığını ve hangi ürünün ortak hesap olduğunu karşılaştırın.", design, "51051022")
    keyvadi("keyvadi_8.txt", "MAĞAZA REHBERİ", "Kodu, daveti, ortak hesabı ve kendi hesabına aktivasyonu birbirine karıştırmadan alışveriş yapın. Her üründe fiyat, teslimat ve kullanım koşulları için ilan detayını açın.", general[:22], "51051020")
    keyvadi("keyvadi_ai.txt", "YAPAY ZEKÂ SEÇENEKLERİ", "Yapay zekâ ürünlerinde teslimat biçimi en önemli ayrım. Ortak hesap, davet ve kendi hesabınıza aktivasyon seçeneklerini karşılaştırın.", ai[:13], "49362861")
    keyvadi("keyvadi_adobe.txt", "TASARIM ARAÇLARI", "Adobe Express, Canva ve CapCut seçeneklerini tasarım iş akışınıza göre inceleyin. Kişisel aktivasyon ile ortak hesap farkını ürün adında görün.", design[:12], "51051022")
    keyvadi("keyvadi_deal.txt", "KUPON VE FIRSATLAR", "Yemek ve ulaşımda doğru kodu seçin. Alt limit ve kullanım şartlarını ilan sayfasında kontrol ederek siparişi tamamlayın.", coupons[:9], "50857984")
    keyvadi("keyvadi_kupon.txt", "KUPON REHBERİ", "Tek bir indirim başlığına bakıp karar vermeyin; kod tutarını ve kullanım koşullarını karşılaştırın.", coupons[:9], "50857985")
    keyvadi("keyvadi_ogrenci.txt", "ÖĞRENİM VE ÜRETKENLİK", "Dil öğrenimi, not alma ve içerik üretimi için süre ve teslimat türü açıkça görünen seçenekler.", learning[:12], "51051020")
    keyvadi("keyvadi_genel.txt", "DİJİTAL MAĞAZA", "Ürünün nasıl teslim edildiğini bilerek seçin. Bu listede kendi hesabına aktivasyon, ortak hesap, kod ve davet seçenekleri ayrı ayrı yazılıdır.", general, "51051020")

    jarvis("jarvis_1.txt", "YAPAY ZEKÂ ÜYELİKLERİ", "Gemini Pro seçenekleri aynı ürün değildir: davet ve promosyon bağlantısını ayrı inceleyin. Uzun süreli seçeneklerin Shopier açıklamasında 1 ay garanti belirtilir.", ["gemini_1m_invite", "gemini_18m_promo", "gemini_18m_invite", "gemini_12m_invite"])
    jarvis("jarvis_2.txt", "ORTAK HESAP SEÇENEKLERİ", "ChatGPT Plus ve Perplexity Pro için 1 aylık ortak hesap seçenekleri. Kişisel hesap veya kendi hesabınıza aktivasyon olarak sunulmaz.", ["chatgpt_shared_1m", "perplexity_shared_1m", "gemini_1m_invite"], "Mevcut Jarvis yazılım, bot ve VIP paketleri de mağazada yer alır.")
    jarvis("jarvis_3.txt", "TASARIM VE ÜRETKENLİK", "Adobe Creative Cloud ve Adobe Express üyelikleri kendi hesabınıza aktivasyon olarak hazırlanır. Süreyi ve ürün adını karşılaştırarak seçim yapın.", ["adobe_cc_2m_personal", "adobe_cc_3m_personal", "adobe_cc_4m_personal", "adobe_express_12m_personal"])
    jarvis("jarvis_4.txt", "DİL ÖĞRENİMİ", "Duolingo Super 12 ay kendi hesabınıza aktivasyon seçeneği. Ürün bilgisi ve teslimat adımlarını bot kartında inceleyin.", ["duolingo_super_12m_personal", "chatgpt_shared_1m"])
    jarvis("jarvis_5.txt", "DİJİTAL ÜYELİKLER", "Yazılım paketlerinin yanında yapay zekâ, tasarım ve eğitim üyelikleri de JarvisCraft mağazasında.", ["gemini_1m_invite", "perplexity_shared_1m", "adobe_cc_2m_personal"])
    jarvis("full_jarvis_1.txt", "YENİ ÜYELİK KATALOĞU", "Gemini davet ve promosyon bağlantıları, ortak AI hesapları ve kendi hesabınıza aktivasyonlar. Her varyant ayrı ilandır; fiyat ve garantiyi doğru varyantla eşleştirin.", ["gemini_1m_invite", "gemini_18m_promo", "gemini_18m_invite", "gemini_12m_invite", "chatgpt_shared_1m", "perplexity_shared_1m", "adobe_cc_2m_personal", "adobe_cc_3m_personal", "adobe_cc_4m_personal", "adobe_express_12m_personal", "duolingo_super_12m_personal"])
    jarvis("full_jarvis_2.txt", "YAPAY ZEKÂ VE TASARIM", "Bir aylık ortak hesap, uzun süreli Gemini daveti ve kendi hesabınıza Adobe aktivasyonu arasında ihtiyacınıza uygun seçeneği bulun.", ["chatgpt_shared_1m", "perplexity_shared_1m", "gemini_18m_promo", "gemini_18m_invite", "gemini_12m_invite", "adobe_cc_2m_personal", "adobe_cc_3m_personal"])
    jarvis("full_jarvis_3.txt", "DİJİTAL EĞİTİM VE ÜYELİK", "JarvisCraft yazılım ürünlerine ek olarak dijital üyelikler. Kendi hesabınıza aktivasyon ve ortak hesap seçenekleri birbirinden ayrıdır.", ["duolingo_super_12m_personal", "adobe_express_12m_personal", "adobe_cc_4m_personal", "gemini_1m_invite", "chatgpt_shared_1m"])

    for name in ("keyvadi_3.txt", "jarvis_1.txt", "full_jarvis_1.txt"):
        path = MESSAGES / name
        print(f"{name}: {len(path.read_text(encoding='utf-8'))} chars")


if __name__ == "__main__":
    main()
