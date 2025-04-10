
import os
import json
from dotenv import load_dotenv
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

def load_json_documents(file_paths):
    documents = []
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):  
                # Split text based on keys and values
                for key, value in data.items():
                    text = f"{key}: {value}"
                    documents.append({"text": text, "source": file_path})
            elif isinstance(data, list): 
                # For lists, treat each element as a chunk
                for obj in data:
                    text = "\n".join([f"{key}: {value}" for key, value in obj.items()])
                    documents.append({"text": text, "source": file_path})
    return documents

if __name__ == "__main__":
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
    pinecone_vector_store = PineconeVectorStore.from_texts(
        texts, embeddings, metadatas=metadatas, index_name=index_name
    )

    print(f"Data has been successfully ingested into Pinecone index: {index_name}")


