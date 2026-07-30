import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional
from governance.audit_log import verify_audit_log
from core.goals import GoalStore
from core.agent_config import AgentConfigStore

class StateRecoveryValidator:
    """
    Validates and repairs durable local state components:
    - Goal store consistency
    - Agent config integrity
    - Audit log verification
    - Corrupted file detection
    """
    
    def __init__(self, state_dir: str = "./state"):
        self.state_dir = Path(state_dir)
        self.goal_store_path = self.state_dir / "goals.db"
        self.config_store_path = self.state_dir / "config.json"
        self.audit_log_path = self.state_dir / "audit.log"
    
    def validate_all(self) -> Dict[str, bool]:
        """Run all validation checks and return results."""
        results = {
            "goal_store": self.validate_goal_store(),
            "config_store": self.validate_config_store(),
            "audit_log": self.validate_audit_log(),
            "state_dir": self.validate_state_dir()
        }
        return results
    
    def validate_goal_store(self) -> bool:
        """Check SQLite goal store for corruption and consistency."""
        try:
            conn = sqlite3.connect(str(self.goal_store_path))
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT COUNT(*) FROM goals")
            count = cursor.fetchone()[0]
            
            # Verify goal structure
            cursor.execute("SELECT id, goal_text, status FROM goals LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return False
                
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Goal store corruption detected: {e}")
            return False
    
    def validate_config_store(self) -> bool:
        """Check JSON config file for corruption and schema validity."""
        try:
            if not self.config_store_path.exists():
                return False
                
            with open(self.config_store_path, 'r') as f:
                config = json.load(f)
            
            # Basic schema validation
            required_keys = ["version", "max_retries", "system_prompt"]
            if not all(key in config for key in required_keys):
                return False
                
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Config store corruption detected: {e}")
            return False
    
    def validate_audit_log(self) -> bool:
        """Verify audit log integrity using HMAC checks."""
        try:
            if not self.audit_log_path.exists():
                return True  # No log is valid if it doesn't exist
            return verify_audit_log(str(self.audit_log_path))
        except Exception as e:
            print(f"Audit log verification failed: {e}")
            return False
    
    def validate_state_dir(self) -> bool:
        """Check state directory exists and is writable."""
        try:
            if not self.state_dir.exists():
                return False
            if not self.state_dir.is_dir():
                return False
            # Test write permission
            test_file = self.state_dir / ".test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            print(f"State directory validation failed: {e}")
            return False
    
    def repair_goal_store(self) -> bool:
        """Attempt to repair corrupted goal store."""
        try:
            # Backup current DB
            backup_path = self.goal_store_path.with_suffix(".bak")
            if self.goal_store_path.exists():
                self.goal_store_path.rename(backup_path)
            
            # Create new DB with proper schema
            GoalStore(str(self.state_dir)).__init__()  # Reinitialize with default schema
            return True
        except Exception as e:
            print(f"Goal store repair failed: {e}")
            return False
    
    def repair_config_store(self) -> bool:
        """Attempt to repair corrupted config file."""
        try:
            # Create default config
            default_config = {
                "version": "1.0",
                "max_retries": 3,
                "system_prompt": "You are an autonomous agent. Be helpful and safe."
            }
            with open(self.config_store_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return True
        except Exception as e:
            print(f"Config store repair failed: {e}")
            return False
    
    def run_recovery_procedure(self) -> Dict[str, str]:
        """Execute recovery procedure based on validation results."""
        results = self.validate_all()
        recovery_report = {}
        
        if not results["goal_store"]:
            recovery_report["goal_store"] = "attempting repair..."
            if self.repair_goal_store():
                recovery_report["goal_store"] = "repaired successfully"
            else:
                recovery_report["goal_store"] = "repair failed"
        
        if not results["config_store"]:
            recovery_report["config_store"] = "attempting repair..."
            if self.repair_config_store():
                recovery_report["config_store"] = "repaired successfully"
            else:
                recovery_report["config_store"] = "repair failed"
        
        if not results["audit_log"]:
            recovery_report["audit_log"] = "audit log corrupted - manual intervention required"
        
        if not results["state_dir"]:
            recovery_report["state_dir"] = "state directory missing or inaccessible"
        
        return recovery_report

# CLI interface for the tool
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="State Recovery Validator")
    parser.add_argument("--validate", action="store_true", help="Run validation checks")
    parser.add_argument("--recover", action="store_true", help="Run recovery procedure")
    parser.add_argument("--state-dir", default="./state", help="State directory path")
    
    args = parser.parse_args()
    
    validator = StateRecoveryValidator(args.state_dir)
    
    if args.validate:
        results = validator.validate_all()
        print("Validation Results:")
        for key, value in results.items():
            print(f"  {key}: {'OK' if value else 'FAILED'}")
    
    if args.recover:
        report = validator.run_recovery_procedure()
        print("Recovery Report:")
        for key, value in report.items():
            print(f"  {key}: {value}")