from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.config import settings
from app.services.prompts import BASE_SYSTEM_PROMPT
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from typing import List

store = {"message_history": {}, "paths": {}}

@lru_cache(maxsize=1)
def get_vector_db():
    embeddings = get_embeddings()
    return PineconeVectorStore(embedding=embeddings, index_name="gemnivector")

@lru_cache(maxsize=1)
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-002",
        temperature=0,
        max_output_tokens=4096
    )

@lru_cache(maxsize=1)
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")

@lru_cache(maxsize=1)
def get_prompt():
    return ChatPromptTemplate.from_messages(
        [
            ("system", BASE_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )

def get_hybrid_retriever(vector_retriever, paths: List[str], bm25_weight=0.5, vector_weight=0.5):
    # Fetch documents from the vector store with path filter
    documents = vector_retriever.vectorstore.similarity_search(
        "", k=1000, filter={"source": {"$in": paths}}
    )
    
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = vector_retriever.search_kwargs["k"]
    
    return EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[bm25_weight, vector_weight]
    )

def get_rag_chain(paths: List[str]):
    vectorstore = get_vector_db()
    llm = get_llm()
    vector_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            'k': 10,
            'filter': {"source": {"$in": paths}}
        }
    )

    # Create hybrid retriever with paths
    hybrid_retriever = get_hybrid_retriever(vector_retriever, paths)

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, hybrid_retriever, contextualize_q_prompt
    )

    qa_prompt = get_prompt()
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    return RunnableWithMessageHistory(
        rag_chain,
        lambda session_id: store.setdefault(session_id, ChatMessageHistory()),
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )