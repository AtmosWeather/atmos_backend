import uuid
import tempfile # Keeping import just in case
import os
import urllib.parse
from fastapi import APIRouter, HTTPException, UploadFile, File
from firebase_admin import auth, storage, firestore
from pydantic import BaseModel
from typing import Optional
from app.services.firebase_service import get_db
from app.services.activity_service import get_all_user_activities

router = APIRouter()

class UserUpdate(BaseModel):
    displayName: Optional[str] = None
    password: Optional[str] = None
    photoUrl: Optional[str] = None
    notification: Optional[str] = None
    theme: Optional[str] = None

class FeedbackCreate(BaseModel):
    name: str
    email: str
    message: str
    photoUrl: Optional[str] = None

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

@router.get("/activities")
async def get_activities():
    try:
        page = auth.list_users()
        activities_data = await get_all_user_activities()
        users = []
        for user in page.users:
            if user.email and user.email.lower() == "admin@gmail.com":
                continue
                
            user_act = activities_data.get(user.uid, {})
            # fallback to email if uid not found
            if not user_act and user.email:
                user_act = activities_data.get(user.email, {})
                
            users.append({
                "uid": user.uid,
                "email": user.email,
                "displayName": user.display_name,
                "ai_calls": user_act.get("ai_calls", 0),
                "planner_tasks": user_act.get("planner_tasks", 0),
                "last_active": user_act.get("last_active", None)
            })
        return {"data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback")
async def get_feedback():
    try:
        db = get_db()
        users_docs = db.collection('users').stream()
        user_photo_map = {}
        for ud in users_docs:
            u_data = ud.to_dict()
            if u_data and "photoUrl" in u_data:
                user_photo_map[ud.id.lower()] = u_data["photoUrl"]
                
        # Also try to get from Firebase auth users if not in users collection
        page = auth.list_users()
        for u in page.users:
            if u.email and u.email.lower() not in user_photo_map and u.photo_url:
                user_photo_map[u.email.lower()] = u.photo_url

        docs = db.collection('contact_messages').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        messages = []
        for doc in docs:
            data = doc.to_dict()
            email = data.get("email", "No Email")
            
            # Use provided photoUrl, or fallback to user database
            photo_url = data.get("photoUrl", None)
            if not photo_url and email.lower() in user_photo_map:
                photo_url = user_photo_map[email.lower()]
                
            msg_data = {
                "id": doc.id,
                "name": data.get("name", "Unknown"),
                "email": email,
                "message": data.get("message", ""),
                "photoUrl": photo_url,
                "status": data.get("status", "unread"),
            }
            timestamp = data.get("timestamp")
            if timestamp and hasattr(timestamp, "isoformat"):
                msg_data["timestamp"] = timestamp.isoformat()
            
            messages.append(msg_data)
        return {"data": messages}
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate):
    try:
        db = get_db()
        db.collection('contact_messages').add({
            'name': feedback.name,
            'email': feedback.email,
            'message': feedback.message,
            'photoUrl': feedback.photoUrl,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'unread'
        })
        return {"message": "Feedback sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/feedback/{message_id}")
async def update_feedback_status(message_id: str, status_data: dict):
    try:
        db = get_db()
        new_status = status_data.get("status", "read")
        db.collection('contact_messages').document(message_id).update({"status": new_status})
        return {"message": "Status updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/feedback/{message_id}")
async def delete_feedback(message_id: str):
    try:
        db = get_db()
        db.collection('contact_messages').document(message_id).delete()
        return {"message": "Feedback deleted successfully", "id": message_id}
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
