# -*- coding: utf-8 -*-
import re

with open("froxy_bot.py", "r", encoding="utf-8") as f:
    content = f.read()

if "from license_delivery import allocate_license" not in content:
    content = content.replace("from shopier_orders import", "from license_delivery import allocate_license\nfrom shopier_orders import")

match = re.search(r"# Check license category.*?json\.dump\(stocks, f.*?except Exception as e:.*?print\(.*?licenses\.json.*?e\)", content, re.DOTALL)
if match:
    replacement = """        # Use global license delivery system
        alloc = allocate_license(prod_name, brand="keyvadi")
        license_key = alloc.get("license_key")
        
        # Save order to keyvadi_users_data so it shows in /siparisler
        user_orders_doc = await async_get_document("keyvadi_users_data")
        u_data = user_orders_doc.get("users", {}) if user_orders_doc else {}
        str_uid = str(user_id)
        if str_uid not in u_data:
            u_data[str_uid] = {
                "id": user_id, "username": getattr(event.sender, "username", ""),
                "first_name": getattr(event.sender, "first_name", "Musteri"),
                "balance": 0.0, "orders": []
            }
        u_data[str_uid].setdefault("orders", []).append({
            "order_id": unclaimed_order.get("order_id"),
            "product_name": unclaimed_order.get("product_name"),
            "title": unclaimed_order.get("product_name"),
            "price": unclaimed_order.get("amount"),
            "status": alloc.get("status", "delivered" if license_key else "pending_delivery"),
            "license_key": license_key,
            "created_at": unclaimed_order.get("timestamp")
        })
        await async_set_document("keyvadi_users_data", {"users": u_data})
"""
    content = content[:match.start()] + replacement + content[match.end():]
    
    with open("froxy_bot.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched froxy_bot.py successfully.")
else:
    print("Could not find the block to patch in froxy_bot.py!")
