import re

files = ["support_flow.py", "lisansarena_bot.py", "froxy_bot.py", "froxy_destek_bot.py"]

for fname in files:
    try:
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()
            
        # We want to replace:
        # except Exception:
        #     pass
        # return True
        # OR
        # except Exception:
        #     pass
        # 
        # return True
        # with:
        # except Exception as e:
        #     print(f"Claim error: {e}")
        #     return False
        
        # It's safer to use regex targeting the claim_event_locally_and_remotely and claim_support_event blocks
        
        # For lisansarena_bot.py:
        if "async def claim_event_locally_and_remotely" in content:
            content = re.sub(r"except Exception:\s*pass\s*return True", r"except Exception as e:\n        print(f'Claim error: {e}')\n        return False\n    return True", content)
            
        # For support_flow.py:
        if "async def claim_support_event" in content:
            content = re.sub(r"except Exception:\s*pass\s*return True", r"except Exception as e:\n        print(f'Claim error: {e}')\n        return False\n    return True", content)
            
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched {fname}")
    except Exception as e:
        print(f"Error patching {fname}: {e}")
