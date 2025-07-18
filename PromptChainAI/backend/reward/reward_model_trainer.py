"""
reward_model_finetune.py

Trains a simple *pairwise ranking* reward model from reward_data.jsonl.
Loss: -logsigmoid(score_chosen - score_rejected)

Base model: distilbert-base-uncased (lightweight, CPU-friendly).
Outputs saved to ./reward_model_output
"""

import os
import json
from typing import List, Dict
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup, AdamW

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "reward_data.jsonl")
OUT_DIR = os.path.join(BASE_DIR, "reward_model_output")
os.makedirs(OUT_DIR, exist_ok=True)

MODEL_NAME = "distilbert-base-uncased"  # change if you want bigger

MAX_LEN = 512
BATCH_SIZE = 4
EPOCHS = 3
LR = 5e-5
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------
# Load reward data
# --------------------------
def load_reward_pairs(path: str) -> List[Dict]:
    pairs = []
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ reward data not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"⚠️ Skipping bad line {i}: {e}")
                continue

            prompt = obj.get("prompt", "")
            chosen = obj.get("chosen", "")
            rejected = obj.get("rejected", "")

            if not prompt or not chosen or not rejected:
                continue

            pairs.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})

    return pairs


# --------------------------
# Dataset
# --------------------------
class RewardPairDataset(Dataset):
    def __init__(self, pairs, tokenizer, max_len=512):
        self.pairs = pairs
        self.tok = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        item = self.pairs[idx]
        prompt = item["prompt"]

        chosen_txt = f"Prompt: {prompt}\nResponse: {item['chosen']}"
        rej_txt    = f"Prompt: {prompt}\nResponse: {item['rejected']}"

        chosen_enc = self.tok(
            chosen_txt,
            truncation=True,
            max_length=self.max_len,
            padding="max_length",
            return_tensors="pt",
        )
        rej_enc = self.tok(
            rej_txt,
            truncation=True,
            max_length=self.max_len,
            padding="max_length",
            return_tensors="pt",
        )

        return {
            "input_ids_chosen": chosen_enc["input_ids"].squeeze(0),
            "attention_mask_chosen": chosen_enc["attention_mask"].squeeze(0),
            "input_ids_rejected": rej_enc["input_ids"].squeeze(0),
            "attention_mask_rejected": rej_enc["attention_mask"].squeeze(0),
        }


# --------------------------
# Train Loop
# --------------------------
def train():
    print("🚀 Loading reward pairs...")
    pairs = load_reward_pairs(DATA_PATH)
    if not pairs:
        print("❌ No training pairs found. Run generate_reward_data.py first.")
        return False
    print(f"✅ Loaded {len(pairs)} pairs.")

    print("📥 Loading model & tokenizer:", MODEL_NAME)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=1)
    model.to(DEVICE)

    ds = RewardPairDataset(pairs, tok, max_len=MAX_LEN)
    dl = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=True)

    optim = AdamW(model.parameters(), lr=LR)
    total_steps = len(dl) * EPOCHS
    sched = get_linear_schedule_with_warmup(
        optim,
        num_warmup_steps=max(1, int(0.05 * total_steps)),
        num_training_steps=total_steps,
    )

    model.train()
    step = 0
    for epoch in range(EPOCHS):
        print(f"\n===== Epoch {epoch+1}/{EPOCHS} =====")
        for batch in dl:
            step += 1
            optim.zero_grad()

            # Move tensors
            ic = batch["input_ids_chosen"].to(DEVICE)
            ac = batch["attention_mask_chosen"].to(DEVICE)
            ir = batch["input_ids_rejected"].to(DEVICE)
            ar = batch["attention_mask_rejected"].to(DEVICE)

            out_c = model(input_ids=ic, attention_mask=ac).logits  # (B,1)
            out_r = model(input_ids=ir, attention_mask=ar).logits  # (B,1)

            # Pairwise ranking loss
            diff = out_c - out_r
            loss = -torch.nn.functional.logsigmoid(diff).mean()

            loss.backward()
            optim.step()
            sched.step()

            if step % 10 == 0:
                print(f"step {step} | loss {loss.item():.4f}")

    # Save
    print("\n💾 Saving reward model to:", OUT_DIR)
    model.save_pretrained(OUT_DIR)
    tok.save_pretrained(OUT_DIR)
    print("✅ Done.")
    return True


if __name__ == "__main__":
    train()
