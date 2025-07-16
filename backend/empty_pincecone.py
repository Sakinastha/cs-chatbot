# empty_pinecone.py
import os
import pinecone
from dotenv import load_dotenv

# 1) Load your env vars
load_dotenv()
api_key       = os.getenv("PINECONE_API_KEY")
environment   = os.getenv("PINECONE_ENV")        
index_name    = os.getenv("PINECONE_INDEX_NAME")  # your index name

if not api_key or not environment or not index_name:
    raise ValueError("Make sure PINECONE_API_KEY, PINECONE_ENV, and PINECONE_INDEX_NAME are set in .env")

# 2) Initialize the Pinecone client
pinecone.init(api_key=api_key, environment=environment)

# 3) Connect to your index
index = pinecone.Index(index_name)

# 4) Delete all vectors in the default namespace
print(f"Clearing all vectors from index '{index_name}'...")
index.delete(delete_all=True)
print("Done.")
