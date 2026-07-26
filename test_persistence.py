"""Test that state persists across daemon restarts."""

import os
import time
import json
from pathlib import Path

if Path("./checkpoints.json").exists():
    Path("./checkpoints.json").unlink()

print("Session 1: Saving state...")
from core.checkpointer import JSONCheckpointer

cp1 = JSONCheckpointer(filepath="./checkpoints.json")
state = {
    "agent": "autobot",
    "step": 42,
    "messages": ["goal created", "executing"]
}
cp1.save_checkpoint("session_test_001", state)
print(f"  Saved: {state}")

print("\nSession 2: Simulating restart...")

cp2 = JSONCheckpointer(filepath="./checkpoints.json")
loaded = cp2.load_checkpoint("session_test_001")

if loaded is None:
    print("FAILED: State was lost on restart")
    exit(1)

if loaded == state:
    print(f"  State restored: {loaded}")
    print("PASSED: State persists across restarts")
else:
    print(f"FAILED: State mismatch")
    print(f"  Expected: {state}")
    print(f"  Got: {loaded}")
    exit(1)
