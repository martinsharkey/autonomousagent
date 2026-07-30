import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

class StateRecoveryTool:
    """Tool to verify and repair checkpoint integrity."""
    
    def __init__(self, state_dir: str = "state", backup_dir: str = "backups"):
        self.state_dir = Path(state_dir)
        self.backup_dir = Path(backup_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def verify_checkpoint(self, checkpoint_path: str) -> dict:
        """Check integrity of a checkpoint file."""
        path = Path(checkpoint_path)
        if not path.exists():
            return {"valid": False, "error": "File not found"}
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            required_keys = ['timestamp', 'state', 'checksum']
            for key in required_keys:
                if key not in data:
                    return {"valid": False, "error": f"Missing key: {key}"}
            # Simple checksum verification
            computed = hash(json.dumps(data['state'], sort_keys=True))
            if computed != data['checksum']:
                return {"valid": False, "error": "Checksum mismatch"}
            return {"valid": True, "timestamp": data['timestamp']}
        except (json.JSONDecodeError, Exception) as e:
            return {"valid": False, "error": str(e)}
    
    def recover_from_backup(self, checkpoint_name: str) -> dict:
        """Restore latest valid backup for a checkpoint."""
        backup_pattern = f"{checkpoint_name}_*.bak"
        backups = sorted(self.backup_dir.glob(backup_pattern), reverse=True)
        for backup in backups:
            result = self.verify_checkpoint(str(backup))
            if result['valid']:
                # Restore to state directory
                target = self.state_dir / checkpoint_name
                with open(backup, 'r') as src:
                    data = json.load(src)
                with open(target, 'w') as dst:
                    json.dump(data, dst, indent=2)
                return {"success": True, "restored_from": str(backup), "timestamp": data['timestamp']}
        return {"success": False, "error": "No valid backup found"}
    
    def list_checkpoints(self) -> list:
        """List all checkpoint files with status."""
        checkpoints = []
        for f in self.state_dir.glob("*.json"):
            status = self.verify_checkpoint(str(f))
            checkpoints.append({
                "name": f.name,
                "valid": status['valid'],
                "error": status.get('error'),
                "timestamp": status.get('timestamp')
            })
        return checkpoints
    
    def create_backup(self, checkpoint_path: str) -> dict:
        """Create a timestamped backup of a checkpoint."""
        path = Path(checkpoint_path)
        if not path.exists():
            return {"success": False, "error": "Checkpoint not found"}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        with open(path, 'r') as src:
            data = src.read()
        with open(backup_path, 'w') as dst:
            dst.write(data)
        return {"success": True, "backup_path": str(backup_path)}

# Example usage
if __name__ == "__main__":
    tool = StateRecoveryTool()
    print(tool.list_checkpoints())
