import asyncio
from firebase_companion import async_get_document

async def main():
    doc = await async_get_document("ad_health_alert_state")
    print(doc)
    
asyncio.run(main())
