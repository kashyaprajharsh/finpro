import uuid
from fastapi import HTTPException, Depends
from models import UserCreate, UserLogin, User
from database import users_collection
from config import settings
from loguru import logger
from functools import lru_cache
from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, HTTPException, status, Depends,BackgroundTasks



@lru_cache(maxsize=128)
def verify_token_cached(token: str):
    return token == settings.CUSTOM_TOKEN

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def verify_token(token: str = Depends(oauth2_scheme)):
    if not verify_token_cached(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# Helper functions
async def authenticate_user(username: str, password: str):
    user_dict = await users_collection.find_one(
        {"username": username, "password": password},
        projection={"_id": 0, "username": 1, "name": 1, "session_id": 1}
    )
    if user_dict:
        logger.info(f"User authenticated: {username}")
        return User(**user_dict)
    logger.info(f"Authentication failed for user: {username}")
    return None


async def register_user(user: UserCreate):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    session_id = str(uuid.uuid4())
    user_dict = user.model_dump()
    user_dict["session_id"] = session_id
    await users_collection.insert_one(user_dict)
    return User(username=user.username, name=user.name, session_id=session_id)


async def login_user(user: UserLogin):
    authenticated_user = await authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return authenticated_user