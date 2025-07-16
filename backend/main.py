import os
import string
import re
import json
from typing import List, Tuple, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

# Pinecone client
from pinecone import Pinecone, ServerlessSpec

# ─── Load env ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_ENV       = os.getenv("PINECONE_ENV")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME")
REDACTED     = os.getenv("REDACTED")

if not all([PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX, REDACTED]):
    raise RuntimeError("Missing one of: PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX_NAME, REDACTED")

# ─── Pinecone & FastAPI setup ──────────────────────────────────────────────────
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
      "http://localhost:5173",
      "http://localhost:5174",  # Vite's fallback port
      "http://localhost:3000",  # if you ever run CRA
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ─────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str

class Course(BaseModel):
    course_code: str
    course_name: str
    credits: int
    prerequisites: List[str] = []
    offered: List[str] = []

chat_history: List[Tuple[str, str]] = []

# ─── Paths & quick-lookup links ────────────────────────────────────────────────
DATA_DIR       = os.path.join(BASE_DIR, "data_sources")
CLASSES_FILE   = os.path.join(DATA_DIR, "classes.json")
RESOURCES_FILE = os.path.join(DATA_DIR, "academic_resources.json")

with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
    res_data = json.load(f)
helpful_links = res_data.get("academic_and_student_support", {}).get("helpful_links", {})

# ─── Curriculum endpoints (unchanged) ────────────────────────────────────────
@app.post("/api/curriculum/add")
async def add_course(course: Course):
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    if not isinstance(arr, list):
        raise HTTPException(500, "classes.json malformed")
    arr.append(course.dict())
    json.dump(arr, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": "Course added", "course": course}

@app.delete("/api/curriculum/delete/{code}")
async def delete_course(code: str):
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    filtered = [c for c in arr if c.get("course_code") != code]
    if len(filtered) == len(arr):
        raise HTTPException(404, f"{code} not found")
    json.dump(filtered, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": f"{code} deleted"}

@app.get("/api/curriculum")
async def get_curriculum():
    try:
        data = json.load(open(CLASSES_FILE, encoding="utf-8"))
        if isinstance(data, list):
            return data
        for key in ("computer_science_courses", "courses", "classes"):
            arr = data.get(key)
            if isinstance(arr, list):
                return arr
        cs = data.get("computer_science_courses")
        if isinstance(cs, dict) and isinstance(cs.get("computer_science_courses"), list):
            return cs["computer_science_courses"]
        raise HTTPException(500, "Unexpected JSON shape")
    except FileNotFoundError:
        raise HTTPException(404, "Curriculum file not found")
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"JSON parse error: {e}")

# ─── Ingest endpoint (unchanged) ──────────────────────────────────────────────
@app.post("/ingest")
async def ingest_data():
    files = [
        os.path.join(DATA_DIR, fn)
        for fn in sorted(os.listdir(DATA_DIR))
        if fn.lower().endswith(".json")
    ]
    raw = []
    for p in files:
        raw.extend(load_json_documents([p]))
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=300,
        separators=["\n\n", "\n", " ", ""]
    )
    texts, metas = [], []
    for doc in raw:
        for chunk in splitter.split_text(doc["text"]):
            texts.append(chunk)
            metas.append({"source": doc["source"]})

    embeds = OpenAIEmbeddings(openai_api_key=REDACTED)
    PineconeVectorStore.from_texts(texts, embeds, metadatas=metas, index_name=PINECONE_INDEX)
    return {"message": f"Ingested into `{PINECONE_INDEX}`"}

@app.delete("/clear-index")
async def clear_index():
    idx = pc.Index(PINECONE_INDEX)
    idx.delete(delete_all=True)
    return {"message": f"Index `{PINECONE_INDEX}` cleared"}

@app.get("/ping")
async def ping():
    return {"status": "pong"}

# ─── 7) Build your QA chain once ───────────────────────────────────────────────
all_files = []
for fn in sorted(os.listdir(DATA_DIR)):
    if not fn.lower().endswith(".json"):
        continue
    path = os.path.join(DATA_DIR, fn)
    # skip empty files
    if os.path.getsize(path) == 0:
        continue
    try:
        with open(path, encoding="utf-8") as f:
            _ = f.read().strip()
        # now try to parse
        with open(path, encoding="utf-8") as f:
            _data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"⚠️  Skipping invalid JSON: {fn}")
        continue
    all_files.append(path)
    
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300,
                                          separators=["\n\n", "\n", " ", ""])
texts, metas = [], []
for p in all_files:
    data = json.load(open(p, encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    for itm in items:
        txt = json.dumps(itm, ensure_ascii=False)
        for chunk in splitter.split_text(txt):
            texts.append(chunk)
            metas.append({"source": os.path.basename(p)})

embeds   = OpenAIEmbeddings(openai_api_key=REDACTED)
store    = PineconeVectorStore.from_texts(texts, embeds, metadatas=metas, index_name=PINECONE_INDEX)
retriever = store.as_retriever(search_kwargs={"k": 15})   # ← bump k to 15
qa        = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

# ─── 8) Chat endpoint ───────────────────────────────────────────────────────────
@app.post("/chat")
async def chat_with_bot(req: QueryRequest):
    user_q = req.query.strip().lower()

    # 1) casual greetings
    if re.match(r'^(hi|hello|hey)\b', user_q):
        return {"response": "Hello! How can I help you today?"}
    if re.match(r'^(bye|goodbye)\b', user_q):
        return {"response": "Goodbye! Have a great day."}
    if 'thank' in user_q:
        return {"response": "You’re welcome!"}

    # 2) quick link lookup
    for name, info in helpful_links.items():
        if name.lower() in user_q and "link" in user_q:
            raw = info.get("url", "")
            # 1) strip any < or > around it
            url = raw.strip().strip("<>")
            # 2) strip trailing punctuation (.,;:!?) and any closing bracket ])
            url = url.rstrip(string.punctuation + "]")
            return {"response": f"Here’s the {name} URL: {url}"}

    # 3) exact‐substring fallback
    for doc in texts:   # we still have `texts` array of chunks
        if user_q in doc.lower():
            return {"response": doc}

    # 4) semantic QA
    result = qa({"query": user_q})
    answer = result["result"].strip()
    srcs   = result["source_documents"]

    if not srcs:
        answer = "I don't know."

    chat_history.append((req.query, answer))
    return {"response": answer}

# ─── 9) Reset & history ─────────────────────────────────────────────────────────
@app.post("/reset-history")
async def reset_history():
    global chat_history
    chat_history = []
    return {"message": "Chat history reset"}

@app.get("/chat-history")
async def get_history():
    return {"history": chat_history}


def load_json_documents(paths: List[str]) -> List[Dict[str,Any]]:
    docs: List[Dict[str,Any]] = []
    for p in paths:
        data = json.load(open(p, encoding="utf-8"))
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    parts = [f"{subk}: {subv}" for subk, subv in v.items()]
                    docs.append({"text": f"{k} – " + "; ".join(parts), "source": p})
                else:
                    docs.append({"text": f"{k}: {v}", "source": p})
        elif isinstance(data, list):
            for obj in data:
                text = "\n".join(f"{kk}: {vv}" for kk, vv in obj.items())
                docs.append({"text": text, "source": p})
    return docs
