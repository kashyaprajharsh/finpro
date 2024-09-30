from datetime import datetime, UTC
from fastapi import HTTPException, BackgroundTasks
from models import UserInput, ClearHistoryInput
from database import users_collection
from api.dependencies import get_rag_chain, store
from loguru import logger
import uuid

async def update_user_messages(username: str, session_id: str, new_message: dict):
    await users_collection.update_one(
        {"username": username, "session_id": session_id},
        {
            "$push": {"messages": new_message},
            "$set": {"updated_at": datetime.now()}
        }
    )

async def chat(user_input: UserInput, background_tasks: BackgroundTasks):
    try:
        chain = get_rag_chain()
        response = chain.invoke(
            {"input": user_input.input},
            {"configurable": {"session_id": user_input.session_id}}
        )
        
        message_id = str(uuid.uuid4())
        new_message = {
            "id": message_id,
            "input": user_input.input,
            "output": response["answer"],
            "timestamp": datetime.now(UTC)
        }
        
        background_tasks.add_task(update_user_messages, user_input.username, user_input.session_id, new_message)
        
        return {
            "session_id": user_input.session_id,
            "response": response["answer"],
            "message_id": message_id
        }
    except Exception as e:
        logger.error(f"Error in chat function: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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