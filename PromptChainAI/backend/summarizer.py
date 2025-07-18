# ✅ summarizer.py with caching, empty-checks, and multithreading

import ollama
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from embedding_utils import chunk_text

# Model and thread settings
SUMMARIZER_MODEL = "phi3:mini"
MAX_THREADS = 4
CACHE_DIR = ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Summarize one chunk with Ollama
def summarize_chunk(chunk, model=SUMMARIZER_MODEL):
    prompt = f"""
You are a helpful assistant. Summarize the following content in 3–4 clear sentences:

{chunk}

Summary:
""".strip()

    try:
        start_time = time.time()
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        duration = time.time() - start_time
        print(f"✅ Chunk summarized in {duration:.2f}s")
        return response.get("message", {}).get("content", "").strip() or "(No response)"
    except Exception as e:
        print(f"❌ Error during summarization: {str(e)}")
        return f"(Chunk summarization failed: {str(e)})"

# Main function to summarize a file or content
def summarize_with_ollama(text, model=SUMMARIZER_MODEL, filename=""):
    if not text.strip():
        print(f"⚠️ File '{filename}' is empty — skipping summarization.")
        return "(Empty file — no summary generated.)"

    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    if not chunks:
        print(f"⚠️ No valid chunks extracted from '{filename}' — skipping.")
        return "(No summary generated — empty chunks.)"

    print(f"✂️ Splitting into {len(chunks)} chunk(s)...")

    cache_path = os.path.join(CACHE_DIR, f"{filename}.summary.json") if filename else None

    # ✅ Try loading from cache
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_summary = cached.get("summary", "").strip()
            if (
                cached.get("model") == model and
                len(cached.get("chunks", [])) == len(chunks) and
                cached_summary
            ):
                print(f"⚡ Using cached summary for: {filename}")
                return cached_summary
            else:
                print(f"⚠️ Cache invalid or empty for: {filename} — regenerating.")
        except Exception as e:
            print(f"⚠️ Failed to read summary cache for {filename}: {e}")

    # ❌ No valid cache — generate summaries
    summaries = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_chunk = {
            executor.submit(summarize_chunk, chunk, model): i for i, chunk in enumerate(chunks)
        }
        for future in as_completed(future_to_chunk):
            try:
                summaries.append(future.result())
            except Exception as e:
                summaries.append(f"(Error: {str(e)})")

    summary_text = "\n\n".join(summaries)

    # ✅ Save to cache
    if cache_path:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "model": model,
                    "summary": summary_text,
                    "chunks": chunks
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved summary cache: {filename}")
        except Exception as e:
            print(f"⚠️ Failed to save summary cache for {filename}: {e}")

    return summary_text
