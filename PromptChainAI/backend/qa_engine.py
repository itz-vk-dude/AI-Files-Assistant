import requests
import ollama
import os
import re
from statistics import mean
from sklearn.metrics.pairwise import cosine_similarity
from memory_store import get_all_chunks_and_sources, get_embeddings, load_folder_memory
from embedding_utils import embed_texts
from reward.reward_model import score_response

OPENROUTER_MODEL = "mistralai/mistral-7b-instruct"
OLLAMA_QA_MODEL = "llama3:8b"
TOP_K_CHUNKS = 6
OPENROUTER_API_KEY = "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"

def get_top_chunks(question, top_k=TOP_K_CHUNKS):
    chunks, sources = get_all_chunks_and_sources()
    if not chunks:
        return []

    try:
        chunk_embeddings = get_embeddings()
        if not chunk_embeddings or len(chunk_embeddings) != len(chunks):
            return []

        question_embedding = embed_texts([question])[0]
        scores = cosine_similarity([question_embedding], chunk_embeddings)[0]
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(chunks[i], sources[i]) for i in top_indices]
    except Exception:
        return []

def extract_numbers(text):
    return [float(num.replace(',', '')) for num in re.findall(r'\b\d[\d,\.]*\b', text)]

def summarize_numeric_totals(chunks, question):
    all_numbers = []
    for chunk, _ in chunks:
        nums = extract_numbers(chunk)
        all_numbers.extend(nums)

    if not all_numbers:
        return None

    q = question.lower()
    if "average" in q:
        avg = mean(all_numbers)
        return f"🔢 The average value across relevant entries is approximately {avg:.2f}."
    elif "total" in q or "sum" in q:
        total = sum(all_numbers)
        return f"🔢 The total value across relevant entries is {total:.2f}."
    return None

def merge_numeric_totals(answers):
    total = 0
    for ans in answers:
        nums = extract_numbers(ans)
        total += sum(nums)
    return total

def ask_question_hybrid(question, folder_id=None, file_texts=None, use_ollama=False):
    if folder_id:
        load_folder_memory(folder_id)

    top_chunks = get_top_chunks(question)
    if not top_chunks:
        return {
            "answer": "(No relevant content found.)",
            "sources": []
        }

    # ✅ Attempt numeric summarization before querying models
    numeric_summary = summarize_numeric_totals(top_chunks, question)
    if numeric_summary:
        return {
            "answer": numeric_summary,
            "sources": sorted(set(src for _, src in top_chunks))
        }

    context_blocks = [f"[{src}]:\n{chunk}" for chunk, src in top_chunks]
    all_answers = []
    for block in context_blocks:
        prompt = f"""
Answer the following question based on the provided data block.

DATA:
{block}

QUESTION:
{question}
""".strip()

        try:
            if use_ollama:
                response = ollama.chat(model=OLLAMA_QA_MODEL, messages=[{"role": "user", "content": prompt}])
                answer = response["message"]["content"].strip()
            else:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {"role": "system", "content": "Answer using only the provided data block."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 400
                    }
                )
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            answer = f"(Error from model: {e})"

        all_answers.append(answer)

    merged_text = "\n\n".join(all_answers)

    if "total" in question.lower():
        merged_total = merge_numeric_totals(all_answers)
        merged_text += f"\n\n🔢 Estimated combined total: {merged_total}"

    return {
        "answer": merged_text.strip(),
        "sources": sorted(set(src for _, src in top_chunks))
    }

def ask_openrouter_chat(question, history=[]):
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be brief and clear."}
    ] + [
        {"role": "user" if m["type"] == "user" else "assistant", "content": m["content"]}
        for m in history
    ] + [{"role": "user", "content": question}]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 400
            }
        )
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "(No answer returned)").strip()
    except Exception as e:
        return f"(OpenRouter error: {str(e)})"

def ask_multi_model_best(question, models=["openrouter", "ollama"], folder_id=None):
    if folder_id:
        load_folder_memory(folder_id)

    completions = []
    for source in models:
        try:
            if source == "openrouter":
                resp = ask_question_hybrid(question, folder_id=folder_id, use_ollama=False)
                completions.append(("openrouter", resp["answer"]))
            elif source == "ollama":
                resp = ask_question_hybrid(question, folder_id=folder_id, use_ollama=True)
                completions.append(("ollama", resp["answer"]))
        except Exception as e:
            print(f"⚠️ {source} failed: {e}")

    if not completions:
        return {"answer": "(No completions generated)", "sources": []}

    print("📊 Scoring responses with reward model...")
    scored = [(src, resp, score_response(question, resp)) for src, resp in completions]
    best = max(scored, key=lambda x: x[2])

    return {
        "answer": best[1],
        "sources": [best[0]],
        "score": best[2]
    }
