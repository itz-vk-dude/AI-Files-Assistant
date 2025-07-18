Here is a complete and clear `README.md` for your **PromptChain AI** backend project with RLHF support, numeric total merging, and multi-model QA:

---

```markdown
# 🤖 PromptChain AI – Backend

A powerful AI assistant backend for summarizing files from Google Drive, answering questions using LLMs, scoring answers with a reward model, and logging chat history. Supports multi-model querying, chunk-based context search, numeric answer merging, and RLHF-style feedback.

---

## 🚀 Features

- ✅ Load all file types from a **Google Drive folder**
- 📄 Extract text from `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.xml`, etc.
- 🧠 Summarize using **Ollama** (`llama3:8b`)
- ❓ Ask questions using:
  - 🔁 OpenRouter (e.g., Mistral)
  - 🔁 Ollama (e.g., DeepSeek Math)
- 🧠 Top-k chunk retrieval with sentence embeddings
- 📊 Merge numeric totals from multiple file chunks
- 💬 Chat history saved per folder
- 🏆 RLHF support with reward model scoring
- ⭐ Manual feedback rating (`👍` / `👎`)
- 🔁 Fine-tune reward model from logs

---

## 📦 Project Structure

```

backend/
│
├── main.py                    # FastAPI backend entry point
├── qa\_engine.py               # Multi-model hybrid QA engine
├── summarizer.py              # Ollama-based summarization
├── file\_processor.py          # Text extraction from various formats
├── drive\_handler.py           # Download files from Google Drive
├── chat\_history.py            # Per-folder chat log handling
│
├── reward/
│   ├── reward\_model.py        # Local scoring wrapper
│   ├── reward\_model\_trainer.py # RLHF-style fine-tuner
│
├── memory\_store.py            # In-memory file+chunk storage
├── embedding\_utils.py         # Chunk embedding utils
│
├── chat\_logs/                 # All chat histories per folder
├── feedback/                  # Feedback logs for training
└── reward\_model\_output/       # Fine-tuned reward model directory

````

---

## ⚙️ Setup Instructions

### 1. 📁 Install Python requirements

```bash
pip install -r requirements.txt
````

Required:

* `fastapi`, `uvicorn`
* `scikit-learn`, `requests`
* `sentence-transformers`, `python-docx`, `PyMuPDF`, `openpyxl`, `pandas`
* `ollama`, `google-api-python-client`, `pydantic`

---

### 2. 🚀 Start the backend server

```bash
cd backend
uvicorn main:app --reload
```

Server runs at:
📡 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

### 3. 🔗 Frontend integration (CORS)

Make sure your frontend is served at:

* [http://localhost:5173](http://localhost:5173)
* [http://127.0.0.1:5173](http://127.0.0.1:5173)

These are whitelisted for CORS in `main.py`.

---

## 🔍 API Endpoints

| Route                        | Description                                    |
| ---------------------------- | ---------------------------------------------- |
| `GET /`                      | Health check                                   |
| `GET /load_drive`            | Load and summarize all files from Drive folder |
| `GET /load_history`          | Load chat history for a folder                 |
| `POST /ask`                  | Ask a question (hybrid LLM)                    |
| `POST /ask_best`             | Ask question with RLHF reward selection        |
| `POST /rate_response`        | Rate an answer with 👍/👎                      |
| `GET /export_training_data`  | Export chat logs to `training_data.jsonl`      |
| `GET /finetune_reward_model` | Trigger fine-tuning of reward model            |

---

## ✅ RLHF Workflow

1. 🧠 Ask questions via `/ask_best`
2. 👍 / 👎 answers via `/rate_response`
3. 📤 Export logs: `/export_training_data`
4. 🧪 Fine-tune reward model: `/finetune_reward_model`
5. 🔁 System now scores future answers better!

---

## 🤝 Feedback Logging

Each feedback is saved to:

```
feedback/{folder_id}_ratings.jsonl

{
  "timestamp": "2025-07-18T10:00:00Z",
  "folder_id": "1W7nZ...TQ",
  "question": "...",
  "answer": "...",
  "score": 1
}
```

---

## 📌 Notes

* Automatically merges numeric totals when asking "total" questions.
* Automatically shortens verbose multi-source answers.
* Works offline via Ollama, or hybrid with OpenRouter if connected.

---

## 📣 Credits

Built by Vasantha Kumar S, Sarath KR,Yamini T,Ruthrabala S, Gayathri N, Sheerin Rizwana Y.with ❤️
Powered by FastAPI + Ollama + OpenRouter + HuggingFace

---
