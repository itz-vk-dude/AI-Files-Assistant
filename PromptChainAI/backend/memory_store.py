import os
import json
import hashlib
from pathlib import Path

import numpy as np
from embedding_utils import embed_texts

# 🧠 In-memory file storage
file_memory = {}

# 📁 Cache folder
CACHE_DIR = Path("backend/memory_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def clear():
    file_memory.clear()

def add_file_to_memory(filename, text, summary):
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)
    file_memory[filename] = {
        "text": text,
        "summary": summary,
        "chunks": chunks,
        "embeddings": embeddings
    }

    # Save cache
    cache_path = get_cache_path(filename)
    cache_data = {
        "hash": text_hash(text),
        "text": text,
        "summary": summary
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_cache_path(filename):
    return CACHE_DIR / f"{filename}.json"

def get_all_chunks_and_sources():
    chunks = []
    sources = []
    for filename, data in file_memory.items():
        for chunk in data["chunks"]:
            chunks.append(chunk)
            sources.append(filename)
    return chunks, sources

def get_embeddings():
    embeddings = []
    for data in file_memory.values():
        embeddings.extend(data["embeddings"])
    return embeddings

# ✅ NEW: load memory from saved cache folder
def load_folder_memory(folder_id=None):
    """
    Reload memory from cached file summaries and embeddings.
    """
    if not CACHE_DIR.exists():
        print("⚠️ No memory cache directory found.")
        return

    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            text = cached.get("text", "")
            summary = cached.get("summary", "")
            filename = cache_file.stem
            add_file_to_memory(filename, text, summary)
            print(f"🔁 Loaded from cache: {filename}")
        except Exception as e:
            print(f"❌ Failed to load {cache_file}: {e}")
