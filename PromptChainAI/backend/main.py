from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import json
from drive_handler import download_files_from_drive
from file_processor import extract_text_from_file
from summarizer import summarize_with_ollama
from qa_engine import (
    ask_question_hybrid,
    get_top_chunks,
    ask_openrouter_chat,
    ask_multi_model_best,
)
from chat_history import save_chat_history, load_chat_history
import memory_store

# 🔧 Config
SUMMARIZER_MODEL = "llama3:8b"
#OPENROUTER_MODEL = "mistralai/mistral-7b-instruct"
#OPENROUTER_API_KEY = "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"  # update yours
# 🚀 FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "✅ Backend is running."}


@app.get("/load_drive")
def load_and_process_drive(folder_id: str = Query(...)):
    print(f"📁 Loading files from Google Drive folder: {folder_id}")
    files = download_files_from_drive(folder_id)
    memory_store.clear()

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"📄 Extracting: {filename}")
        try:
            text = extract_text_from_file(filepath)
        except Exception as e:
            text = f"(Failed to extract: {str(e)})"

        cache_path = memory_store.get_cache_path(filename)
        file_hash = memory_store.text_hash(text)

        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("hash") == file_hash:
                print(f"⚡ Using cache for {filename}")
                summary = "(cached summary not stored)"
                memory_store.add_file_to_memory(filename, text, summary)
                continue

        try:
            print(f"🧠 Summarizing: {filename}")
            summary = summarize_with_ollama(text, model=SUMMARIZER_MODEL)
        except Exception as e:
            summary = f"(Summary failed: {str(e)})"

        memory_store.add_file_to_memory(filename, text, summary)

    return {
        "files": {
            fname: {
                "text": data["text"],
                "summary": data["summary"],
                "chunk_count": len(data["chunks"])
            }
            for fname, data in memory_store.file_memory.items()
        }
    }


@app.get("/clear_memory")
def clear_memory():
    memory_store.clear()
    return {"message": "✅ Memory cleared."}


@app.get("/load_history")
def load_history(folder_id: str = Query(...)):
    return {"history": load_chat_history(folder_id)}


# 📥 Request model
class AskRequest(BaseModel):
    question: str
    folder_id: str = ""
    history: list = []
    use_ollama: bool = False


@app.post("/ask")
def ask_question(payload: AskRequest):
    question = payload.question.strip()
    folder_id = payload.folder_id.strip()
    history = payload.history
    use_ollama = payload.use_ollama

    if not question:
        return {"answer": "(Missing question)", "sources": []}

    if folder_id:
        memory_store.load_folder_memory(folder_id)

    if not memory_store.file_memory:
        print(f"💬 Chat mode (no files): {question}")
        response = ask_openrouter_chat(question, history)
    else:
        print(f"🧐 Hybrid QA Mode: {question}")
        response = ask_question_hybrid(question, folder_id=folder_id, use_ollama=use_ollama)["answer"]

    timestamp = datetime.utcnow().isoformat()
    messages = history + [
        {
            "id": f"{int(datetime.utcnow().timestamp())}",
            "type": "user",
            "question": question,
            "answer": "",
            "feedback": "",
            "timestamp": timestamp
        },
        {
            "id": f"{int(datetime.utcnow().timestamp())+1}",
            "type": "assistant",
            "question": question,
            "answer": response,
            "feedback": "",
            "timestamp": timestamp
        }
    ]
    save_chat_history(folder_id, messages)
    return {"answer": response, "sources": []}


@app.post("/ask_best")
def ask_best_answer(payload: AskRequest):
    question = payload.question.strip()
    folder_id = payload.folder_id.strip()
    history = payload.history

    if not question:
        return {"answer": "(Missing question)", "sources": []}

    memory_store.load_folder_memory(folder_id)

    print(f"🧠 Multi-model RLHF QA: {question}")
    result = ask_multi_model_best(question, folder_id=folder_id)

    timestamp = datetime.utcnow().isoformat()
    messages = history + [
        {
            "id": f"{int(datetime.utcnow().timestamp())}",
            "type": "user",
            "question": question,
            "answer": "",
            "feedback": "",
            "timestamp": timestamp
        },
        {
            "id": f"{int(datetime.utcnow().timestamp())+1}",
            "type": "assistant",
            "question": question,
            "answer": result["answer"],
            "feedback": "",
            "timestamp": timestamp
        }
    ]
    save_chat_history(folder_id, messages)
    return result


@app.get("/export_training_data")
def export_training_data(folder_id: str = Query(...)):
    from pathlib import Path
    history = load_chat_history(folder_id)
    if not history:
        return {"message": "❌ No chat history found."}

    path = Path("backend/reward/training_data.jsonl")
    data = []
    pair = []

    for msg in history:
        if msg['type'] == 'user':
            pair = [{"role": "user", "content": msg["question"]}]
        elif msg['type'] == 'assistant' and pair:
            pair.append({"role": "assistant", "content": msg["answer"]})
            data.append({"messages": pair})
            pair = []

    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return {"message": f"✅ Exported {len(data)} pairs", "file": str(path)}


@app.get("/finetune_reward_model")
def finetune_reward_model():
    from reward.reward_model_trainer import main as run_finetune
    try:
        return {
            "message": "✅ Fine-tuning done." if run_finetune() else "❌ Failed.",
            "output_folder": "reward_model_output"
        }
    except Exception as e:
        return {"message": f"❌ Error: {str(e)}"}


@app.post("/rate_response")
async def rate_response(request: Request):
    try:
        data = await request.json()
        folder_id = data.get("folder_id", "unknown")
        os.makedirs("feedback", exist_ok=True)

        with open(f"feedback/{folder_id}_ratings.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "folder_id": folder_id,
                "question": data.get("question"),
                "answer": data.get("answer"),
                "score": data.get("score", 0)
            }) + "\n")

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Rating error: {e}")
        return {"status": "error", "message": str(e)}
