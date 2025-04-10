import os
from dotenv import load_dotenv
# import pinecone
from pinecone import Pinecone


# Load environment variables
load_dotenv()

# Retrieve Pinecone API key and environment from the environment variables
api_key = os.getenv("PINECONE_API_KEY")
environment = os.getenv("PINECONE_ENV")

# Initialize Pinecone
pc = Pinecone(api_key=api_key)

# Specify the index name you want to delete
index_name = os.getenv("PINECONE_INDEX_NAME")



# To get the unique host for an index, 
# see https://docs.pinecone.io/guides/data/target-an-index
index = pc.Index(host="https://vectorized-datasource-76i6d2b.svc.aped-4627-b74a.pinecone.io")

index.delete(delete_all=True, namespace='')

