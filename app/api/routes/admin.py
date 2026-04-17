import uuid
import tempfile # Keeping import just in case
import os
import urllib.parse
from fastapi import APIRouter, HTTPException, UploadFile, File
from firebase_admin import auth, storage
from pydantic import BaseModel
from typing import Optional
from app.services.firebase_service import get_db

router = APIRouter()

class UserUpdate(BaseModel):
    displayName: Optional[str] = None
    password: Optional[str] = None
    photoUrl: Optional[str] = None
    notification: Optional[str] = None
    theme: Optional[str] = None

@router.get("/users")
async def get_users():
    try:
        page = auth.list_users()
        users = []
        for user in page.users:
            users.append({
                "uid": user.uid,
                "email": user.email,
                "displayName": user.display_name,
                "creationTime": user.user_metadata.creation_timestamp,
                "lastSignInTime": user.user_metadata.last_sign_in_timestamp
            })
        return {"data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{uid}")
async def update_user(uid: str, update_data: UserUpdate):
    try:
        kwargs = {"display_name": update_data.displayName}
        pwd = update_data.password
        if pwd and pwd.strip():
            kwargs["password"] = pwd.strip()
        photo = update_data.photoUrl
        notification = update_data.notification
        theme = update_data.theme
        
        if (photo and isinstance(photo, str)) or (notification and isinstance(notification, str)) or (theme and isinstance(theme, str)):
            db = get_db()
            user_record = auth.get_user(uid)
            email = user_record.email
            update_payload = {}
            if photo and isinstance(photo, str):
                update_payload["photoUrl"] = photo
            if notification and isinstance(notification, str):
                update_payload["notification"] = notification
            if theme and isinstance(theme, str):
                update_payload["theme"] = theme
            db.collection("users").document(email).set(update_payload, merge=True)
            
        auth.update_user(uid, **kwargs)
        return {"message": "User updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{uid}")
async def delete_user(uid: str):
    try:
        auth.delete_user(uid)
        return {"message": "User deleted successfully", "uid": uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        bucket = storage.bucket()
        # Create a unique filename
        filename = f"news_images/{uuid.uuid4()}_{file.filename}"
        blob = bucket.blob(filename)
        
        # Upload entirely from memory, avoiding Windows locked file handle exceptions entirely
        file_bytes = await file.read()
        print(f"Uploading {len(file_bytes)} bytes to {filename}...", flush=True)
        import asyncio
        import functools
        loop = asyncio.get_event_loop()
        upload_func = functools.partial(blob.upload_from_string, file_bytes, content_type=file.content_type)
        await loop.run_in_executor(None, upload_func)
        print("Upload successful!", flush=True)
        
        # Bypass make_public() to prevent Uniform Bucket-Level Access 403 Forbidden exceptions
        encoded_name = urllib.parse.quote(filename, safe='')
        download_url = f"https://firebasestorage.googleapis.com/v0/b/atmos-6f7c6.appspot.com/o/{encoded_name}?alt=media"
        
        return {"imageUrl": download_url}
    except Exception as e:
        print(f"UPLOAD EXCEPTION: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
