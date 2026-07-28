import json
import hashlib
import os

CHECKPOINT_DIR = "checkpoints"
MAX_CHECKPOINTS = 5

def _checkpoint_path(name):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    return os.path.join(CHECKPOINT_DIR, f"{name}.json")

def save_checkpoint(name, state):
    path = _checkpoint_path(name)
    serialized = json.dumps(state, sort_keys=True)
    checksum = hashlib.sha256(serialized.encode()).hexdigest()
    with open(path, "w") as f:
        json.dump({"state": state, "checksum": checksum}, f)
    # Rotate old checkpoints
    checkpoints = sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")])
    while len(checkpoints) > MAX_CHECKPOINTS:
        os.remove(os.path.join(CHECKPOINT_DIR, checkpoints.pop(0)))

def load_checkpoint(name):
    path = _checkpoint_path(name)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        data = json.load(f)
    serialized = json.dumps(data["state"], sort_keys=True)
    expected = hashlib.sha256(serialized.encode()).hexdigest()
    if data["checksum"] != expected:
        raise ValueError("Checkpoint corrupted")
    return data["state"]

def list_checkpoints():
    if not os.path.exists(CHECKPOINT_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")]
