import os

# Whitelisted/target groups in otomatik_katil.py
whitelist_groups = [
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

# Auto groups
auto_groups = []
if os.path.exists("auto_groups.txt"):
    with open("auto_groups.txt", "r", encoding="utf-8") as f:
        for line in f:
            g = line.strip().lower()
            if g:
                auto_groups.append(g)

all_targets = set(w.lower() for w in whitelist_groups).union(set(auto_groups))

# Load blacklist
blacklist = set()
if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r", encoding="utf-8") as f:
        for line in f:
            g = line.strip().lower()
            if g:
                blacklist.add(g)

print(f"Total target groups (whitelist + auto): {len(all_targets)}")
print(f"Total blacklisted groups: {len(blacklist)}")

blacklisted_targets = all_targets.intersection(blacklist)
print(f"\nBlacklisted target groups ({len(blacklisted_targets)}):")
for g in sorted(blacklisted_targets):
    print(f"  - {g}")
