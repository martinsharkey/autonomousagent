#!/usr/bin/env python3
"""Tool to log mutation outcomes and adjust learning rate based on success rate."""
import json
import os
from collections import deque

FEEDBACK_FILE = "evolution_feedback.json"
WINDOW_SIZE = 20

def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE) as f:
            return json.load(f)
    return {"outcomes": [], "learning_rate": 0.1}

def save_feedback(data):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

def record_outcome(success: bool):
    data = load_feedback()
    data["outcomes"].append(success)
    if len(data["outcomes"]) > WINDOW_SIZE:
        data["outcomes"] = data["outcomes"][-WINDOW_SIZE:]
    # Compute rolling success rate
    if len(data["outcomes"]) >= 5:
        recent = data["outcomes"][-5:]
        success_rate = sum(recent) / len(recent)
        # Adjust learning_rate: increase if success > 0.6, decrease if < 0.3
        if success_rate > 0.6:
            data["learning_rate"] = min(0.5, data["learning_rate"] * 1.1)
        elif success_rate < 0.3:
            data["learning_rate"] = max(0.01, data["learning_rate"] * 0.9)
    save_feedback(data)
    return data["learning_rate"]

def get_learning_rate():
    return load_feedback()["learning_rate"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        success = sys.argv[2].lower() == "true"
        new_lr = record_outcome(success)
        print(f"Recorded outcome, new learning_rate: {new_lr}")
    else:
        print(f"Current learning_rate: {get_learning_rate()}")
