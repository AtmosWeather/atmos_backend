from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.ai_service import get_ai_response
from app.services.firebase_service import save_chat_message, get_chat_history, delete_chat_history
from app.services.activity_service import update_user_activity

router = APIRouter()

@router.get("/history")
async def fetch_chat_history(userId: str):
    history = await get_chat_history(userId)
    return {"history": history}

@router.delete("/history")
async def clear_chat_history(userId: str):
    result = await delete_chat_history(userId)
    return result


class ChatRequest(BaseModel):
    userId: str
    message: str

class ChatResponse(BaseModel):
    message: str
    success: bool = True

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    # 1. Save User Message to Firestore
    user_save_result = await save_chat_message(request.userId, request.message, is_user=True)
    if not user_save_result or "error" in user_save_result:
        print(f"Warning: Failed to save user message to Firestore - {user_save_result}")

    # 2. Get AI Response from Make.com Webhook
    ai_response_text = await get_ai_response(request.message)

    # 3. Save AI Response to Firestore
    ai_save_result = await save_chat_message(request.userId, ai_response_text, is_user=False)
    if not ai_save_result or "error" in ai_save_result:
        print(f"Warning: Failed to save AI response to Firestore - {ai_save_result}")

    # 4. Update activity
    await update_user_activity(request.userId, 'ai')

    return ChatResponse(message=ai_response_text)
