# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path("messages")
kv_files = sorted(list(p.glob("*keyvadi*.txt")))

print(f"Found {len(kv_files)} KeyVadi template files:")
all_passed = True

for f in kv_files:
    content = f.read_text(encoding="utf-8")
    line_count = len(content.strip().splitlines())
    has_shopier = "shopier" in content.lower()
    has_bot = "@KeyVadiSatisBot" in content or "KeyVadiSatisBot" in content
    # Check for emojis (broad unicode range)
    has_emoji = bool(re.search(r'[\U00010000-\U0010ffff]', content))
    
    status = "OK"
    if line_count < 12:
        status = f"SHORT ({line_count} lines)"
        all_passed = False
    if has_shopier:
        status = "HAS SHOPIER"
        all_passed = False
    
    print(f"  {f.name:25} | Lines: {line_count:2} | Bot link: {has_bot} | Shopier: {has_shopier} | Emoji: {has_emoji} | Status: {status}")

print(f"\nAll KeyVadi templates passed verification: {all_passed}")
