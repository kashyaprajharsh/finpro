from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    name: str
    session_id: str

class UserInput(BaseModel):
    input: str
    username: str
    session_id: str
    paths: List[str]

class ClearHistoryInput(BaseModel):
    username: str
    session_id: str

class FeedbackInput(BaseModel):
    message_id: str
    feedback_type: str
    score: float
    comment: Optional[str] = None