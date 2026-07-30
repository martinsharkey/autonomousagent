import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from core.agent_config import AgentConfig
from governance.audit_log import audit_log

class StateRecoveryTool:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.current_checkpoint: Optional[str] = None

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum for data integrity verification."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _validate_checkpoint(self, checkpoint_path: Path) -> bool:
        """Validate checkpoint integrity by verifying checksum."""
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Verify required fields
            required_fields = ['state', 'checksum', 'timestamp']
            if not all(field in checkpoint_data for field in required_fields):
                return False
            
            # Verify checksum
            calculated_checksum = self._calculate_checksum(checkpoint_data['state'])
            if calculated_checksum != checkpoint_data['checksum']:
                return False
            
            return True
        except Exception as e:
            audit_log(f"Checkpoint validation failed: {str(e)}")
            return False

    def save_checkpoint(self, state: Dict[str, Any]) -> bool:
        """Save agent state to a durable checkpoint with integrity verification."""
        try:
            timestamp = int(time.time())
            checkpoint_data = {
                'state': state,
                'checksum': self._calculate_checksum(state),
                'timestamp': timestamp
            }
            
            checkpoint_path = self.checkpoint_dir / f"checkpoint_{timestamp}.json"
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f)
            
            self.current_checkpoint = str(checkpoint_path)
            audit_log(f"Checkpoint saved: {self.current_checkpoint}")
            return True
        except Exception as e:
            audit_log(f"Failed to save checkpoint: {str(e)}")
            return False

    def find_latest_valid_checkpoint(self) -> Optional[Path]:
        """Find the most recent valid checkpoint."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda x: int(x.stem.split('_')[-1]),
            reverse=True
        )
        
        for checkpoint in checkpoints:
            if self._validate_checkpoint(checkpoint):
                return checkpoint
        return None

    def recover_state(self) -> Optional[Dict[str, Any]]:
        """Recover agent state from the most recent valid checkpoint."""
        latest_checkpoint = self.find_latest_valid_checkpoint()
        if not latest_checkpoint:
            audit_log("No valid checkpoints found for recovery")
            return None
        
        try:
            with open(latest_checkpoint, 'r') as f:
                checkpoint_data = json.load(f)
            
            recovered_state = checkpoint_data['state']
            audit_log(f"State recovered from {latest_checkpoint}")
            return recovered_state
        except Exception as e:
            audit_log(f"Failed to recover state: {str(e)}")
            return None

    def cleanup_old_checkpoints(self, max_keep: int = 5) -> int:
        """Clean up old checkpoints, keeping only the most recent valid ones."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda x: int(x.stem.split('_')[-1]),
            reverse=True
        )
        
        removed_count = 0
        for checkpoint in checkpoints[max_keep:]:
            try:
                checkpoint.unlink()
                removed_count += 1
            except Exception as e:
                audit_log(f"Failed to remove checkpoint {checkpoint}: {str(e)}")
        
        return removed_count

# Tool interface for MCP registry
state_recovery_tool = StateRecoveryTool()

def recover_state() -> dict:
    """Recover agent state from the most recent valid checkpoint."""
    recovered_state = state_recovery_tool.recover_state()
    if recovered_state:
        return {"status": "success", "state": recovered_state}
    return {"status": "failed", "reason": "No valid checkpoints found"}

def save_checkpoint(state: dict) -> dict:
    """Save agent state to a durable checkpoint."""
    success = state_recovery_tool.save_checkpoint(state)
    if success:
        return {"status": "success"}
    return {"status": "failed", "reason": "Checkpoint save failed"}

def cleanup_checkpoints(max_keep: int = 5) -> dict:
    """Clean up old checkpoints."""
    removed = state_recovery_tool.cleanup_old_checkpoints(max_keep)
    return {"status": "success", "removed_count": removed}