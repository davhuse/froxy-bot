import os
import json
import time
import asyncio
import logging
from telethon import Button

logger = logging.getLogger(__name__)

LEADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lead_interactions.json")

def _load_leads():
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load leads file: {e}")
    return {}

def _save_leads(data):
    try:
        temp_file = f"{LEADS_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, LEADS_FILE)
    except Exception as e:
        logger.warning(f"Failed to save leads file: {e}")

def record_lead_interaction(user_id, product_name=None):
    """Kullanıcının bota gelişini veya ürün incelemesini kaydeder."""
    try:
        leads = _load_leads()
        uid = str(user_id)
        current = leads.get(uid, {})
        # Eğer zaten retarget edilmişse tekrar rahatsız etmeyelim (veya 7 gün geçtiyse sıfırlanabilir)
        leads[uid] = {
            "last_seen": int(time.time()),
            "product": product_name or current.get("product", ""),
            "retargeted": current.get("retargeted", False),
            "created_at": current.get("created_at", int(time.time()))
        }
        _save_leads(leads)
    except Exception as e:
        logger.warning(f"record_lead_interaction error: {e}")

async def run_retargeting_loop(bot):
    """Arka planda çalışıp 12-36 saat önce gelen ve alım yapmayan kullanıcılara GERİGEL10 kodunu DM atar."""
    logger.info("Retargeting worker başlatıldı.")
    while True:
        try:
            await asyncio.sleep(1800)  # Her 30 dakikada bir kontrol et
            now = int(time.time())
            leads = _load_leads()
            updated = False

            for uid, record in list(leads.items()):
                if record.get("retargeted", False):
                    continue

                last_seen = record.get("last_seen", 0)
                diff_hours = (now - last_seen) / 3600.0

                # 12 saat ile 48 saat arasında olan ve henüz retarget edilmemiş kullanıcılara mesaj at
                if 12.0 <= diff_hours <= 48.0:
                    user_id = int(uid)
                    product = record.get("product")
                    
                    prod_text = f"incelediğiniz {product}" if product else "ürünlerimizi"
                    
                    message = (
                        f"Merhaba!\n\n"
                        f"KeyVadi mağazamızda {prod_text} henüz satın almadığınızı fark ettik. "
                        f"Aklınıza takılan bir soru veya yardıma ihtiyacınız varsa doğrudan bu mesaja yanıt verebilirsiniz.\n\n"
                        f"Siparişinizi tamamlamanız için size özel indirim kodu tanımladık:\n"
                        f"İndirim Kodu: GERİGEL10\n"
                        f"(Shopier ödeme sayfasında kodu girerek anında %10 indirimden faydalanabilirsiniz)\n\n"
                        f"Alışverişe devam etmek için aşağıdaki butona tıklayabilirsiniz."
                    )
                    
                    buttons = [
                        [Button.inline("Mağazayı Aç", b"menu_main")]
                    ]

                    try:
                        await bot.send_message(user_id, message, buttons=buttons)
                        logger.info(f"Retargeting DM gönderildi: {user_id}")
                        record["retargeted"] = True
                        record["retargeted_at"] = now
                        updated = True
                    except Exception as send_err:
                        logger.warning(f"Retargeting DM gönderilemedi ({user_id}): {send_err}")
                        # Engellemiş veya silmiş olabilir, tekrar denememek için retargeted işaretle
                        record["retargeted"] = True
                        updated = True

            if updated:
                _save_leads(leads)

        except Exception as loop_err:
            logger.error(f"Retargeting loop error: {loop_err}")
            await asyncio.sleep(60)
