import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.checkpointer import Checkpointer
from core.health_monitor import HealthMonitor

class StateRecoveryValidator:
    """
    Validates the integrity of agent state checkpoints to ensure reliable recovery.
    Checks for corruption, completeness, and consistency before recovery procedures.
    """

    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpointer = Checkpointer()
        self.health_monitor = HealthMonitor()

    def validate_checkpoint(self, checkpoint_id: str) -> Tuple[bool, str]:
        """
        Validate a specific checkpoint for integrity.
        Returns (is_valid, error_message).
        """
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_path.exists():
            return False, f"Checkpoint {checkpoint_id} not found"

        try:
            # Load and validate JSON structure
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)

            # Validate required fields
            required_fields = ['state', 'metadata', 'timestamp', 'checksum']
            for field in required_fields:
                if field not in checkpoint_data:
                    return False, f"Missing required field: {field}"

            # Verify checksum
            calculated_checksum = self._calculate_checksum(checkpoint_data['state'])
            if calculated_checksum != checkpoint_data['checksum']:
                return False, "Checksum mismatch - checkpoint may be corrupted"

            # Validate state structure
            if not self._validate_state_structure(checkpoint_data['state']):
                return False, "Invalid state structure"

            # Check health metrics
            health_status = self.health_monitor.check_system_health()
            if not health_status.get('healthy', False):
                return False, f"System unhealthy: {health_status.get('message', 'Unknown')}"

            return True, "Checkpoint valid"

        except json.JSONDecodeError:
            return False, "Invalid JSON format"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _calculate_checksum(self, state: Dict) -> str:
        """Calculate SHA-256 checksum of state for integrity verification."""
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    def _validate_state_structure(self, state: Dict) -> bool:
        """Validate the structure of agent state."""
        required_sections = ['agent_config', 'goals', 'memory', 'tools']
        for section in required_sections:
            if section not in state:
                return False
        return True

    def recover_from_checkpoint(self, checkpoint_id: str) -> Tuple[bool, str]:
        """
        Attempt recovery from a validated checkpoint.
        Returns (success, message).
        """
        is_valid, validation_msg = self.validate_checkpoint(checkpoint_id)
        if not is_valid:
            return False, f"Cannot recover from invalid checkpoint: {validation_msg}"

        try:
            # Load validated checkpoint
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)

            # Restore state
            self.checkpointer.restore_state(checkpoint_data['state'])
            return True, f"Successfully recovered from checkpoint {checkpoint_id}"

        except Exception as e:
            return False, f"Recovery failed: {str(e)}"

    def list_valid_checkpoints(self) -> Dict[str, str]:
        """List all valid checkpoints with their validation status."""
        valid_checkpoints = {}
        
        if not self.checkpoint_dir.exists():
            return valid_checkpoints

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoint_id = checkpoint_file.stem
            is_valid, msg = self.validate_checkpoint(checkpoint_id)
            valid_checkpoints[checkpoint_id] = {
                "valid": is_valid,
                "message": msg,
                "path": str(checkpoint_file)
            }

        return valid_checkpoints


def register_tool():
    """Register the state recovery validator as a tool."""
    validator = StateRecoveryValidator()
    
    def validate_checkpoint_tool(checkpoint_id: str) -> Dict:
        """Validate a checkpoint for recovery."""
        is_valid, message = validator.validate_checkpoint(checkpoint_id)
        return {
            "valid": is_valid,
            "message": message,
            "checkpoint_id": checkpoint_id
        }

    def recover_checkpoint_tool(checkpoint_id: str) -> Dict:
        """Recover agent state from a checkpoint."""
        success, message = validator.recover_from_checkpoint(checkpoint_id)
        return {
            "success": success,
            "message": message,
            "checkpoint_id": checkpoint_id
        }

    def list_checkpoints_tool() -> Dict:
        """List all available checkpoints with validation status."""
        return validator.list_valid_checkpoints()

    return {
        "name": "state_recovery_validator",
        "description": "Validates and recovers agent state from checkpoints",
        "tools": [
            {
                "name": "validate_checkpoint",
                "description": "Validate a checkpoint for integrity before recovery",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {
                            "type": "string",
                            "description": "ID of the checkpoint to validate"
                        }
                    },
                    "required": ["checkpoint_id"]
                },
                "handler": validate_checkpoint_tool
            },
            {
                "name": "recover_checkpoint",
                "description": "Recover agent state from a validated checkpoint",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {
                            "type": "string",
                            "description": "ID of the checkpoint to recover from"
                        }
                    },
                    "required": ["checkpoint_id"]
                },
                "handler": recover_checkpoint_tool
            },
            {
                "name": "list_checkpoints",
                "description": "List all available checkpoints with validation status",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": list_checkpoints_tool
            }
        ]
    }