from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from app.models import UserInput, User, UserCreate, UserLogin, ClearHistoryInput, FeedbackInput
from app.services.auth import register_user, login_user, authenticate_user, verify_token
from app.services.chat import chat, clear_history, submit_feedback
from app.database import users_collection
from app.api.dependencies import get_rag_chain, store

router = APIRouter()

@router.post("/chat/")
async def chat_endpoint(user_input: UserInput, background_tasks: BackgroundTasks):
    return await chat(user_input, background_tasks)

@router.post("/register", response_model=User)
async def register_endpoint(user: UserCreate):
    try:
        return await register_user(user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/login", response_model=User)
async def login_endpoint(user: UserLogin):
    return await login_user(user)

@router.post("/clear_history/")
async def clear_history_endpoint(clear_input: ClearHistoryInput):
    return await clear_history(clear_input)

@router.get("/user_messages/")
async def get_user_messages(username: str):
    user = await users_collection.find_one({"username": username}, projection={"messages": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.get("messages", [])

@router.post("/feedback/")
async def feedback_endpoint(feedback: FeedbackInput, username: str = Query(...)):
    try:
        return await submit_feedback(feedback, username)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
