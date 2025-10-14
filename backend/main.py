# backend/main.py
print("✅✅✅ main.py loaded successfully")

import os
import re
import json
from typing import List, Tuple, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from sqlalchemy.orm import Session



# LangChain
from langchain.text_splitter import TokenTextSplitter
from langchain_openai import OpenAIEmbeddings  # pin model
from langchain_pinecone import PineconeVectorStore
# Keep your existing ChatOpenAI import to avoid package churn
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

# Pinecone
from pinecone import Pinecone

# ─── Auth & DB ─────────────────────────────────────────────────────────

from db import SessionLocal, engine, Base
from models import User
from security import hash_password, verify_password, create_access_token

from jose import JWTError, jwt

# ─── Env ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_ENV       = os.getenv("PINECONE_ENV")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "docs")  # <<— important
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
JWT_SECRET         = os.getenv("JWT_SECRET")
ALGORITHM          = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

if not all([PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX, OPENAI_API_KEY, JWT_SECRET]):
    raise RuntimeError("Missing one of: PINECONE_*, OPENAI_API_KEY, or JWT_SECRET")

# DB tables
Base.metadata.create_all(bind=engine)

# ─── FastAPI ───────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173", 
    "http://localhost:5174", 
    "http://localhost:3000",
    "http://18.214.136.155:3000",  
    "http://18.214.136.155",        
],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "localhost:5173", "*"]  # the "*" at the end allows any host temporarily
)

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str,Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

# ─── Schemas ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QueryRequest(BaseModel):
    query: str

class Course(BaseModel):
    course_code: str
    course_name: str
    credits: int
    prerequisites: List[str] = []
    offered: List[str] = []

# ─── In-memory chat history ────────────────────────────────────────────
chat_history: List[Tuple[str, str]] = []

# ─── Static data ───────────────────────────────────────────────────────
DATA_DIR       = os.path.join(BASE_DIR, "data_sources")
CLASSES_FILE   = os.path.join(DATA_DIR, "classes.json")
RESOURCES_FILE = os.path.join(DATA_DIR, "academic_resources.json")
with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
    res_data = json.load(f)
helpful_links = res_data.get("academic_and_student_support", {}).get("helpful_links", {})

# ─── Auth endpoints ────────────────────────────────────────────────────
@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(req.password)
    student = User(email=req.email, password_hash=hashed, role="student")
    db.add(student); db.commit(); db.refresh(student)
    return {"message": "Student account created", "user_id": student.id}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({
        "user_id": user.id,
        "role": user.role,
        "email": user.email
    })
    return {"access_token": token, "token_type": "bearer"}

# ─── Pinecone + Retrieval globals ──────────────────────────────────────
# IMPORTANT: do NOT re-upsert at startup. Only connect to the existing index/namespace.
pc = Pinecone(api_key=PINECONE_API_KEY)  # v3 SDK (no 'environment' arg here)
retriever = None
qa = None
llm = None

@app.on_event("startup")
def build_qa_chain():
    global retriever, qa, llm

    # Same embedding model as ingestion (1536-dim)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY,
    )

    # Connect to existing index + namespace (no re-indexing)
    store = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX,
        embedding=embeddings,
        namespace=PINECONE_NAMESPACE,
    )

    # A forgiving retriever (no strict score threshold)
    retriever = store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 8}
    )

    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name="gpt-3.5-turbo",
        temperature=0
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

