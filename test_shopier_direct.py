import sys
from miniapp.shopier_dynamic import create_dynamic_shopier_listing

res = create_dynamic_shopier_listing(
    amount=10.0,
    user_id=6196006704,
    user_name="Test User",
    username="testuser",
    persist_local=False
)
print("KeyVadi Shopier Listing Result:")
print(res)
