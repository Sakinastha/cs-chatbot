# backend/count_chunks.py

import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Since this script lives in backend/, data_sources is a subfolder here:
DATA_DIR = os.path.join(os.path.dirname(__file__), "data_sources")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

for fname in sorted(os.listdir(DATA_DIR)):
    if not fname.lower().endswith(".json"):
        continue
    path = os.path.join(DATA_DIR, fname)
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"{fname:30} → ERROR loading JSON: {e}")
        continue

    text = json.dumps(data, indent=2)
    chunks = splitter.split_text(text)
    print(f"{fname:30} → {len(chunks):3d} chunks")
