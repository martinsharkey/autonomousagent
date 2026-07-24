from typing import Dict, Any
from core.state import AgentState
from datetime import datetime
import json
import os

SNAPSHOT_DIR = "reasoning_snapshots"

def _ensure_snapshot_dir():
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)

def capture_snapshot(state: AgentState, node_name: str):
    _ensure_snapshot_dir()

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": node_name,
        "loop_count": state["loop_count"],
        "message_count": len(state["messages"]),
        "last_message_preview": state["messages"][-1].content[:200] if state["messages"] else "",
        "completed_nodes": state.get("completed_nodes", []),
        "codebase_hash": state.get("codebase_hash", "")
    }

    filename = f"{SNAPSHOT_DIR}/snapshot_{node_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"[SNAPSHOT] Captured reasoning state for {node_name} at loop {state['loop_count']}")

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
