import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

FIREBASE_API_KEY = os.getenv("apiKey")
if FIREBASE_API_KEY and FIREBASE_API_KEY.endswith(","):
    FIREBASE_API_KEY = FIREBASE_API_KEY[:-1] # Remove trailing comma if exists

class UserCredentials(BaseModel):
    email: str
    password: str
    displayName: str = None

@router.post("/signup")
async def signup(user: UserCredentials):
    # 1. Create the user
    signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    signup_payload = {
        "email": user.email,
        "password": user.password,
        "returnSecureToken": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(signup_url, json=signup_payload)
            signup_data = response.json()
            
            if response.status_code != 200:
                error_message = signup_data.get("error", {}).get("message", "Unknown error")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
            
            # 2. Update profile with displayName if provided
            if user.displayName:
                id_token = signup_data.get("idToken")
                update_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={FIREBASE_API_KEY}"
                update_payload = {
                    "idToken": id_token,
                    "displayName": user.displayName,
                    "returnSecureToken": False
                }
                await client.post(update_url, json=update_payload)
                signup_data["displayName"] = user.displayName
                
            return {"message": "User created successfully", "data": signup_data}
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Firebase connection error: {str(e)}")

@router.post("/signin")
async def signin(user: UserCredentials):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": user.email,
        "password": user.password,
        "returnSecureToken": True
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if response.status_code != 200:
                error_message = data.get("error", {}).get("message", "Unknown error")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
            
            # Firebase signInWithPassword returns displayName if it exists
            email = user.email
            if email:
                try:
                    from app.services.firebase_service import get_db
                    db = get_db()
                    doc = db.collection("users").document(email).get()
                    if doc.exists:
                        user_data = doc.to_dict()
                        if user_data and "photoUrl" in user_data:
                            data["photoUrl"] = user_data["photoUrl"]
                        if user_data and "notification" in user_data:
                            data["notification"] = user_data["notification"]
                        if user_data and "theme" in user_data:
                            data["theme"] = user_data["theme"]
                except Exception as e:
                    print(f"Failed to fetch profile info from firestore: {e}", flush=True)

            return {"message": "Signed in successfully", "data": data}
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Firebase connection error: {str(e)}")
