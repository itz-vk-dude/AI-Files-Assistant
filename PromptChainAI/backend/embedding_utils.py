from sentence_transformers import SentenceTransformer
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
import hashlib

# ✅ Inlined config values
EMBEDDING_MODEL = "BAAI/bge-small-en"
EMBEDDING_PREFIX = "Represent this document for retrieval:"

# 🔍 Global embedding model
model = SentenceTransformer(EMBEDDING_MODEL)

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
    """
    Split long text into overlapping chunks.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks

def embed_texts(texts: List[str], batch_size: int = 32, show_progress: bool = False) -> List[List[float]]:
    """
    Generate BGE-style embeddings with instruction prefix.
    """
    if not texts:
        return []

    texts = [f"{EMBEDDING_PREFIX} {t}" for t in texts]
    return model.encode(texts, batch_size=batch_size, show_progress_bar=show_progress)

def text_hash(text: str) -> str:
    """
    Create a SHA256 hash for tracking file uniqueness.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def process_file(file_text: str) -> Tuple[str, List[str], List[List[float]]]:
    """
    Process one file: chunk + embed.
    Returns: (hash, chunks, embeddings)
    """
    file_text = file_text.strip()
    if not file_text:
        print("⚠️ Skipping embedding: Empty file.")
        return "", [], []

    chunks = chunk_text(file_text)
    if not chunks:
        print("⚠️ Skipping embedding: No valid chunks.")
        return "", [], []

    embeddings = embed_texts(chunks)
    return text_hash(file_text), chunks, embeddings

def process_multiple_files(file_texts: List[str], max_workers: int = 4) -> List[Tuple[str, List[str], List[List[float]]]]:
    """
    Process multiple files in parallel.
    Returns list of (hash, chunks, embeddings)
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_file, file_texts))
    return results
