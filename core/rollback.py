from core.state import AgentState
from typing import Dict, Any
import os
import shutil
from datetime import datetime

ROLLBACK_DIR = "rollback_states"

def _ensure_rollback_dir():
    if not os.path.exists(ROLLBACK_DIR):
        os.makedirs(ROLLBACK_DIR)

def create_checkpoint(state: AgentState, checkpoint_id: str = None):
    _ensure_rollback_dir()

    if checkpoint_id is None:
        checkpoint_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    checkpoint = {
        "id": checkpoint_id,
        "timestamp": datetime.utcnow().isoformat(),
        "loop_count": state["loop_count"],
        "completed_nodes": state.get("completed_nodes", []),
        "codebase_hash": state.get("codebase_hash", ""),
        "message_count": len(state["messages"])
    }

    filename = f"{ROLLBACK_DIR}/checkpoint_{checkpoint_id}.json"
    import json
    with open(filename, "w") as f:
        json.dump(checkpoint, f, indent=2)

    print(f"[ROLLBACK] Created checkpoint {checkpoint_id}")
    return checkpoint_id

def rollback_to_checkpoint(state: AgentState, checkpoint_id: str) -> Dict[str, Any]:
    import json
    filename = f"{ROLLBACK_DIR}/checkpoint_{checkpoint_id}.json"

    if not os.path.exists(filename):
        print(f"[ROLLBACK] Checkpoint {checkpoint_id} not found")
        return {
            "messages": [{"role": "system", "content": f"Rollback failed: checkpoint {checkpoint_id} not found"}],
            "completed_nodes": state.get("completed_nodes", [])
        }

    with open(filename, "r") as f:
        checkpoint = json.load(f)

    print(f"[ROLLBACK] Rolling back to checkpoint {checkpoint_id}")

    return {
        "messages": [{"role": "system", "content": f"Rolled back to checkpoint {checkpoint_id}. Retrying from stable state."}],
        "loop_count": checkpoint["loop_count"],
        "completed_nodes": checkpoint["completed_nodes"],
        "codebase_hash": checkpoint["codebase_hash"]
    }

def error_handler_node(state: AgentState) -> Dict[str, Any]:
    print(f"[ERROR HANDLER] Attempting recovery from error at loop {state['loop_count']}")

    if state["loop_count"] >= 5:
        return {
            "messages": [{"role": "system", "content": "Maximum retry attempts exceeded. Terminating workflow."}],
            "completed_nodes": state.get("completed_nodes", [])
        }

    checkpoints = []
    if os.path.exists(ROLLBACK_DIR):
        for filename in os.listdir(ROLLBACK_DIR):
            if filename.endswith(".json"):
                checkpoints.append(filename.replace("checkpoint_", "").replace(".json", ""))

    if checkpoints:
        checkpoints.sort(reverse=True)
        latest_checkpoint = checkpoints[0]
        return rollback_to_checkpoint(state, latest_checkpoint)

    return {
        "messages": [{"role": "system", "content": "No checkpoints available. Resetting to initial state."}],
        "loop_count": 0,
        "completed_nodes": []
    }
