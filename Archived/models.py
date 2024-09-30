from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    session_id: str

class UserInput(BaseModel):
    input: str
    username: str
    session_id: str

class ClearHistoryInput(BaseModel):
    username: str
    session_id: str