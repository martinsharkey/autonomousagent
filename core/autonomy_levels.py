"""
Autonomy levels for production hardening.
Defines safe, limited, and full autonomy modes.
"""

from enum import Enum
from typing import Dict, Any


class AutonomyLevel(Enum):
    SAFE = "safe"
    LIMITED = "limited"
    FULL = "full"


AUTONOMY_LEVEL_CONFIG = {
    AutonomyLevel.SAFE: {
        "allow_mutations": False,
        "allow_code_execution": False,
        "allow_sandbox": False,
        "allow_evolution": False,
        "require_human_approval": True,
        "description": "No mutations, no code execution. Human approves everything."
    },
    AutonomyLevel.LIMITED: {
        "allow_mutations": True,
        "allow_code_execution": False,
        "allow_sandbox": True,
        "allow_evolution": True,
        "require_human_approval": True,
        "max_risk_level": "low",
        "description": "Low-risk mutations only. Human approves medium/high risk."
    },
    AutonomyLevel.FULL: {
        "allow_mutations": True,
        "allow_code_execution": True,
        "allow_sandbox": True,
        "allow_evolution": True,
        "require_human_approval": False,
        "max_risk_level": "high",
        "description": "Full autonomy. Low/medium auto-approved, high requires human."
    }
}


class AutonomyController:
    """Controls autonomy level and enforces restrictions."""
    
    def __init__(self, level: AutonomyLevel = AutonomyLevel.LIMITED):
        self.current_level = level
        self.config = AUTONOMY_LEVEL_CONFIG[level]
    
    def set_level(self, level: AutonomyLevel):
        """Set autonomy level."""
        self.current_level = level
        self.config = AUTONOMY_LEVEL_CONFIG[level]
        print(f"[AUTONOMY] Level set to {level.value}: {self.config['description']}")
    
    def can_mutate(self, risk_level: str = "low") -> bool:
        """Check if mutation is allowed at current autonomy level."""
        if not self.config["allow_mutations"]:
            return False
        
        max_risk = self.config.get("max_risk_level", "low")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        
        return risk_order.get(risk_level, 0) <= risk_order.get(max_risk, 0)
    
    def can_execute_code(self) -> bool:
        """Check if code execution is allowed."""
        return self.config["allow_code_execution"]
    
    def can_use_sandbox(self) -> bool:
        """Check if sandbox execution is allowed."""
        return self.config["allow_sandbox"]
    
    def can_evolve(self) -> bool:
        """Check if evolution is allowed."""
        return self.config["allow_evolution"]
    
    def requires_human_approval(self, risk_level: str = "low") -> bool:
        """Check if human approval is required."""
        if self.config["require_human_approval"]:
            return True
        
        # In FULL mode, only high-risk requires approval
        if risk_level == "high":
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current autonomy status."""
        return {
            "level": self.current_level.value,
            "config": self.config,
            "can_mutate": self.config["allow_mutations"],
            "can_execute_code": self.config["allow_code_execution"],
            "can_use_sandbox": self.config["allow_sandbox"],
            "can_evolve": self.config["allow_evolution"],
            "require_human_approval": self.config["require_human_approval"]
        }


_global_autonomy_controller: AutonomyController = None


def get_autonomy_controller() -> AutonomyController:
    """Get or create the global autonomy controller."""
    global _global_autonomy_controller
    if _global_autonomy_controller is None:
        _global_autonomy_controller = AutonomyController()
    return _global_autonomy_controller
