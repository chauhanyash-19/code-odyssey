import asyncio
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings

async def test_whatsapp():
    print("\n--- Testing WhatsApp Business API ---")
    cfg = get_settings()
    
    if not cfg.whatsapp_phone_number_id or not cfg.whatsapp_access_token:
        print("FAIL: WhatsApp keys not set in .env")
        return
        
    url = f"https://graph.facebook.com/v21.0/{cfg.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {cfg.whatsapp_access_token}",
        "Content-Type": "application/json"
    }
    
    # Using a dummy destination number. The user is expected to put their actual test number here,
    # or we can just send it and observe the expected failure (number not allowed, etc).
    # Since I don't know their test number, I will use a dummy one. Meta should return a 400 error.
    dummy_number = "919876543210"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": dummy_number,
        "type": "text",
        "text": {"body": "PhaseGuard test message - API working"}
    }
    
    print(f"Sending POST to {url}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            print(f"HTTP Status: {response.status_code}")
            print(f"Raw Response Body: {response.text}")
    except Exception as e:
        print(f"Exception during request: {e}")

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
