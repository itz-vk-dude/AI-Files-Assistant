# ✅ scripts/auto_retrain.py

import os
import time
import subprocess
from datetime import datetime

REWARD_PAIR_SCRIPT = "backend/reward/generate_reward_data.py"
TRAIN_SCRIPT = "backend/reward/reward_model_trainer.py"
REWARD_DATA = "backend/data/reward_data.jsonl"
CHECK_INTERVAL_SECONDS = 1200  # retrain every 1 hour
MIN_REQUIRED_PAIRS = 10

def get_reward_pair_count(path=REWARD_DATA):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f if _.strip())

def run_retrain_pipeline():
    print(f"\n⏳ [{datetime.now()}] Checking for new reward pairs...")

    # Step 1: Generate new reward pairs
    subprocess.run(["python", REWARD_PAIR_SCRIPT], check=True)

    # Step 2: Check count
    count = get_reward_pair_count()
    print(f"📊 Reward pairs available: {count}")

    if count >= MIN_REQUIRED_PAIRS:
        print(f"🏋️ Starting reward model training...")
        subprocess.run(["python", TRAIN_SCRIPT], check=True)
        print(f"✅ Training complete at {datetime.now()}")
    else:
        print(f"⚠️ Not enough reward pairs (need at least {MIN_REQUIRED_PAIRS}). Skipping training.")

def auto_loop():
    while True:
        try:
            run_retrain_pipeline()
        except Exception as e:
            print(f"❌ Retraining loop error: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    auto_loop()
