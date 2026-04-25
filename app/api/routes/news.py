from fastapi import APIRouter, HTTPException, Path
from typing import List
from app.schemas.news import WeatherUpdate, WeatherUpdateResponse
from app.services.firebase_service import get_db

router = APIRouter()

COLLECTION_NAME = "weather_updates"

@router.get("/", response_model=List[WeatherUpdateResponse])
async def get_weather_updates():
    try:
        db = get_db()
        docs = db.collection(COLLECTION_NAME).order_by("date").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            # Skip archived weather updates
            if data.get("archived") == True:
                continue
            data["id"] = doc.id
            results.append(WeatherUpdateResponse(**data))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch updates: {str(e)}")

@router.post("/", response_model=WeatherUpdateResponse)
async def create_weather_update(update: WeatherUpdate):
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document()
        doc_ref.set(update.model_dump() if hasattr(update, "model_dump") else update.dict())
        
        data = update.model_dump() if hasattr(update, "model_dump") else update.dict()
        data["id"] = doc_ref.id
        return WeatherUpdateResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create update: {str(e)}")

@router.put("/{update_id}", response_model=WeatherUpdateResponse)
async def update_weather_update(update_id: str, update: WeatherUpdate):
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document(update_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Update not found")
        
        doc_ref.update(update.model_dump() if hasattr(update, "model_dump") else update.dict())
        
        data = update.model_dump() if hasattr(update, "model_dump") else update.dict()
        data["id"] = update_id
        return WeatherUpdateResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit update: {str(e)}")

@router.delete("/{update_id}")
async def delete_weather_update(update_id: str):
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document(update_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Update not found")
            
        doc_ref.update({"archived": True})
        return {"message": "Update archived successfully", "id": update_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete update: {str(e)}")
