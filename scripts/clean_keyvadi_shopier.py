# -*- coding: utf-8 -*-
from pathlib import Path
import re

replacements = {
    "Shopier ile 3D Secure": "3D Secure",
    "Shopier altyapısıyla 3D Secure": "3D Secure",
    "Shopier 3D Secure": "3D Secure",
}

p = Path("messages")
for f in p.glob("*keyvadi*.txt"):
    text = f.read_text(encoding="utf-8")
    original = text
    for k, v in replacements.items():
        text = text.replace(k, v)
    if text != original:
        f.write_text(text, encoding="utf-8")
        print(f"Updated {f.name}")

