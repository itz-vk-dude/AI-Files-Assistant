import os
import json
from datetime import datetime

CHAT_LOG_DIR = "chat_logs"
os.makedirs(CHAT_LOG_DIR, exist_ok=True)

def get_chat_path(folder_id):
    return os.path.join(CHAT_LOG_DIR, f"{folder_id}.json")

def save_chat_history(folder_id, messages):
    """
    Save the full chat history (list of message dicts) for a folder.
    Each message should have:
      - id, type, question, answer, feedback, timestamp
    """
    path = get_chat_path(folder_id)
    try:
        cleaned = []
        for msg in messages:
            msg_type = msg.get("type", "")
            if msg_type not in ["user", "assistant"]:
                continue  # skip invalid

            entry = {
                "id": msg.get("id", ""),
                "type": msg_type,
                "question": msg.get("question", "") if msg_type == "user" else "",
                "answer": msg.get("answer", "") if msg_type == "assistant" else "",
                "feedback": msg.get("feedback", ""),
                "timestamp": msg.get("timestamp", datetime.utcnow().isoformat())
            }

            # Avoid saving completely empty messages
            if entry["question"] or entry["answer"]:
                cleaned.append(entry)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error saving chat history for folder {folder_id}: {e}")

def load_chat_history(folder_id):
    path = get_chat_path(folder_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cleaned = []
                for msg in data:
                    msg_type = msg.get("type", "")
                    if msg_type not in ["user", "assistant"]:
                        continue  # skip corrupted entries

                    cleaned.append({
                        "id": msg.get("id", ""),
                        "type": msg_type,
                        "question": msg.get("question", "") if msg_type == "user" else "",
                        "answer": msg.get("answer", "") if msg_type == "assistant" else "",
                        "feedback": msg.get("feedback", ""),
                        "timestamp": msg.get("timestamp", datetime.utcnow().isoformat())
                    })
                return cleaned
        except Exception as e:
            print(f"❌ Error loading chat history for folder {folder_id}: {e}")
    return []

def list_all_chats():
    chats = []
    for filename in os.listdir(CHAT_LOG_DIR):
        if filename.endswith(".json"):
            folder_id = filename[:-5]
            history = load_chat_history(folder_id)
            if history:
                first_q = next((m["question"] for m in history if m["type"] == "user"), "Untitled Chat")
                last_a = next((m["answer"] for m in reversed(history) if m["answer"]), "")
                last_time = next((m["timestamp"] for m in reversed(history) if "timestamp" in m), datetime.utcnow().isoformat())
                chats.append({
                    "id": folder_id,
                    "title": first_q,
                    "lastMessage": last_a,
                    "messageCount": len(history),
                    "timestamp": last_time
                })
    return sorted(chats, key=lambda x: x["timestamp"], reverse=True)
