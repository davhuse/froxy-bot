import os

gruplar = [
    "ticaretforumofficial",
    "sultanbeyliikinciel0",
    "tahaaslan11",
    "casinox_grup",
    "ReklamOnliene",
    "alimsatimmerkezii",
    "illegalalimsatimerkezi",
    "ilanticaret",
    "reklamreferans",
    "sosyalmedyaalimsatimticaret",
    "ReferansReklamYardimlasma",
    "sanalalimsatimticaret",
    "kuponsatisgrup",
    "referansreklam1",
    "referanslinkpaylasimigrup",
    "kuponsatislari0",
    "YuceKuponSatis",
    "letgoilanlari",
    "-1001572316417",
    "-3608209943",
    "ticar4t",
    "kuponhesapsatis",
    "reklamvereferanss",
    "kuponvekodsatisgrubu",
    "indirimkodusatis",
]

with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = set(line.strip().lower() for line in f if line.strip())

print("Checking whitelisted/target groups in blacklist.txt:")
found_in_blacklist = []
for g in gruplar:
    if g.lower() in blacklist:
        found_in_blacklist.append(g)
        print(f"  BLACKLISTED: {g}")
        
if not found_in_blacklist:
    print("  None of the whitelisted/target groups are in blacklist.txt!")
else:
    print(f"Total whitelisted groups in blacklist: {len(found_in_blacklist)}")
