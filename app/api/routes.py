from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from models import UserInput, User, UserCreate, UserLogin, ClearHistoryInput
from services.auth import register_user, login_user,authenticate_user,verify_token
from services.chat import chat, clear_history
from database import users_collection

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