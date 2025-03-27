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
                text = "\n".join([f"{key}: {value}" for key, value in data.items()])
                documents.append(text)
            elif isinstance(data, list): 
                for obj in data:
                    text = "\n".join([f"{key}: {value}" for key, value in obj.items()])
                    documents.append(text)
    return documents

if __name__ == "__main__":
    print("Ingesting data...")
    

    json_files = ["datasource/degree.json", "datasource/Department.json"]
    raw_texts = load_json_documents(json_files)
    

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.create_documents(raw_texts)
    print(f"Created {len(texts)} chunks")


    embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("REDACTED"))
    PineconeVectorStore.from_documents(texts, embeddings, index_name=os.environ.get("INDEX_NAME"))