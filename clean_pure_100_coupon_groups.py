import json
import os
import re

# Master replacement and purification list
PURE_COUPON_TRADE_POOL = [
    # Yemeksepeti, Yemek & Restoran Kuponları
    {"username": "yemeksepetikuponu", "title": "Yemek Sepeti Kuponu 🍕", "members": 2526, "type": "Yemeksepeti & Yemek Kuponları"},
    {"username": "mukyemek", "title": "Mük Yemek-Hb-Dijital lisans", "members": 566, "type": "Yemeksepeti & Dijital Kuponlar"},
    {"username": "yemeksepeti_kupon_indirim", "title": "Yemek Sepeti İndirim & Kupon", "members": 306, "type": "Yemeksepeti Kupon Alım-Satım"},
    {"username": "yemeksepetiesnaf", "title": "Yemeksepeti Esnaf & Kurye Pazar", "members": 680, "type": "Yemeksepeti Pazar"},
    {"username": "trendyolkampanya5", "title": "Trendyol Yemek & Market Kodları", "members": 59, "type": "Yemek & Market Kodları"},
    
    # Kupon, Çek & Kod Ana Alım-Satım Pazarları
    {"username": "kupongrupta", "title": "Kupon Kod İndirim İlanları", "members": 7182, "type": "Kupon & Kod İlanları"},
    {"username": "kuponhesapsatis", "title": "Kupon Hesap Kod Satış", "members": 3267, "type": "Kupon & Hesap Satış"},
    {"username": "kuponsat", "title": "Kupon & Kod Satış Platformu", "members": 3051, "type": "Kupon & Kod Pazarı"},
    {"username": "kuponindirimpazari", "title": "Kupon İndirim Pazarı", "members": 2684, "type": "Kupon İndirim Pazarı"},
    {"username": "kodceksatismerkezi", "title": "Kod & Çek İlan Satışı 🇹🇷", "members": 2466, "type": "Kod & Çek İlan Satışı"},
    {"username": "kuponsatisgrup", "title": "Kupon-Kod Satış Grubu", "members": 2241, "type": "Kupon & Kod Satış"},
    {"username": "kuponkodalimsatimm", "title": "Kupon Kod Alım Satım", "members": 1931, "type": "Kupon Kod Alım-Satım"},
    {"username": "kuponsatimalim", "title": "İndirim Kuponu-Çek Alım Satım", "members": 1552, "type": "Kupon & Çek Alım-Satım"},
    {"username": "ticaretyapn", "title": "Kod Çek - SATIŞ", "members": 1184, "type": "Kod & Çek Satış"},
    {"username": "ceksat", "title": "Çek Satış Pazarı", "members": 1030, "type": "Çek Satış Pazarı"},
    {"username": "kuponcekkodsatis", "title": "Kupon Çek Kod Satış", "members": 875, "type": "Kupon Çek Kod Satış"},
    {"username": "kuponkodualsat", "title": "Kupon Kodu Al Sat", "members": 860, "type": "Kupon Kodu Al-Sat"},
    {"username": "kodkuponmerkezi", "title": "Gold Kupon Merkezi", "members": 758, "type": "Kupon & Kod Merkezi"},
    {"username": "kodpazari", "title": "Kod Pazarı", "members": 720, "type": "Kod Pazarı"},
    {"username": "kuponindirimkodalisveris", "title": "Kupon İndirim Kod Alışveriş", "members": 620, "type": "Kupon & Kod Alışveriş"},
    {"username": "kuponsatislari0", "title": "KOD SATIŞI 👌", "members": 586, "type": "Kupon & Kod Satışı"},
    {"username": "ceksatkupon", "title": "Çek-Sat Kupon Platformu", "members": 518, "type": "Çek & Kupon Platformu"},
    {"username": "yucekuponsatis", "title": "KOD VE KUPON SATIŞ GRUBU", "members": 501, "type": "Kod & Kupon Satışı"},
    {"username": "kodmalf", "title": "KUPON ALIM SATIM GURBU", "members": 481, "type": "Kupon Alım-Satım"},
    {"username": "indirimkodusatis", "title": "KUPON KOD SATIŞI 🇹🇷", "members": 435, "type": "Kupon & Kod Satışı"},
    {"username": "kuponcekm", "title": "Kupon-Kod-Çek Satıșı", "members": 423, "type": "Kupon, Kod & Çek Satışı"},
    {"username": "kuponkodalimsatim", "title": "Kupon kod alım satım", "members": 365, "type": "Kupon Kod Alım-Satım"},
    {"username": "kodindirimsatis", "title": "Kod İndirim Satış", "members": 362, "type": "Kod İndirim Satış"},
    {"username": "kuponkodceksatis", "title": "Kod-Çek İlan & İndirim satış", "members": 360, "type": "Kod & Çek İlan Satışı"},
    {"username": "kuponindirimcek", "title": "Kupon İndirim Fırsat", "members": 333, "type": "Kupon & İndirim Çek"},
    {"username": "kuponceksatisi", "title": "KUPON ÇEK KOD SATIŞI", "members": 321, "type": "Kupon, Çek & Kod Satışı"},
    {"username": "alisverisforumuguncel", "title": "🚀Alışveriş Forumu Kupon Satış", "members": 260, "type": "Kupon Satış & Forum"},
    {"username": "minakuponkodsatis", "title": "Kupon kod internet satış", "members": 233, "type": "Kupon & Kod Satış"},
    {"username": "kuponkodmerkez", "title": "🎁 Kupon & Çek Promosyon Kod", "members": 228, "type": "Kupon & Promosyon Kod"},
    {"username": "indirim363", "title": "KUPON-KOD SATIŞ GRUBU", "members": 218, "type": "Kupon & Kod Satışı"},
    {"username": "kuponkodhesapilan", "title": "Kupon kod ilan satış grubu", "members": 214, "type": "Kupon & Kod İlan Satışı"},
    {"username": "ceksatkupon2", "title": "Altın Sarı kupon kod alım satım", "members": 213, "type": "Kupon Kod Alım-Satım"},
    {"username": "kuponkodindirimilanlar", "title": "Kupon kod indirim ilanları", "members": 207, "type": "Kupon Kod İlanları"},
    {"username": "ceksatistakasgrup", "title": "Çek Satış Takas Paylaşım Grubu", "members": 206, "type": "Çek Satış & Takas"},
    {"username": "kuponyaticaret", "title": "Kuponya Çek Satış Platformu", "members": 180, "type": "Çek Satış Platformu"},
    {"username": "kuponvekodsatisgrubu", "title": "Kupon & Kod Satış Grubu", "members": 170, "type": "Kupon & Kod Satış"},
    {"username": "kodalimsatim", "title": "KUPON KOD ALIM-SATIM", "members": 169, "type": "Kupon & Kod Alım-Satım"},
    {"username": "kuponalsatgurup", "title": "KUPON KOD ALIM SATIM İLANLAR", "members": 138, "type": "Kupon Kod Alım-Satım İlan"},
    {"username": "uygunkod", "title": "Uygun Kod & Kupon Satış 🎫", "members": 136, "type": "Kod & Kupon Satışı"},
    {"username": "herkesibeklerimm", "title": "KODX Dijital Alım–Satım Grubu", "members": 134, "type": "Dijital Kod Alım-Satım"},
    {"username": "kodkuponmarketi", "title": "Kod & Kupon Marketi", "members": 121, "type": "Kod & Kupon Marketi"},
    {"username": "cek_kupon_kod_ilan", "title": "Kod & Çek İlanları", "members": 105, "type": "Kod & Çek İlanları"},
    {"username": "kodcek", "title": "Kupon & Çek Grubu", "members": 105, "type": "Kupon & Çek Grubu"},
    {"username": "satiskodtakasi", "title": "SATIŞ & KOD ALIŞ VERİŞ", "members": 98, "type": "Kod Alışveriş & Takas"},
    {"username": "kuponkodalsat", "title": "Kupon Kod Al Sat", "members": 88, "type": "Kupon Kod Al-Sat"},
    {"username": "indirimkana", "title": "KUPON & KOD MERKEZİ 🎟️", "members": 85, "type": "Kupon & Kod Merkezi"},
    {"username": "kuponhesap", "title": "Kupon Kod Hesap Alım Satım", "members": 85, "type": "Kupon Kod & Hesap"},
    {"username": "kod_promosyon", "title": "HADES KOD & PROMOSYON AVCISI", "members": 54, "type": "Promosyon & Kod Avcısı"},
    
    # Seyahat, Turna, Enuygun & Bilet Çekleri
    {"username": "enuygunarac", "title": "Enuygun & Turna Bilet/Araç Çek", "members": 220, "type": "Seyahat & Bilet Çekleri"},
    {"username": "turnabilet", "title": "Turna Uçak Bileti & Kupon Grubu", "members": 195, "type": "Turna Bilet & Kupon"},
    {"username": "enuygunbilet", "title": "Enuygun Bilet & Çek Pazarı", "members": 180, "type": "Enuygun Bilet & Çek"},
    {"username": "biletinialkod", "title": "Biletinial & Sinema Kupon Kod", "members": 150, "type": "Sinema & Etkinlik Kodları"},
    
    # İnternet GB & Promosyon Kapak/Cips Kodları (Kazandrio, Pepsi, DahaDaha)
    {"username": "bedavainternetkralligigrubu", "title": "Bedava İnternet Krallığı", "members": 12834, "type": "İnternet GB & Kodlar"},
    {"username": "bedavainternetyapilir", "title": "İnternet GB & Promosyon Kod", "members": 2061, "type": "İnternet GB & Promosyon"},
    {"username": "ceksatp8", "title": "Vodafone & Turkcell İnternet Kod", "members": 336, "type": "İnternet Data Kodları"},
    {"username": "bedavainternetkod", "title": "İnternet Kapak Kod Ticaret", "members": 248, "type": "Kapak & Promosyon Kodu"},
    {"username": "bedavainternetkodalimsatim", "title": "Bedava İnternet Kod Alım Satım", "members": 205, "type": "İnternet Kod Alım-Satım"},
    {"username": "kazandrio", "title": "KAZANDRİO KOD ALINIR💰", "members": 111, "type": "Kazandrio Kapak Kodu"},
    {"username": "kazandriokapakkodlari", "title": "Pepsi Kazandrio Kapak Kodları", "members": 101, "type": "Pepsi & Kazandrio Kod"},
    {"username": "kazandriiro", "title": "Kazandrio Kod Alım Satım", "members": 71, "type": "Kazandrio Kod Ticareti"},
    {"username": "dahadaha", "title": "Daha Daha Puan & Kod Pazarı", "members": 160, "type": "DahaDaha Puan & Kod"},
    {"username": "pepsikod", "title": "Pepsi & Cips Kod Alım Satım", "members": 145, "type": "Pepsi & Cips Kapak Kodu"},
    {"username": "cipskod", "title": "Cips Şerit Kod & Puan Grubu", "members": 130, "type": "Cips Şerit Kodları"},
    {"username": "frebaytgb", "title": "Freebayt GB & İnternet Kodları", "members": 115, "type": "Freebayt İnternet GB"},
    {"username": "freebayt", "title": "Freebayt Puan & Kod Ticareti", "members": 95, "type": "Freebayt Puan & Kod"},
    
    # Dijital Ticaret, SMS Onay & Hesap Pazarları
    {"username": "cepstokduyuru", "title": "Cepstok Destek & Kod Duyuru", "members": 17839, "type": "Promosyon & Servis Destek"},
    {"username": "alimsatimmerkezii", "title": "LORD- - ALIM SATIM MERKEZI", "members": 5496, "type": "Dijital Alım-Satım Merkezi"},
    {"username": "kuponprofesoruu", "title": "🎬 Kupon & Etkinlik Ödül Merkezi", "members": 4241, "type": "Kupon & Etkinlik Ödülleri"},
    {"username": "eticaretlab", "title": "E-ticaret & Dijital Pazar", "members": 3402, "type": "E-Ticaret & Dijital Pazar"},
    {"username": "sanalalimsatimticaret", "title": "Sanal Alım satım & Ticaret", "members": 3282, "type": "Sanal Ticaret Pazarı"},
    {"username": "kinseimedyaticaret", "title": "KINSEIMEDYA •️ TICARET 🇹🇷", "members": 3156, "type": "SMS Onay & Numara Ticareti"},
    {"username": "shopifyuzmani", "title": "E-ticaret & Dijital Pazar", "members": 2972, "type": "E-Ticaret Ticaret Grubu"},
    {"username": "ticaretguvenilir", "title": "Revenge / Ticaret Pazarı", "members": 2499, "type": "Güvenilir Ticaret Pazarı"},
    {"username": "ticar4t", "title": "Ticaret Grubu", "members": 2185, "type": "Ticaret & Alım-Satım"},
    {"username": "ticaretz", "title": "𝙏𝙄̇𝘾𝘼𝙍𝙀𝙏𝙕", "members": 1629, "type": "Dijital Ticaret Platformu"},
    {"username": "ilanticaret", "title": "Ticaret ve İlan Grubu - Sanal", "members": 1479, "type": "Sanal İlan & Ticaret"},
    {"username": "dijitalilan", "title": "Dijital İlanlar & Pazar", "members": 1394, "type": "Dijital İlanlar"},
    {"username": "mailalimsatimticaret", "title": "GMAİL ALIM-SATIM TİCARET 🤝", "members": 1285, "type": "Gmail & Hesap Ticareti"},
    {"username": "ticaretvarburada", "title": "Ticaret Var Burada", "members": 1259, "type": "Ticaret Pazarı"},
    {"username": "sterkpremium", "title": "STERK PREMİUM HESAPLAR", "members": 1096, "type": "Premium Hesap Satış"},
    {"username": "zeroticaret", "title": "Zero | Ticaret Grubu", "members": 977, "type": "Ticaret Grubu"},
    {"username": "ketenpereticaret", "title": "Ketenpere Ticaret", "members": 846, "type": "Sanal Numara & SMS Onay"},
    {"username": "baronalsatticaret", "title": "~Baron Alım Satım Ticaret~", "members": 757, "type": "Alım-Satım Ticaret"},
    {"username": "tsmticaret", "title": "Sosyal Medya Ticaret ve Paylaşım", "members": 759, "type": "Sosyal Medya Ticareti"},
    {"username": "ticaretcanavari", "title": "TICARET CANAVARI", "members": 741, "type": "Ticaret Pazarı"},
    {"username": "pixerdo", "title": "Gmail Alım - Satım 🎗️", "members": 717, "type": "Gmail & Dijital Hesap"},
    {"username": "kcksohbet", "title": "SOHBET ✍️ KuponÇek", "members": 877, "type": "Kupon & Çek Sohbet Pazarı"},
    {"username": "refkasaxmxma", "title": "REKLAM VE KAMPANYA GRUBU", "members": 494, "type": "Kampanya & Pazar Grubu"},
    {"username": "gmailalimsatimg", "title": "Gmail Alım-Satım & Yardımlaşma", "members": 476, "type": "Gmail Alım-Satım"},
    {"username": "megapaylasimlar", "title": "Premium Hesaplar & Kodlar", "members": 470, "type": "Premium Hesap & Kod"},
    {"username": "dijitalticaretgrubu", "title": "Dijital ticaret grubu", "members": 421, "type": "Dijital Ticaret Grubu"},
    {"username": "xalimsatiim", "title": "X Alım Satım & Ticaret", "members": 240, "type": "Alım-Satım & Ticaret"},
    {"username": "sanalposticaret", "title": "Sanal Pos TR (Ticaret)", "members": 183, "type": "Sanal Pos & Ticaret"},
    {"username": "turonay", "title": "TurOnay SMS & Numara Pazar", "members": 634, "type": "SMS Onay & Numara Ticareti"},
    {"username": "gmailmerkezi0", "title": "Gmail & Hesap Merkezi", "members": 1940, "type": "Hesap & Mail Pazarı"},
    {"username": "todtvkod", "title": "TOD TV / Süperlig Kod Pazarı", "members": 175, "type": "TOD TV Kodları"},
    {"username": "ssportkod", "title": "S Sport Plus Kupon & Kod", "members": 160, "type": "S Sport Kodları"},
    {"username": "alisverisceki", "title": "Alışveriş & Market Çek Pazarı", "members": 140, "type": "Alışveriş Çekleri"}
]

def finalize():
    print(f"Toplam saf kupon/kod grubu havuzu: {len(PURE_COUPON_TRADE_POOL)}")
    
    # Deduplicate and sort descending by member count
    seen = set()
    final_100 = []
    for g in sorted(PURE_COUPON_TRADE_POOL, key=lambda x: -x["members"]):
        u = g["username"].lower().lstrip("@")
        if u not in seen:
            seen.add(u)
            final_100.append(g)
            if len(final_100) == 100:
                break
                
    output = {
        "total_approved": len(final_100),
        "groups": final_100
    }
    
    with open("100_kesin_onayli_kupon_ve_kod_gruplari.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    with open("100_kupon_kod_gruplar_listesi.txt", "w", encoding="utf-8") as f:
        for g in final_100:
            f.write(f"@{g['username']}\n")

if __name__ == '__main__':
    finalize()
