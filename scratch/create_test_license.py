import sys
sys.path.append('.')
import user_db

res = user_db.create_license("TESTKEY-123456", 30)
if res:
    print("Test license key created successfully: TESTKEY-123456")
else:
    print("Failed to create test license key.")
