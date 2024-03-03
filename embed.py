import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()
# Avoid printing API Keys directly
print("API Keys Loaded")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

folder_path = "E:\earning_reports_copilot\Concalls"

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")

# Initialize Pinecone vector store with the specified embedding
vector_store = PineconeVectorStore(embedding=embeddings, index_name="gemnivector")

# Iterate through each subfolder in the main folder
for subfolder in os.listdir(folder_path):
    subfolder_path = os.path.join(folder_path, subfolder)

    # Check if the item in the folder is a directory
    if os.path.isdir(subfolder_path):
        # Iterate through each PDF file in the subfolder
        for pdf_file in os.listdir(subfolder_path):
            if pdf_file.endswith(".pdf"):
                # Create the full path to the PDF file
                pdf_path = os.path.join(subfolder_path, pdf_file)

                # Load PDF pages
                loader = PyPDFLoader(pdf_path)
                pages = loader.load()

                # Split documents into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1024,
                    chunk_overlap=100,
                    length_function=len,
                    is_separator_regex=False,
                )
                docs = text_splitter.split_documents(pages)

                # Create embeddings for each document
                index = PineconeVectorStore.from_documents(docs, embeddings, index_name="gemnivector")

        # Signal when the subfolder is completed
        print(f"Subfolder {subfolder} completed.")
