# reward/download_reward_model.py

from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

MODEL_NAME = "OpenAssistant/reward-model-mini"
SAVE_PATH = "./reward_model_output"

print(f"⬇️ Downloading model from {MODEL_NAME}...")

model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)

print(f"✅ Model and tokenizer saved to {SAVE_PATH}")
