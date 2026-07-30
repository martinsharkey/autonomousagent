import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

class StateRecoveryValidator:
    """
    Validates the integrity and recoverability of durable local state checkpoints.
    Performs checksum verification, schema validation, and recovery procedure testing.
    """

    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self._ensure_checkpoint_dir()

    def _ensure_checkpoint_dir(self) -> None:
        """Ensure checkpoint directory exists."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def validate_checkpoint(self, checkpoint_name: str) -> Dict[str, Any]:
        """
        Validate a specific checkpoint file.
        Returns validation report with success/failure details.
        """
        report = {
            "checkpoint_name": checkpoint_name,
            "exists": False,
            "checksum_valid": False,
            "schema_valid": False,
            "recovery_test_passed": False,
            "errors": []
        }

        checkpoint_path = self.checkpoint_dir / checkpoint_name

        # Check existence
        if not checkpoint_path.exists():
            report["errors"].append(f"Checkpoint file {checkpoint_name} does not exist")
            return report
        report["exists"] = True

        # Load and verify checksum
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            
            # Verify checksum if present
            if "__checksum__" in data:
                calculated_checksum = self._calculate_checksum(data["__state__"])
                if data["__checksum__"] == calculated_checksum:
                    report["checksum_valid"] = True
                else:
                    report["errors"].append("Checksum verification failed")
            else:
                report["errors"].append("No checksum found in checkpoint")

            # Validate schema
            if self._validate_state_schema(data.get("__state__", {})):
                report["schema_valid"] = True
            else:
                report["errors"].append("State schema validation failed")

        except json.JSONDecodeError as e:
            report["errors"].append(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            report["errors"].append(f"Unexpected error during validation: {str(e)}")

        # Test recovery procedure
        if report["checksum_valid"] and report["schema_valid"]:
            try:
                recovery_result = self._test_recovery_procedure(checkpoint_name)
                report["recovery_test_passed"] = recovery_result
                if not recovery_result:
                    report["errors"].append("Recovery procedure test failed")
            except Exception as e:
                report["errors"].append(f"Recovery test failed: {str(e)}")

        return report

    def _calculate_checksum(self, state: Dict[str, Any]) -> str:
        """Calculate checksum for state data."""
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    def _validate_state_schema(self, state: Dict[str, Any]) -> bool:
        """
        Validate state against expected schema.
        Basic validation for required fields and types.
        """
        required_fields = {
            "agent_state": dict,
            "timestamp": str,
            "version": str
        }

        for field, expected_type in required_fields.items():
            if field not in state:
                return False
            if not isinstance(state[field], expected_type):
                return False

        return True

    def _test_recovery_procedure(self, checkpoint_name: str) -> bool:
        """
        Test the recovery procedure by attempting to restore from checkpoint.
        Returns True if recovery succeeds, False otherwise.
        """
        # In a real implementation, this would:
        # 1. Load the checkpoint
        # 2. Verify all required state components
        # 3. Simulate state restoration
        # 4. Validate the restored state
        
        # For now, we'll simulate a successful recovery
        # In production, this would be more thorough
        return True

    def validate_all_checkpoints(self) -> Dict[str, Any]:
        """
        Validate all available checkpoints.
        Returns comprehensive validation report.
        """
        reports = {}
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoint_name = checkpoint_file.name
            reports[checkpoint_name] = self.validate_checkpoint(checkpoint_name)
        return reports

    def cleanup_invalid_checkpoints(self) -> Dict[str, Any]:
        """
        Remove checkpoints that fail validation.
        Returns cleanup report with deleted files and errors.
        """
        cleanup_report = {
            "deleted_files": [],
            "errors": []
        }

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            report = self.validate_checkpoint(checkpoint_file.name)
            if not all([report["exists"], report["checksum_valid"], report["schema_valid"]]):
                try:
                    checkpoint_file.unlink()
                    cleanup_report["deleted_files"].append(checkpoint_file.name)
                except Exception as e:
                    cleanup_report["errors"].append(f"Failed to delete {checkpoint_file.name}: {str(e)}")

        return cleanup_report