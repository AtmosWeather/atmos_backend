import os
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

async def get_ai_response(message: str) -> str:
    if not MAKE_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="MAKE_WEBHOOK_URL is not configured in .env")

    try:
        async with httpx.AsyncClient() as client:
            # The Make.com scenario expects "city" based on the URL ?city=...
            # We'll pass both "message", "city", and "?city" to cover all bases
            # It's highly likely they mapped a variable named literally `?city` in Make
            params = {
                "message": message,
                "city": message,
                "?city": message
            }
            response = await client.get(MAKE_WEBHOOK_URL, params=params, timeout=30.0)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Assuming the webhook returns {"response": "ai text"} or similar
                    if "response" in data:
                        return data["response"]
                    elif "message" in data:
                        return data["message"]
                    else:
                        return str(data)  # fallback to stringified json
                except Exception:
                    # If response is not JSON, just return the raw text
                    return response.text if response.text else "Message sent to Make.com successfully."
            else:
                print(f"Webhook error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Error from AI Webhook")

    except httpx.RequestError as e:
        print(f"Error connecting to Make.com Webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reach AI service")
