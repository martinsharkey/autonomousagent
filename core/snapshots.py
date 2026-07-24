from typing import Dict, Any, List
from core.state import AgentState
from datetime import datetime
import json
import os
import hashlib
import hmac
from governance.keys import get_snapshot_key

SNAPSHOT_DIR = "reasoning_snapshots"

def _ensure_snapshot_dir():
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)

def _compute_snapshot_hash(snapshot_data: Dict[str, Any]) -> str:
    snapshot_json = json.dumps(snapshot_data, sort_keys=True)
    return hashlib.sha256(snapshot_json.encode()).hexdigest()

def _compute_hmac(data: str, secret: str = None) -> str:
    if secret is None:
        secret = get_snapshot_key()
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()

def _get_last_snapshot_hash(node_name: str) -> str:
    _ensure_snapshot_dir()
    
    snapshot_files = []
    for filename in os.listdir(SNAPSHOT_DIR):
        if filename.endswith(".json") and node_name in filename:
            snapshot_files.append(filename)
    
    if not snapshot_files:
        return "genesis"
    
    snapshot_files.sort(reverse=True)
    latest_file = os.path.join(SNAPSHOT_DIR, snapshot_files[0])
    
    try:
        with open(latest_file, 'r') as f:
            snapshot = json.load(f)
            return snapshot.get("snapshot_hash", "genesis")
    except Exception:
        return "genesis"

def capture_snapshot(state: AgentState, node_name: str):
    _ensure_snapshot_dir()
    
    prev_hash = _get_last_snapshot_hash(node_name)

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": node_name,
        "loop_count": state["loop_count"],
        "message_count": len(state["messages"]),
        "last_message_preview": state["messages"][-1].content[:200] if state["messages"] else "",
        "completed_nodes": state.get("completed_nodes", []),
        "codebase_hash": state.get("codebase_hash", ""),
        "prev_hash": prev_hash
    }

    snapshot_hash = _compute_snapshot_hash(snapshot)
    snapshot["snapshot_hash"] = snapshot_hash
    
    hmac_signature = _compute_hmac(snapshot_hash)
    snapshot["hmac"] = hmac_signature

    filename = f"{SNAPSHOT_DIR}/snapshot_{node_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"[SNAPSHOT] Captured reasoning state for {node_name} at loop {state['loop_count']}")

def verify_snapshot_integrity(snapshot_file: str, secret: str = None) -> Dict[str, Any]:
    if secret is None:
        secret = get_snapshot_key()
    
    if not os.path.exists(snapshot_file):
        return {"valid": False, "error": "File not found"}
    
    try:
        with open(snapshot_file, 'r') as f:
            snapshot = json.load(f)
        
        if "snapshot_hash" not in snapshot:
            return {"valid": False, "error": "Missing snapshot_hash"}
        
        if "hmac" not in snapshot:
            return {"valid": False, "error": "Missing HMAC signature"}
        
        stored_hmac = snapshot["hmac"]
        snapshot_hash = snapshot["snapshot_hash"]
        computed_hmac = _compute_hmac(snapshot_hash, secret)
        
        if not hmac.compare_digest(stored_hmac, computed_hmac):
            return {"valid": False, "error": "HMAC verification failed"}
        
        return {"valid": True, "hash": snapshot_hash}
    
    except Exception as e:
        return {"valid": False, "error": str(e)}

def verify_snapshot_chain(node_name: str, secret: str = None) -> Dict[str, Any]:
    if secret is None:
        secret = get_snapshot_key()
    
    _ensure_snapshot_dir()
    
    snapshot_files = []
    for filename in os.listdir(SNAPSHOT_DIR):
        if filename.endswith(".json") and node_name in filename:
            snapshot_files.append(filename)
    
    if not snapshot_files:
        return {"valid": True, "snapshots": 0, "errors": []}
    
    snapshot_files.sort()
    errors = []
    expected_prev_hash = "genesis"
    
    for snapshot_file in snapshot_files:
        filepath = os.path.join(SNAPSHOT_DIR, snapshot_file)
        result = verify_snapshot_integrity(filepath, secret)
        
        if not result["valid"]:
            errors.append(f"{snapshot_file}: {result['error']}")
            continue
        
        with open(filepath, 'r') as f:
            snapshot = json.load(f)
        
        if snapshot.get("prev_hash") != expected_prev_hash:
            errors.append(f"{snapshot_file}: Chain broken - prev_hash mismatch")
        
        expected_prev_hash = snapshot["snapshot_hash"]
    
    return {
        "valid": len(errors) == 0,
        "snapshots": len(snapshot_files),
        "errors": errors
    }

def load_snapshots(node_name: str = None, limit: int = 10) -> list:
    _ensure_snapshot_dir()

    snapshots = []
    for filename in os.listdir(SNAPSHOT_DIR):
        if filename.endswith(".json"):
            if node_name and node_name not in filename:
                continue
            filepath = os.path.join(SNAPSHOT_DIR, filename)
            with open(filepath, "r") as f:
                snapshots.append(json.load(f))

    snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
    return snapshots[:limit]

def detect_semantic_loop(node_name: str, threshold: int = 3) -> bool:
    snapshots = load_snapshots(node_name, threshold)
    if len(snapshots) < threshold:
        return False

    recent_messages = [s["last_message_preview"] for s in snapshots]
    unique_messages = set(recent_messages)

    if len(unique_messages) < threshold * 0.5:
        print(f"[SEMANTIC LOOP DETECTED] Node {node_name} is repeating similar approaches")
        return True

    return False
