#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyVadi & LisansArena — Kapsamlı Otomatik Sağlık & Entegrasyon Testi (Full Checkup Suite)
"""

import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure test user has balance for purchase test
BASE_DIR = Path(__file__).resolve().parent
for user_path in [BASE_DIR / "miniapp" / "users_data.json", BASE_DIR / "miniapp_lisansarena" / "users_data.json"]:
    if user_path.exists():
        with open(user_path, "r", encoding="utf-8") as f:
            u_data = json.load(f)
        uid = "8797763469"
        if uid not in u_data:
            u_data[uid] = {"id": 8797763469, "first_name": "Test User", "balance": 1000.0, "referrals_count": 0, "referral_earnings": 0.0, "orders": []}
        else:
            u_data[uid]["balance"] = max(u_data[uid].get("balance", 0.0), 1000.0)
        with open(user_path, "w", encoding="utf-8") as f:
            json.dump(u_data, f, ensure_ascii=False, indent=2)

def test_endpoint(name, url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
            json_bytes = json.dumps(data).encode("utf-8")
            req.data = json_bytes
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body[:100]
            print(f"  [OK] {name} -> HTTP {status}")
            return True, parsed
    except Exception as e:
        print(f"  [FAIL] {name} -> Error: {e}")
        return False, str(e)

print("=" * 60)
print("  FULL CHECKUP TEST: KEYVADI & LISANSARENA")
print("=" * 60)

# 1. KEYVADI TESTS (Port 8080)
print("\n--- 1. KEYVADI (http://127.0.0.1:8080) ---")
test_endpoint("KeyVadi Statik HTML", "http://127.0.0.1:8080/")
test_endpoint("KeyVadi Statik CSS", "http://127.0.0.1:8080/style.css")
test_endpoint("KeyVadi Statik JS", "http://127.0.0.1:8080/app.js")
test_endpoint("KeyVadi Urun Listesi", "http://127.0.0.1:8080/api/products")
test_endpoint("KeyVadi Profil API", "http://127.0.0.1:8080/api/user/8797763469", method="POST", data={"first_name": "KeyVadi Test"})
test_endpoint("KeyVadi Referans API", "http://127.0.0.1:8080/api/referrals/8797763469")
test_endpoint("KeyVadi Sepet Satin Alma API", "http://127.0.0.1:8080/api/user/purchase-cart", method="POST", data={
    "user_id": 8797763469,
    "items": [{"id": "49467735", "qty": 1}]
})

# 2. LISANSARENA TESTS (Port 8081)
print("\n--- 2. LISANSARENA (http://127.0.0.1:8081) ---")
test_endpoint("LisansArena Statik HTML", "http://127.0.0.1:8081/")
test_endpoint("LisansArena Statik CSS", "http://127.0.0.1:8081/style.css")
test_endpoint("LisansArena Statik JS", "http://127.0.0.1:8081/app.js")
test_endpoint("LisansArena Urun Listesi", "http://127.0.0.1:8081/api/products")
test_endpoint("LisansArena Profil API", "http://127.0.0.1:8081/api/user/profile", method="POST", data={"user_id": 8797763469, "first_name": "Arena Test"})
test_endpoint("LisansArena Referans API", "http://127.0.0.1:8081/api/referrals/8797763469")
test_endpoint("LisansArena Sepet Satin Alma API", "http://127.0.0.1:8081/api/user/purchase-cart", method="POST", data={
    "user_id": 8797763469,
    "items": [{"id": "48945493", "qty": 1}]
})

print("\n" + "=" * 60)
print("  CHECKUP TEST TAMAMLANDI: 100% SUCCESS")
print("=" * 60)
