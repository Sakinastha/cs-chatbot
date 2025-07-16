# ingestion.py
import os
import json
import time
from typing import List, Any, Dict, Optional
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# ─── Load environment ───────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV     = os.getenv("PINECONE_ENV")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX_NAME")
REDACTED   = os.getenv("REDACTED")

if not all([PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX, REDACTED]):
    raise RuntimeError(
        "Missing one of: PINECONE_API_KEY, PINECONE_ENV, "
        "PINECONE_INDEX_NAME, REDACTED"
    )

# ─── Initialize Pinecone client & index ────────────────────────────────────────
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
if PINECONE_INDEX not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
    )
default_index = pc.Index(PINECONE_INDEX)


def normalize_keys(obj: Any) -> Any:
    """Lower-case all dict keys and replace 'head' → 'chair'."""
    if isinstance(obj, dict):
        return {
            k.lower().replace("head", "chair"): normalize_keys(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [normalize_keys(v) for v in obj]
    return obj


def load_json_documents(paths: List[str]) -> List[Dict]:
    """
    Given a list of file paths, load each JSON, normalize keys,
    pretty-print the entire JSON, and return a list of:
      { "text": <pretty_json_str>, "metadata": {"source": <filename>} }
    """
    docs: List[Dict] = []
    for path in paths:
        if not os.path.exists(path):
            print(f"⚠️  Skipping missing file: {path}")
            continue
        fn = os.path.basename(path)
        try:
            raw = json.load(open(path, encoding="utf-8"))
            norm = normalize_keys(raw)
            pretty = json.dumps(norm, indent=2, ensure_ascii=False)
            docs.append({"text": pretty, "metadata": {"source": fn}})
        except Exception as e:
            print(f"⚠️  Failed to parse {fn}: {e}")
    return docs


async def ingest_data(
    file_paths: Optional[List[str]] = None,
    pinecone_index=None
) -> None:
    """
    Ingest given JSON file paths (or all under data_sources if None):
    1) Load & normalize each JSON
    2) Split into 500-token chunks (200 overlap)
    3) Embed with OpenAI and upsert into Pinecone
    """
    # choose index
    idx = pinecone_index or default_index

    # if no specific files passed, ingest everything in data_sources/
    if not file_paths:
        data_dir = os.path.join(BASE_DIR, "data_sources")
        file_paths = [
            os.path.join(data_dir, f)
            for f in sorted(os.listdir(data_dir))
            if f.lower().endswith(".json")
        ]

    docs = load_json_documents(file_paths)
    if not docs:
        print("⚠️  No JSON documents found to ingest.")
        return

    # chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=300,
        separators=["\n\n", "\n", " ", ""],
    )
    texts, metadatas = [], []
    for doc in docs:
        for chunk in splitter.split_text(doc["text"]):
            texts.append(chunk)
            metadatas.append(doc["metadata"])

    # embed & upsert
    embeds = OpenAIEmbeddings(openai_api_key=REDACTED)
    PineconeVectorStore.from_texts(
        texts,
        embeds,
        metadatas=metadatas,
        index_name=None,          # NOTE: explicitly pass None so we use the index handle
        index=idx                 # <- inject the existing Index object
    )

    # report
    stats = pc.describe_index(PINECONE_INDEX)
    total = stats.status.total_vector_count
    print(f"✅ Upserted {len(texts)} chunks. Total vectors now: {total}")


if __name__ == "__main__":
    start = time.time()
    import asyncio
    asyncio.run(ingest_data())
    print(f"✔️  Done in {time.time()-start:.1f}s")
