from datetime import datetime, UTC
from fastapi import HTTPException, BackgroundTasks
from app.models import UserInput, ClearHistoryInput, FeedbackInput
from app.database import users_collection
from app.api.dependencies import get_rag_chain, store
from loguru import logger
import uuid
from langkit.openai import OpenAILegacy
from langkit import llm_metrics
import whylogs as why
from whylogs.experimental.core.udf_schema import udf_schema

async def update_user_messages(username: str, session_id: str, new_message: dict):
    await users_collection.update_one(
        {"username": username, "session_id": session_id},
        {
            "$push": {"messages": new_message},
            "$set": {"updated_at": datetime.now()}
        }
    )

async def calculate_metrics(input: str, output: str):
    schema = llm_metrics.init()
    schema = udf_schema()
    #response_hallucination.init(llm=OpenAILegacy(), num_samples=1)
    prompt_and_response = {"prompt": input, "response": output}
    profile = why.log(prompt_and_response, schema=schema).profile()
    profview = profile.view()
    df = profview.to_pandas()
    selected_rows = df[df.index.str.startswith(('response.toxicity', 'response.sentiment_nltk', 'response.relevance_to_prompt', 'response.hallucination', 'prompt.toxicity', 'prompt.jailbreak_similarity'))]
    selected_columns = selected_rows[['distribution/max']].to_dict()['distribution/max']
    return selected_columns

async def chat(user_input: UserInput, background_tasks: BackgroundTasks):
    try:
        chain = get_rag_chain(user_input.paths) 
        response = chain.invoke(
            {"input": user_input.input},
            {"configurable": {"session_id": user_input.session_id}}
        )
        
        message_id = str(uuid.uuid4())
        metrics = await calculate_metrics(user_input.input, response["answer"])
        
        # Serialize the sources (Document objects) to a format that can be stored in MongoDB
        serialized_sources = []
        for doc in response.get("context", []):
            serialized_source = {
                "page_content": doc.page_content,
                "metadata": {
                    k: (str(v) if not isinstance(v, (int, float, bool, type(None))) else v)
                    for k, v in doc.metadata.items()
                }
            }
            serialized_sources.append(serialized_source)
        
        new_message = {
            "id": message_id,
            "input": user_input.input,
            "output": response["answer"],
            "timestamp": datetime.now(UTC),
            "metrics": metrics,
            "sources": serialized_sources  # Use the serialized sources
        }
        
        background_tasks.add_task(update_user_messages, user_input.username, user_input.session_id, new_message)
        
        return {
            "session_id": user_input.session_id,
            "response": response["answer"],
            "message_id": message_id,
            "metrics": metrics,
            "sources": serialized_sources  # Return the serialized sources
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

async def submit_feedback(feedback_input: FeedbackInput, username: str):
    try:
        logger.info(f"Submitting feedback for user: {username}, message_id: {feedback_input.message_id}")
        
        user = await users_collection.find_one({"username": username})
        if not user:
            logger.error(f"User not found: {username}")
            raise ValueError(f"User not found: {username}")
        
        logger.info(f"User found: {username}")
        logger.info(f"Number of messages: {len(user.get('messages', []))}")
        
        message = next((msg for msg in user.get('messages', []) if msg.get('id') == feedback_input.message_id), None)
        if not message:
            logger.error(f"Message not found for user {username}, message_id: {feedback_input.message_id}")
            logger.info(f"Available message IDs: {[msg.get('id') for msg in user.get('messages', [])]}")
            raise ValueError(f"Message not found for id: {feedback_input.message_id}")
        
        logger.info(f"Message found: {message}")
        
        result = await users_collection.update_one(
            {
                "username": username,
                "messages.id": feedback_input.message_id
            },
            {
                "$set": {
                    "messages.$.feedback": {
                        "type": feedback_input.feedback_type,
                        "score": feedback_input.score,
                        "comment": feedback_input.comment,
                        "timestamp": datetime.now(UTC)
                    }
                }
            }
        )
        
        if result.matched_count == 0:
            logger.error(f"No document matched for update. User: {username}, message_id: {feedback_input.message_id}")
            raise ValueError("No matching document found for update.")
        
        if result.modified_count == 0:
            logger.warning(f"Document matched but not modified. Possible duplicate feedback. User: {username}, message_id: {feedback_input.message_id}")
            return {"message": "Feedback already submitted or no changes made."}
        
        logger.info(f"Feedback submitted successfully for user: {username}, message_id: {feedback_input.message_id}")
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error in submit_feedback function: {str(e)}")
        raise ValueError(f"An error occurred: {str(e)}")