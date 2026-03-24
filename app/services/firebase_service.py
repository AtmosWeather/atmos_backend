import os
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

db = None

def init_firebase():
    global db
    if not firebase_admin._apps:
        # Check for service account file
        cred_path = os.path.join(os.path.dirname(__file__), "..", "core", "firebase-service-account.json")
        fallback_path = os.path.join(os.path.dirname(__file__), "..", "..", "atmos-6f7c6-firebase-adminsdk-fbsvc-072956756f.json")
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        elif os.path.exists(fallback_path):
            cred = credentials.Certificate(fallback_path)
        else:
            # Fallback for when the user might have set GOOGLE_APPLICATION_CREDENTIALS
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                cred = credentials.ApplicationDefault()
            else:
                # We can't initialize without credentials
                print("WARNING: Firebase Admin SDK credentials not found. Firestore will not work.")
                return

        try:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {str(e)}")

def get_db():
    if db is None:
        raise HTTPException(status_code=500, detail="Firebase Database not initialized. Please configure the service account.")
    return db

async def save_chat_message(user_id: str, message: str, is_user: bool):
    try:
        db_client = get_db()
        # Save to users/{user_id}/chats collection
        chat_ref = db_client.collection('users').document(user_id).collection('chats').document()
        chat_data = {
            "text": message,
            "isUser": is_user,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        chat_ref.set(chat_data)
        return {"id": chat_ref.id, "text": message, "isUser": is_user}
    except Exception as e:
        print(f"Error saving to Firestore: {str(e)}")
        # We might not want to crash the app if analytics/saving fails
        return {"error": str(e)}

async def get_chat_history(user_id: str):
    try:
        db_client = get_db()
        chats_ref = db_client.collection('users').document(user_id).collection('chats')
        # Order by timestamp ascending
        query = chats_ref.order_by("timestamp", direction=firestore.Query.ASCENDING)
        docs = query.stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append({
                "id": doc.id,
                "text": data.get("text", ""),
                "isUser": data.get("isUser", False)
            })
        return history
    except Exception as e:
        print(f"Error fetching from Firestore: {str(e)}")
        return []

async def delete_chat_history(user_id: str):
    try:
        db_client = get_db()
        chats_ref = db_client.collection('users').document(user_id).collection('chats')
        docs = chats_ref.stream()
        
        # Firestore recommended way to delete a collection is to delete all its documents
        batch = db_client.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count >= 400: # Batch limit is 500
                batch.commit()
                batch = db_client.batch()
                count = 0
                
        if count > 0:
            batch.commit()
            
        return {"success": True, "message": "Conversation deleted"}
    except Exception as e:
        print(f"Error deleting chat history: {str(e)}")
        return {"success": False, "error": str(e)}
