import torch
import torch.nn.functional as F
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 📍 Path to local reward model directory
MODEL_PATH = Path(__file__).parent / "reward_model_output"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ✅ Load model and tokenizer once at startup
try:
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_PATH), local_files_only=True)
    model.to(DEVICE)
    model.eval()
    print("✅ Reward model loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load reward model: {e}")
    tokenizer = None
    model = None

def score_response(prompt: str, response: str) -> float:
    """
    Scores (prompt, response) pair using the reward model.
    Returns a float score — higher means better.
    """
    if model is None or tokenizer is None:
        print("⚠️ Reward model not loaded — returning fallback score.")
        return -1.0

    try:
        text = f"Prompt: {prompt}\nResponse: {response}"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512).to(DEVICE)

        with torch.no_grad():
            logits = model(**inputs).logits

        # Handle both 1-logit (regression) and 2-logit (classification)
        if logits.shape[-1] == 1:
            score = torch.sigmoid(logits[0]).item()  # Convert regression logit to [0, 1] score
        elif logits.shape[-1] == 2:
            score = F.softmax(logits, dim=1)[0][1].item()  # Class 1 = "helpful"
        else:
            print(f"❌ Unexpected reward model output shape: {logits.shape}")
            score = -1.0
        return float(score)

    except Exception as e:
        print(f"❌ Scoring error: {e}")
        return -1.0  # Fallback score if something fails
