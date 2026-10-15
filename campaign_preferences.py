"""Per-customer campaign notification preferences."""
import firestore_helper


def notifications_enabled(brand, user_id):
    record = firestore_helper.get_document(f"campaign_pref_{brand}_{int(user_id)}") or {}
    return record.get("enabled", True) is not False


def set_notifications(brand, user_id, enabled):
    return firestore_helper.set_document(f"campaign_pref_{brand}_{int(user_id)}", {"enabled": bool(enabled)})
