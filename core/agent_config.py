"""
Versioned agent configuration store.
Agents load their active config on every entry.
Mutations create new versions; evaluation gates promotion.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from governance.decision_logger import DecisionLogger


DEFAULT_CONFIGS = {
    "autobot": {
        "temperature": 0.2,
        "max_retries": 3,
        "system_prompt": "You are Autobot, the security auditor and orchestrator.",
        "strategy_flags": {"security_focus": True},
        "allowed_tools": ["editor", "shell_exec"],
        "version": "v1.0.0",
        "status": "active"
    },
    "alpha_evaluator": {
        "temperature": 0.1,
        "max_retries": 3,
        "system_prompt": "You are Alpha, the mission alignment evaluator.",
        "strategy_flags": {"mission_focus": True},
        "allowed_tools": ["editor"],
        "version": "v1.0.0",
        "status": "active"
    },
    "beta_worker": {
        "temperature": 0.3,
        "max_retries": 3,
        "system_prompt": "You are Beta, the feasibility evaluator and worker.",
        "strategy_flags": {"execution_focus": True},
        "allowed_tools": ["editor", "shell_exec", "load_tool"],
        "version": "v1.0.0",
        "status": "active"
    }
}


class AgentConfigStore:
    """Versioned agent configuration store with promote/rollback."""
    
    def __init__(self, storage_dir: Path = Path("./agent_configs")):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        self.decision_logger = DecisionLogger()
        
        # Initialize default configs if not present
        for agent_name, config in DEFAULT_CONFIGS.items():
            agent_dir = self.storage_dir / agent_name
            agent_dir.mkdir(exist_ok=True)
            
            active_file = agent_dir / "active.json"
            if not active_file.exists():
                self._save_version(agent_name, "v1.0.0", config)
                self._set_active(agent_name, "v1.0.0")
    
    def get_active(self, agent_name: str) -> Dict[str, Any]:
        """Get the currently active config for an agent."""
        agent_dir = self.storage_dir / agent_name
        active_file = agent_dir / "active.json"
        
        if not active_file.exists():
            raise FileNotFoundError(f"No active config for {agent_name}")
        
        with open(active_file, "r") as f:
            active_info = json.load(f)
        
        version = active_info["version"]
        return self._load_version(agent_name, version)
    
    def create_version(
        self,
        agent_name: str,
        changes: Dict[str, Any],
        parent_version: str,
        mutation_id: str
    ) -> str:
        """Create a new config version. Returns new version_id."""
        current_config = self._load_version(agent_name, parent_version)
        
        # Merge changes
        new_config = current_config.copy()
        for key, value in changes.items():
            if isinstance(value, dict) and key in new_config and isinstance(new_config[key], dict):
                new_config[key].update(value)
            else:
                new_config[key] = value
        
        # Generate version ID
        config_hash = hashlib.sha256(json.dumps(new_config, sort_keys=True).encode()).hexdigest()[:12]
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{config_hash}"
        
        new_config["version"] = version_id
        new_config["parent_version"] = parent_version
        new_config["mutation_id"] = mutation_id
        new_config["status"] = "candidate"
        new_config["created_at"] = datetime.now().isoformat()
        
        self._save_version(agent_name, version_id, new_config)
        
        self.decision_logger.log(
            decision_type="CONFIG_VERSION_CREATED",
            metadata={
                "agent": agent_name,
                "version": version_id,
                "parent": parent_version,
                "mutation_id": mutation_id,
                "changes": changes
            },
            mutation_id=mutation_id
        )
        
        return version_id
    
    def promote(self, agent_name: str, version: str) -> None:
        """Promote a version to active."""
        self._set_active(agent_name, version)
        
        # Update status in version file
        config = self._load_version(agent_name, version)
        config["status"] = "active"
        config["promoted_at"] = datetime.now().isoformat()
        self._save_version(agent_name, version, config)
        
        self.decision_logger.log(
            decision_type="CONFIG_PROMOTED",
            metadata={
                "agent": agent_name,
                "version": version
            }
        )
        
        print(f"[CONFIG] Promoted {agent_name} to {version}")
    
    def rollback(self, agent_name: str, to_version: str) -> None:
        """Rollback to a previous version."""
        self._set_active(agent_name, to_version)
        
        config = self._load_version(agent_name, to_version)
        config["status"] = "active"
        config["rolled_back_at"] = datetime.now().isoformat()
        self._save_version(agent_name, to_version, config)
        
        self.decision_logger.log(
            decision_type="CONFIG_ROLLBACK",
            metadata={
                "agent": agent_name,
                "version": to_version
            }
        )
        
        print(f"[CONFIG] Rolled back {agent_name} to {to_version}")
    
    def get_version_history(self, agent_name: str) -> List[Dict]:
        """Get version history for an agent."""
        agent_dir = self.storage_dir / agent_name
        versions = []
        
        for version_file in agent_dir.glob("v*.json"):
            if version_file.name == "active.json":
                continue
            
            with open(version_file, "r") as f:
                config = json.load(f)
            
            versions.append({
                "version": config.get("version"),
                "status": config.get("status"),
                "parent_version": config.get("parent_version"),
                "mutation_id": config.get("mutation_id"),
                "created_at": config.get("created_at"),
                "promoted_at": config.get("promoted_at")
            })
        
        return sorted(versions, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def _load_version(self, agent_name: str, version: str) -> Dict[str, Any]:
        """Load a specific version."""
        agent_dir = self.storage_dir / agent_name
        version_file = agent_dir / f"{version}.json"
        
        if not version_file.exists():
            raise FileNotFoundError(f"Version {version} not found for {agent_name}")
        
        with open(version_file, "r") as f:
            return json.load(f)
    
    def _save_version(self, agent_name: str, version: str, config: Dict) -> None:
        """Save a version."""
        agent_dir = self.storage_dir / agent_name
        agent_dir.mkdir(exist_ok=True)
        version_file = agent_dir / f"{version}.json"
        
        with open(version_file, "w") as f:
            json.dump(config, f, indent=2)
    
    def _set_active(self, agent_name: str, version: str) -> None:
        """Set the active version."""
        agent_dir = self.storage_dir / agent_name
        
        # Ensure directory exists before writing
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        active_file = agent_dir / "active.json"
        
        with open(active_file, "w") as f:
            json.dump({"version": version, "updated_at": datetime.now().isoformat()}, f)


_global_config_store: Optional[AgentConfigStore] = None


def get_config_store() -> AgentConfigStore:
    """Get or create the global config store instance."""
    global _global_config_store
    if _global_config_store is None:
        _global_config_store = AgentConfigStore()
    return _global_config_store
