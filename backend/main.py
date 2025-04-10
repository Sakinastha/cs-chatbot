from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# FastAPI application
app = FastAPI()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Pydantic model for request validation
class QueryRequest(BaseModel):
    query: str  # Ensures the query is a string

# Global variable to hold chat history
chat_history = []

# Helper functions

def load_json_documents(file_paths):
    documents = []
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):  
                for key, value in data.items():
                    text = f"{key}: {value}"
                    documents.append({"text": text, "source": file_path})
            elif isinstance(data, list): 
                for obj in data:
                    text = "\n".join([f"{key}: {value}" for key, value in obj.items()])
                    documents.append({"text": text, "source": file_path})
    return documents

# Endpoint to handle ingestion
@app.post("/ingest")
async def ingest_data():
    try:
        print("Ingesting data...")

        # List of your JSON files
        json_files = ["datasource/degree.json", "datasource/Department.json", "datasource/advising.json", "datasource/academic_resources.json", "datasource/classes.json"]
        
        # Load the raw documents with source metadata
        raw_documents = load_json_documents(json_files)

        # Reducing the chunk size to 500 characters to avoid exceeding token limits
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)  # Smaller chunk size and overlap
        
        texts = []
        metadatas = []
        
        for doc in raw_documents:
            doc_text = doc['text']
            doc_metadata = {"source": doc['source']}  # Adding the source file as metadata
            
            # Split the text into chunks
            chunks = text_splitter.create_documents([doc_text])
            
            # Store each chunk and its associated metadata
            for chunk in chunks:
                texts.append(chunk.page_content)  # Extracting text content from Document object
                metadatas.append(doc_metadata)
        
        print(f"Created {len(texts)} chunks.")

        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("REDACTED"))

        # Initialize PineconeVectorStore and store the documents along with metadata
        index_name = os.environ.get("INDEX_NAME")
        PineconeVectorStore.from_texts(texts, embeddings, metadatas=metadatas, index_name=index_name)

        return {"message": f"Data successfully ingested into Pinecone index: {index_name}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to clear Pinecone index
@app.delete("/clear-index")
async def clear_index():
    try:
        # Initialize Pinecone client
        api_key = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENV")
        index_name = os.getenv("PINECONE_INDEX_NAME")

        pc = Pinecone(api_key=api_key)

        # Get the Pinecone index
        index = pc.Index(index_name)
        
        # Delete all data in the index
        index.delete(delete_all=True)
        
        return {"message": f"Index {index_name} cleared successfully."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to handle chat
@app.post("/chat")
async def chat_with_bot(request: QueryRequest):
    try:
        query = request.query  # Access the query from the validated request body

        embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("REDACTED"))
        vectorstore = PineconeVectorStore(index_name=os.environ["INDEX_NAME"], embedding=embeddings)

        chat = ChatOpenAI(model_name="gpt-3.5-turbo", verbose=True, temperature=0)
        qa = ConversationalRetrievalChain.from_llm(llm=chat, chain_type="stuff", retriever=vectorstore.as_retriever())

        global chat_history
        res = qa({"question": query, "chat_history": chat_history})
        
        ai_response = res["answer"]
        chat_history.append((query, ai_response))

        return {"response": ai_response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

