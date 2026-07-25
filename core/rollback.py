from core.state import AgentState
from typing import Dict, Any, List
import os
import shutil
import json
from datetime import datetime
from models.mllm_registry import load_mllm
from governance.decision_logger import DecisionLogger
from core.operator_interface import OperatorInterface

ROLLBACK_DIR = "rollback_states"

def _ensure_rollback_dir():
    if not os.path.exists(ROLLBACK_DIR):
        os.makedirs(ROLLBACK_DIR)

class RollbackSafetyAssessor:
    def __init__(self):
        self.decision_logger = DecisionLogger()
        self.operator_interface = OperatorInterface()
    
    async def assess_rollback_safety(self, current_version: str, target_version: str, 
                                    current_state_schema: Dict, target_state_schema: Dict,
                                    mutation_id: str = None) -> Dict[str, Any]:
        """Assess rollback safety using Qwen2.5-14B"""
        
        rollback_model = load_mllm("Qwen2.5-14B-Instruct")
        
        schema_delta = self._get_schema_delta(current_state_schema, target_state_schema)
        
        prompt = f"""
        ROLLBACK SAFETY ASSESSMENT
        
        CURRENT VERSION: {current_version}
        TARGET VERSION: {target_version}
        
        CURRENT STATE SCHEMA:
        {json.dumps(list(current_state_schema.keys()), indent=2)}
        
        TARGET VERSION SCHEMA:
        {json.dumps(list(target_state_schema.keys()), indent=2)}
        
        SCHEMA CHANGES:
        {json.dumps(schema_delta, indent=2)}
        
        Analyze:
        1. Will fields in current state be lost?
        2. Will new fields in target state cause undefined behavior?
        3. Are there dependencies on the current version's state?
        
        Respond with JSON:
        {{
            "rollback_safe": boolean,
            "data_loss_risk": "NONE" | "MINOR" | "CRITICAL",
            "fields_lost": [...],
            "compatibility_issues": [...],
            "recommended_actions": [...],
            "operator_approval_required": boolean
        }}
        """
        
        response = rollback_model.invoke([{"role": "user", "content": prompt}])
        
        try:
            assessment = json.loads(response.content)
        except json.JSONDecodeError:
            assessment = {
                "rollback_safe": False,
                "data_loss_risk": "CRITICAL",
                "fields_lost": [],
                "compatibility_issues": ["Failed to parse assessment"],
                "recommended_actions": ["Manual review required"],
                "operator_approval_required": True
            }
        
        self.decision_logger.log(
            decision_type="ROLLBACK_SAFETY_CHECK",
            metadata={
                "current_version": current_version,
                "target_version": target_version,
                "assessment": assessment
            },
            mutation_id=mutation_id,
            model_used="Qwen2.5-14B-Instruct"
        )
        
        return assessment
    
    def _get_schema_delta(self, current_schema: Dict, target_schema: Dict) -> Dict:
        current_keys = set(current_schema.keys())
        target_keys = set(target_schema.keys())
        
        return {
            "fields_added": list(target_keys - current_keys),
            "fields_removed": list(current_keys - target_keys),
            "fields_retained": list(current_keys & target_keys)
        }

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
        "message_count": len(state["messages"]),
        "state_schema": list(state.keys())
    }

    filename = f"{ROLLBACK_DIR}/checkpoint_{checkpoint_id}.json"
    
    # Ensure directory exists before writing
    from pathlib import Path
    Path(ROLLBACK_DIR).mkdir(parents=True, exist_ok=True)
    
    with open(filename, "w") as f:
        json.dump(checkpoint, f, indent=2)

    print(f"[ROLLBACK] Created checkpoint {checkpoint_id}")
    return checkpoint_id

def rollback_to_checkpoint(state: AgentState, checkpoint_id: str) -> Dict[str, Any]:
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
