import json
import os
import hashlib
from pathlib import Path

CHECKPOINT_DIR = Path("checkpoints")
INTEGRITY_LOG = Path("logs/state_integrity.log")

def compute_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def verify_checkpoint(checkpoint_path: Path) -> bool:
    try:
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
        stored_hash = data.get("_integrity_hash")
        if not stored_hash:
            return False
        computed = compute_hash({k: v for k, v in data.items() if k != "_integrity_hash"})
        return stored_hash == computed
    except (json.JSONDecodeError, IOError, KeyError):
        return False

def find_latest_valid() -> Path | None:
    if not CHECKPOINT_DIR.exists():
        return None
    checkpoints = sorted(CHECKPOINT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    for cp in checkpoints:
        if verify_checkpoint(cp):
            return cp
    return None

def run_integrity_check() -> dict:
    results = {"valid": [], "corrupt": [], "latest_valid": None}
    if not CHECKPOINT_DIR.exists():
        return results
    for cp in sorted(CHECKPOINT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        if verify_checkpoint(cp):
            results["valid"].append(str(cp))
        else:
            results["corrupt"].append(str(cp))
    latest = find_latest_valid()
    if latest:
        results["latest_valid"] = str(latest)
    with open(INTEGRITY_LOG, "a") as log:
        log.write(json.dumps(results) + "\n")
    return results

if __name__ == "__main__":
    print(json.dumps(run_integrity_check(), indent=2))
