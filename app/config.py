import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY")
    MONGODB_URI: str = os.getenv("MONGODB_URI")
    CUSTOM_TOKEN: str = os.getenv("CUSTOM_TOKEN")
    
settings = Settings()