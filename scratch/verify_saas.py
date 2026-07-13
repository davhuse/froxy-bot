import sys
sys.path.append('.')
import user_db

def test_saas_flow():
    print("=== SaaS Flow Verification ===")
    
    # 1. Try to register with invalid license key
    print("\nTesting registration with invalid license key...")
    res = user_db.register_user("testuser_invalid", "testpass123", "INVALIDKEY-999")
    print(f" -> Result: {res}")
    assert res["success"] is False, "Should fail with invalid key"
    
    # 2. Try to register with valid license key (TESTKEY-123456 created earlier)
    print("\nTesting registration with valid license key...")
    res = user_db.register_user("testuser", "testpass123", "TESTKEY-123456")
    print(f" -> Result: {res}")
    if not res["success"]:
        # If it was already claimed in previous tests, that's fine, let's check if we can log in
        if "zaten alınmış" in res["message"] or "zaten kullanılmış" in res["message"]:
            print(" -> User or key already exists, proceeding to login test.")
        else:
            raise AssertionError("Registration failed: " + res["message"])
            
    # 3. Verify Login
    print("\nTesting login...")
    res = user_db.login_user("testuser", "testpass123")
    print(f" -> Result: {res}")
    assert res["success"] is True, "Login failed"
    
    # 4. Verify Config Saving and Loading
    print("\nTesting config saving/loading...")
    user_id = "testuser"
    cfg = user_db.get_user_config(user_id)
    print(f" -> Original Config: {cfg}")
    
    cfg["bot_token"] = "987654321:XYZabc_test_token"
    cfg["ad_sleep_min"] = 300
    cfg["ad_sleep_max"] = 500
    cfg["ad_string_session"] = "TEST_STRING_SESSION_TOKEN_123"
    
    save_res = user_db.save_user_config(user_id, cfg)
    print(f" -> Save Result: {save_res}")
    assert save_res is True, "Config saving failed"
    
    loaded_cfg = user_db.get_user_config(user_id)
    print(f" -> Loaded Config: {loaded_cfg}")
    assert loaded_cfg["bot_token"] == cfg["bot_token"], "Token mismatch"
    assert loaded_cfg["ad_sleep_min"] == 300, "Min sleep mismatch"
    assert loaded_cfg["ad_string_session"] == "TEST_STRING_SESSION_TOKEN_123", "String session mismatch (encryption/decryption failed)"
    
    print("\n✅ All SaaS DB & Encryption Tests PASSED!")

if __name__ == "__main__":
    test_saas_flow()