# ─── Curriculum endpoints ──────────────────────────────────────────────
@app.post("/api/curriculum/add")
async def add_course(course: Course, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    if not isinstance(arr, list):
        raise HTTPException(status_code=500, detail="classes.json malformed")
    arr.append(course.dict())
    json.dump(arr, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": "Course added", "course": course}

@app.delete("/api/curriculum/delete/{code}")
async def delete_course(code: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    filtered = [c for c in arr if c.get("course_code") != code]
    if len(filtered) == len(arr):
        raise HTTPException(status_code=404, detail=f"{code} not found")
    json.dump(filtered, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": f"{code} deleted"}

@app.get("/api/curriculum")
async def get_curriculum():
    try:
        data = json.load(open(CLASSES_FILE, encoding="utf-8"))
        if isinstance(data, list):
            return data
        for key in ("computer_science_courses","courses","classes"):
            arr = data.get(key)
            if isinstance(arr,list):
                return arr
        cs = data.get("computer_science_courses")
        if isinstance(cs,dict) and isinstance(cs.get("computer_science_courses"),list):
            return cs["computer_science_courses"]
        raise HTTPException(500,"Unexpected JSON shape")
    except FileNotFoundError:
        raise HTTPException(404,"Curriculum file not found")
    except json.JSONDecodeError as e:
        raise HTTPException(500,f"JSON parse error: {e}")

# ─── Ingest & index management ─────────────────────────────────────────
@app.post("/ingest")
async def ingest_data(user=Depends(get_current_user)):
    # admin only
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    # Minimal, safe ingest into the SAME namespace (no default namespace!)
    files = [
        os.path.join(DATA_DIR, fn)
        for fn in sorted(os.listdir(DATA_DIR))
        if fn.lower().endswith(".json")
    ]

    # Normalize + chunk
    raw = []
    for p in files:
        raw.extend(load_json_documents([p]))

    splitter = TokenTextSplitter(chunk_size=800, chunk_overlap=160, model_name="gpt-3.5-turbo")
    texts, metas = [], []
    for doc in raw:
        for chunk in splitter.split_text(doc["text"]):
            texts.append(chunk)
            metas.append({"source": os.path.basename(doc["source"])})

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=OPENAI_API_KEY)
    PineconeVectorStore.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metas,
        index_name=PINECONE_INDEX,
        namespace=PINECONE_NAMESPACE,  # <<— keep it in docs
    )
    return {"message": f"Ingested into {PINECONE_INDEX}:{PINECONE_NAMESPACE}", "chunks": len(texts)}

@app.delete("/clear-index")
async def clear_index(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    idx = pc.Index(PINECONE_INDEX)
    idx.delete(delete_all=True, namespace=PINECONE_NAMESPACE)  # safer: clear only your namespace
    return {"message": f"Cleared namespace '{PINECONE_NAMESPACE}' in index {PINECONE_INDEX}"}

@app.get("/ping")
async def ping():
    return {"status": "pong"}

# ─── Chat endpoint (protected) ─────────────────────────────────────────
@app.post("/chat")
async def chat_with_bot(req: QueryRequest, user=Depends(get_current_user)):
    if user.get("role") not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="Students or admins only")

    user_q = req.query.strip().lower()
    norm   = re.sub(r'[\s\W]+', '', user_q)

    # small talk
    if re.match(r'^(hi|hello|hey)\b', user_q):
        return {"response": "Hello! How can I help you today?"}
    if re.match(r'^(bye|goodbye|see you)\b', user_q):
        return {"response": "Goodbye! Have a great day."}
    if re.search(r'\b(thankyou|thanks|thanx|thx|ty)\b', norm):
        return {"response": "You’re welcome! "}
    if re.match(r'^(ok|okay|sure|got it)\b', user_q):
        return {"response": "Alright! Let me know if you need CS help."}
    if re.search(r'\bhow are you\b', user_q):
        return {"response": "I’m doing great, thanks! How about you?"}
    if re.search(r'\b(i(\'?m| am) (doing )?(good|well|great|fine)|doing (good|well|great))\b', user_q):
        return {"response": "Glad to hear that! Anything I can help you with today?"}
    if re.search(r"\bwhat(?:'s| is) up\b", user_q):
        return {"response": "Not much—just here and ready to help. What’s on your mind?"}
    if re.match(r'\b(good morning)\b', user_q):
        return {"response": "Good morning! ☀️ How’s your day starting off?"}
    if re.match(r'\b(good afternoon)\b', user_q):
        return {"response": "Good afternoon! How can I make your day better?"}
    if re.match(r'\b(good evening)\b', user_q):
        return {"response": "Good evening! How’s everything going?"}
    if re.search(r'\b(sorry|apologies)\b', user_q):
        return {"response": "No worries at all. What can I do for you?"}
    if re.search(r'\bhow(\'?s| is) your day\b', user_q):
        return {"response": "It’s going well—thanks for asking! And yours?"}
    if re.match(r'^(bye|goodbye|see you|good night|goodnight|gnight)\b', user_q): 
        return {"response": "Goodnight! If you have more CS questions tomorrow, I'm here."}
    if re.search(r"\bwhat(?:'s| is) up\b", user_q):
        return {"response": "Not much—just here to help with CS department questions. What’s on your mind?"}
    if re.match(r'\b(good morning)\b', user_q):
        return {"response": "Good morning! ☀️ Ready for some Computer Science queries?"}
    if re.match(r'\b(good afternoon)\b', user_q):
        return {"response": "Good afternoon! How can I assist with CS topics?"}
    if re.match(r'\b(good evening)\b', user_q):
        return {"response": "Good evening! Let’s talk Computer Science."}
    if re.search(r'\b(sorry|apologies)\b', user_q):
        return {"response": "No worries at all. What CS question can I help with?"}

    # Helpful-links lookup
    for name, info in helpful_links.items():
        if name in user_q and "link" in user_q:
            raw_url = info.get("url", "")
            m = re.search(r"(https?://[^\s\)\]>]+)", raw_url)
            url = m.group(1) if m else raw_url
            return {"response": f"Here’s the {name.title()} link: {url}"}

    # Retrieval + QA
    docs   = retriever.get_relevant_documents(user_q)
    result = qa({"query": user_q})
    answer = result["result"].strip()

    # Fallback if RetrievalQA didn't return sources
    if not result.get("source_documents"):
        if docs:
            context = "\n\n---\n\n".join(d.page_content for d in docs)
            prompt = f"""Use the context to answer concisely. If the answer is not in the context, say "I don't know".

Context:
{context}

Question: {user_q}
Answer:"""
            answer = llm.invoke(prompt).content.strip()
        else:
            answer = "I don't know."

    chat_history.append((req.query, answer))
    return {"response": answer}


@app.get("/chat-history")
async def get_chat_history(user=Depends(get_current_user)):
    if user.get("role") not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {"history": chat_history}

@app.post("/reset-history")
async def reset_chat_history(user=Depends(get_current_user)):
    if user.get("role") not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    chat_history.clear()
    return {"message": "Chat history reset."}

# ─── helpers ───────────────────────────────────────────────────────────
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
