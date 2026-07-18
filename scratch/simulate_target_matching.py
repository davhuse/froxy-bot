import os
import json

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

protected_groups = set(g.lower() for g in whitelist_groups)
if os.path.exists("auto_groups.txt"):
    with open("auto_groups.txt", "r", encoding="utf-8") as f:
        for line in f:
            g = line.strip().lower()
            if g:
                protected_groups.add(g)

# Simulate Hesap #3 joined dialogs (only 1 group in the dialogs list)
# Real ID for ReklamOnliene is -1001790937453
joined_dialogs = {
    "reklamonliene": "entity_reklamonliene",
    "-1001790937453": "entity_reklamonliene"
}

blacklist = set()
if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r", encoding="utf-8") as f:
        for line in f:
            g = line.strip().lower()
            if g:
                blacklist.add(g)

hedef_set = protected_groups.copy()
for g_key in joined_dialogs:
    hedef_set.add(g_key)

print(f"Total hedef_set: {len(hedef_set)}")
print(f"hedef_set elements: {sorted(list(hedef_set))}")

debug_blacklisted = 0
debug_not_cached = 0
blast_targets = []

for username_lower in hedef_set:
    if username_lower in blacklist:
        debug_blacklisted += 1
        print(f"  - Blacklisted: {username_lower}")
        continue
    if username_lower in joined_dialogs:
        blast_targets.append(username_lower)
    else:
        debug_not_cached += 1
        print(f"  - Not joined: {username_lower}")

print(f"\nResults:")
print(f"  Hedef: {len(hedef_set)}")
print(f"  Gönderilecek: {len(blast_targets)}")
print(f"  Kara liste: {debug_blacklisted}")
print(f"  Üye değil: {debug_not_cached}")
