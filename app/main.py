import nltk
import os

nltk_data_path = os.path.expanduser("~/nltk_data")
if not os.path.exists(os.path.join(nltk_data_path, "sentiment", "vader_lexicon.txt")):
    nltk.download("vader_lexicon", quiet=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)