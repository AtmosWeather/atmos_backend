from firebase_admin import firestore
from app.services.firebase_service import get_db
import datetime

async def update_user_activity(user_email: str, activity_type: str):
    """
    Update the user's activity statistics.
    activity_type can be 'ai' or 'planner'.
    """
    try:
        db = get_db()
        # Ensure we are using the user_activities collection tied to the user's email
        activity_ref = db.collection('user_activities').document(user_email)
        
        # We use transaction or set with merge
        # but for simple increments, FieldValue.increment is best
        update_data = {
            "last_active": firestore.SERVER_TIMESTAMP
        }
        
        if activity_type == 'ai':
            update_data["ai_calls"] = firestore.Increment(1)
        elif activity_type == 'planner':
            update_data["planner_tasks"] = firestore.Increment(1)
            
        activity_ref.set(update_data, merge=True)
    except Exception as e:
        print(f"Error updating user activity for {user_email}: {e}")

async def get_all_user_activities():
    """
    Fetch all user activities from Firestore.
    """
    try:
        db = get_db()
        docs = db.collection('user_activities').stream()
        activities = {}
        for doc in docs:
            data = doc.to_dict()
            # Convert timestamp to ISO string if needed
            last_active = data.get("last_active")
            if last_active and hasattr(last_active, "isoformat"):
                last_active = last_active.isoformat()
            
            activities[doc.id] = {
                "ai_calls": data.get("ai_calls", 0),
                "planner_tasks": data.get("planner_tasks", 0),
                "last_active": last_active
            }
        return activities
    except Exception as e:
        print(f"Error fetching user activities: {e}")
        return {}
