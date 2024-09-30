import os
import uuid
import json
import calendar
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import UserInput, User, UserCreate, UserLogin, ClearHistoryInput
from functools import lru_cache
from google.generativeai.types import HarmCategory, HarmBlockThreshold

load_dotenv()

# Set up environment variables
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["finpro_db"]
users_collection = db["users"]

# Global variables
store = {}

@lru_cache(maxsize=1)
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")

@lru_cache(maxsize=1)
def get_vector_db():
    embeddings = get_embeddings()
    return PineconeVectorStore(embedding=embeddings, index_name="gemnivector")

@lru_cache(maxsize=1)
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.0-pro-latest",
        temperature=0,
        top_p=0.8,
        top_k=8,
        max_output_tokens=2048,
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        convert_system_message_to_human=True
    )

def get_rag_chain():
    vectorstore = get_vector_db()
    llm = get_llm()
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Answer the user's questions based on the below context {context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    return RunnableWithMessageHistory(
        rag_chain,
        lambda session_id: store.setdefault(session_id, []),
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

async def get_or_create_user(username: str, session_id: str):
    user = await users_collection.find_one({"username": username, "session_id": session_id})
    if not user:
        new_user = {
            "username": username,
            "session_id": session_id,
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        await users_collection.insert_one(new_user)
        return new_user
    return user

async def update_user_messages(username: str, session_id: str, new_message: dict):
    await users_collection.update_one(
        {"username": username, "session_id": session_id},
        {
            "$push": {"messages": new_message},
            "$set": {"updated_at": datetime.now()}
        }
    )

# Endpoints
@app.post("/chat/")
async def chat(user_input: UserInput, background_tasks: BackgroundTasks):
    try:
        user = await get_or_create_user(user_input.username, user_input.session_id)
        
        chain = get_rag_chain()
        response = chain.invoke(
            {"input": user_input.input},
            {"configurable": {"session_id": user_input.session_id}}
        )

        new_message = {
            "input": user_input.input,
            "output": response["answer"],
            "timestamp": datetime.utcnow()
        }
        
        background_tasks.add_task(update_user_messages, user_input.username, user_input.session_id, new_message)

        return {
            "session_id": user_input.session_id,
            "response": response["answer"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register", response_model=User)
async def register_user(user: UserCreate):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    session_id = str(uuid.uuid4())
    user_dict = user.dict()
    user_dict["session_id"] = session_id
    await users_collection.insert_one(user_dict)
    return User(username=user.username, session_id=session_id)

@app.post("/login", response_model=User)
async def login_user(user: UserLogin):
    db_user = await users_collection.find_one({"username": user.username, "password": user.password})
    if not db_user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return User(username=db_user["username"], session_id=db_user["session_id"])

@app.post("/clear_history/")
async def clear_history(clear_input: ClearHistoryInput):
    try:
        user = await users_collection.find_one({"username": clear_input.username, "session_id": clear_input.session_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if clear_input.session_id in store:
            del store[clear_input.session_id]
        
        await users_collection.update_one(
            {"username": clear_input.username, "session_id": clear_input.session_id},
            {"$set": {"messages": []}}
        )
        
        return {"message": "Conversation history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)