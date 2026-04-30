import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import httpx
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

class VerifyOtpRequest(BaseModel):
    email: str
    code: str

class ResendOtpRequest(BaseModel):
    email: str

def send_otp_email_helper(email: str):
    from app.services.firebase_service import get_db
    from firebase_admin import firestore
    db = get_db()
    otp_code = str(random.randint(100000, 999999))
    db.collection("otp_codes").document(email).set({
        "code": otp_code,
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    if SMTP_EMAIL and SMTP_PASSWORD:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        msg['Subject'] = "Your Atmos Verification Code"
        body = f"Your one-time verification code is: {otp_code}\n\nThis code is required to sign in to your account. It will expire in 5 minutes."
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_EMAIL, email, text)
        server.quit()
        print(f"OTP sent to {email}")
    else:
        print("SMTP_EMAIL or SMTP_PASSWORD not set. OTP stored but not sent.", flush=True)

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

            # Generate and send OTP
            try:
                send_otp_email_helper(email)
            except smtplib.SMTPAuthenticationError:
                raise HTTPException(status_code=500, detail="SMTP Auth Failed: Google requires an App Password instead of a regular password.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

            return {"message": "OTP sent", "requires_otp": True, "data": data}
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Firebase connection error: {str(e)}")

@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest):
    try:
        from app.services.firebase_service import get_db
        db = get_db()
        doc_ref = db.collection("otp_codes").document(req.email)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=400, detail="No OTP requested for this email.")
        
        doc_data = doc.to_dict()
        if doc_data.get("code") != req.code:
            raise HTTPException(status_code=400, detail="Invalid OTP code.")
            
        from datetime import datetime, timezone
        created_at = doc_data.get("createdAt")
        if created_at:
            time_diff = datetime.now(timezone.utc) - created_at
            if time_diff.total_seconds() > 300: # 5 minutes
                doc_ref.delete()
                raise HTTPException(status_code=400, detail="OTP code has expired. Please sign in again to request a new one.")
        
        # Delete OTP so it can't be reused
        doc_ref.delete()
        
        return {"message": "OTP verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resend-otp")
async def resend_otp(req: ResendOtpRequest):
    try:
        send_otp_email_helper(req.email)
        return {"message": "OTP resent successfully"}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="SMTP Authentication failed. Google requires you to use an App Password, not your regular password.")
    except Exception as e:
        print(f"Failed to resend OTP: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
