# ✅ generate_reward_data.py

"""
Reads training_data.jsonl and creates reward_data.jsonl with preference pairs.
Each line: {"prompt": "...", "chosen": "...", "rejected": "..."}
"""

import os
import json
import random

BASE_DIR = os.path.dirname(__file__)
INPUT_PATH = os.path.join(BASE_DIR, "training_data.jsonl")
OUTPUT_PATH = os.path.join(BASE_DIR, "reward_data.jsonl")

if not os.path.exists(INPUT_PATH):
    print(f"❌ Cannot find {INPUT_PATH}. Skipping reward data generation.")
    exit(0)

num_in = 0
num_out = 0

with open(INPUT_PATH, "r", encoding="utf-8") as f_in, open(OUTPUT_PATH, "w", encoding="utf-8") as f_out:
    for line in f_in:
        line = line.strip()
        if not line:
            continue
        num_in += 1
        try:
            rec = json.loads(line)
        except Exception as e:
            print(f"⚠️ Skipping malformed line {num_in}: {e}")
            continue

        msgs = rec.get("messages", [])
        if len(msgs) < 2:
            continue

        # Extract prompt + assistant answer
        prompt = ""
        answer = ""
        for m in msgs:
            role = m.get("role")
            if role == "user" and not prompt:
                prompt = m.get("content", "")
            elif role == "assistant" and not answer:
                answer = m.get("content", "")

        if not prompt or not answer:
            continue

        # Simulate a bad (rejected) version
        words = answer.split()
        if len(words) > 10:
            bad = " ".join(words[:5]) + " ... (incomplete)"
        else:
            bad_opts = [
                "I don't know.",
                "No data.",
                "(failed to answer)",
                "Sorry, cannot help."
            ]
            bad = random.choice(bad_opts)

        out = {"prompt": prompt, "chosen": answer, "rejected": bad}
        f_out.write(json.dumps(out, ensure_ascii=False) + "\n")
        num_out += 1

print(f"✅ Done. Read {num_in} lines, wrote {num_out} reward pairs -> {OUTPUT_PATH}")
