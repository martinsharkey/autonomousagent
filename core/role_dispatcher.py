"""Role-based task dispatcher for the council.

The council detects system signals (performance degradation, bloat, errors)
and dispatches tasks to the appropriate role/agent. Each role has:
- A set of capabilities (what it can do)
- Callable actions (functions it can invoke directly)
- Self-modification ability (can write new tools via the editor)

Usage in agent_loop.py:
    dispatcher = get_role_dispatcher()
    dispatcher.dispatch_signal("bloat_detected", {"bytes": 50_000_000})
    # → Creates a goal assigned to "janitor" role
    
    dispatcher.dispatch_signal("architecture_concern", {"issue": "duplicate tools"})  
    # → Creates a goal assigned to "architect" role
"""

import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path


# Role definitions: what each role is responsible for
ROLE_CAPABILITIES = {
    "janitor": {
        "description": "Repository cleanup, bloat prevention, dead code removal",
        "triggers": ["bloat_detected", "stale_files", "disk_pressure", "duplicate_tools"],
        "actions": {
            "cleanup": "tools.repo_janitor.cleanup",
            "audit": "tools.repo_janitor.full_audit",
            "tool_quality": "tools.auto_discovery.audit_tool_quality",
        },
        "can_self_modify": True,
        "assigned_agent": "beta_worker",  # Beta handles maintenance tasks
    },
    "architect": {
        "description": "Design review, performance optimization, consolidation",
        "triggers": ["architecture_concern", "performance_degradation", "tool_overlap", "design_review"],
        "actions": {
            "review": "tools.repo_janitor.generate_council_report",
            "discover_tools": "tools.auto_discovery.discover_and_register",
        },
        "can_self_modify": True,
        "assigned_agent": "autobot",  # Autobot handles architectural decisions
    },
    "security": {
        "description": "Security scanning, secret rotation, hardening",
        "triggers": ["security_alert", "secret_exposed", "dependency_vuln"],
        "actions": {
            "pentest": "core.self_pentest.get_self_pentest",
            "threat_assess": "core.security_awareness.assess_threat_surface",
        },
        "can_self_modify": False,
        "assigned_agent": "alpha_evaluator",  # Alpha evaluates security
    },
}


class RoleDispatcher:
    """Dispatches tasks to roles based on system signals."""
    
    def __init__(self):
        from core.goals import get_goal_store, GoalPriority
        self.goal_store = get_goal_store()
        self.GoalPriority = GoalPriority
        self._dispatch_log: List[Dict] = []
    
    def dispatch_signal(self, signal: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Dispatch a system signal to the appropriate role.
        
        Args:
            signal: Signal name (e.g., "bloat_detected", "performance_degradation")
            context: Additional context about the signal
            
        Returns:
            goal_id if a goal was created, None otherwise
        """
        context = context or {}
        
        # Find which role handles this signal
        target_role = None
        for role_name, role_def in ROLE_CAPABILITIES.items():
            if signal in role_def["triggers"]:
                target_role = role_name
                break
        
        if not target_role:
            return None
        
        role_def = ROLE_CAPABILITIES[target_role]
        
        # Build goal description from signal + context
        description = self._build_goal_description(signal, target_role, context)
        
        # Create goal assigned to the role's agent
        goal_id = self.goal_store.create_goal(
            description=description,
            source=f"role_dispatch:{target_role}",
            priority=self.GoalPriority.from_source("system"),
            assigned_agent=role_def["assigned_agent"],
            metadata={
                "signal": signal,
                "role": target_role,
                "context": context,
                "dispatched_at": datetime.utcnow().isoformat(),
                "available_actions": list(role_def["actions"].keys()),
                "can_self_modify": role_def["can_self_modify"],
            },
        )
        
        self._dispatch_log.append({
            "time": datetime.utcnow().isoformat(),
            "signal": signal,
            "role": target_role,
            "goal_id": goal_id,
            "agent": role_def["assigned_agent"],
        })
        
        # Keep log bounded
        if len(self._dispatch_log) > 100:
            self._dispatch_log = self._dispatch_log[-50:]
        
        return goal_id
    
    def execute_role_action(self, role: str, action_name: str, **kwargs) -> Any:
        """Execute a specific action for a role.
        
        This allows agents to call role-specific actions directly.
        E.g., the janitor can call cleanup() without going through a full goal cycle.
        """
        if role not in ROLE_CAPABILITIES:
            return {"error": f"Unknown role: {role}"}
        
        role_def = ROLE_CAPABILITIES[role]
        if action_name not in role_def["actions"]:
            return {"error": f"Unknown action '{action_name}' for role '{role}'"}
        
        # Import and call the action
        module_path = role_def["actions"][action_name]
        try:
            parts = module_path.rsplit(".", 1)
            module_name, func_name = parts[0], parts[1]
            import importlib
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            return func(**kwargs)
        except Exception as e:
            return {"error": f"Action failed: {str(e)}"}
    
    def get_role_for_signal(self, signal: str) -> Optional[str]:
        """Get which role handles a given signal."""
        for role_name, role_def in ROLE_CAPABILITIES.items():
            if signal in role_def["triggers"]:
                return role_name
        return None
    
    def get_dispatch_log(self) -> List[Dict]:
        """Get recent dispatch history."""
        return self._dispatch_log[-20:]
    
    def get_available_signals(self) -> Dict[str, str]:
        """Get all registered signals and their handling roles."""
        signals = {}
        for role_name, role_def in ROLE_CAPABILITIES.items():
            for trigger in role_def["triggers"]:
                signals[trigger] = role_name
        return signals
    
    def spawn_agent(self, agent_name: str, role: str, system_prompt: str,
                    capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Dynamically create a new agent with its own config and loop.
        
        The council can spawn specialist agents to handle specific work.
        The new agent gets:
        - A config file in agent_configs/
        - Registration in the role dispatcher
        - Its own AutonomousAgentLoop instance
        
        Args:
            agent_name: Unique name for the new agent (e.g., "performance_tuner")
            role: Role category (janitor, architect, security, or new custom role)
            system_prompt: The agent's system prompt defining its behavior
            capabilities: List of tool names this agent is allowed to use
            
        Returns:
            Dict with success status and agent details.
        """
        from core.agent_config import get_config_store
        import os
        
        config_store = get_config_store()
        capabilities = capabilities or ["editor", "shell_exec", "search_tools"]
        
        # Create agent config
        config = {
            "agent_name": agent_name,
            "version": "v1.0.0",
            "system_prompt": system_prompt,
            "allowed_tools": capabilities,
            "temperature": 0.2,
            "role": role,
            "spawned_at": datetime.utcnow().isoformat(),
            "spawned_by": "council",
        }
        
        # Save config
        config_dir = Path("agent_configs") / agent_name
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "active.json"
        config_path.write_text(json.dumps(config, indent=2))
        
        # Register the role if it's new
        if role not in ROLE_CAPABILITIES:
            ROLE_CAPABILITIES[role] = {
                "description": f"Dynamically spawned role: {role}",
                "triggers": [],
                "actions": {},
                "can_self_modify": True,
                "assigned_agent": agent_name,
            }
        
        # Create agent source file if it doesn't exist
        agent_file = Path("agents") / f"{agent_name}.py"
        if not agent_file.exists():
            agent_code = f'''"""Dynamically spawned agent: {agent_name}
Role: {role}
Spawned by council at {datetime.utcnow().isoformat()}
"""

import os
from typing import Dict, Any

def {agent_name}_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process state for {agent_name} agent."""
    # This agent was dynamically spawned by the council
    # It can self-modify this file to add new capabilities
    return state
'''
            agent_file.write_text(agent_code)
        
        return {
            "success": True,
            "agent_name": agent_name,
            "role": role,
            "config_path": str(config_path),
            "agent_file": str(agent_file),
            "capabilities": capabilities,
        }
    
    def list_spawned_agents(self) -> List[Dict[str, Any]]:
        """List all dynamically spawned agents."""
        spawned = []
        config_dir = Path("agent_configs")
        if not config_dir.exists():
            return spawned
        
        for agent_dir in config_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            active_config = agent_dir / "active.json"
            if active_config.exists():
                try:
                    config = json.loads(active_config.read_text())
                    if config.get("spawned_by") == "council":
                        spawned.append({
                            "agent_name": config.get("agent_name"),
                            "role": config.get("role"),
                            "spawned_at": config.get("spawned_at"),
                            "capabilities": config.get("allowed_tools", []),
                        })
                except (json.JSONDecodeError, OSError):
                    pass
        
        return spawned
    
    def _build_goal_description(self, signal: str, role: str, context: Dict) -> str:
        """Build a human-readable goal description from a signal."""
        templates = {
            "bloat_detected": "JANITOR: Clean up repository bloat. {detail}",
            "stale_files": "JANITOR: Remove {count} stale files older than retention period.",
            "disk_pressure": "JANITOR: Disk usage critical. Free space by purging old data.",
            "duplicate_tools": "JANITOR: Consolidate duplicate tools identified by quality audit. Duplicates: {duplicates}",
            "architecture_concern": "ARCHITECT: Review and resolve architecture issue: {issue}",
            "performance_degradation": "ARCHITECT: Performance declining (success_rate={success_rate}). Investigate and propose fixes.",
            "tool_overlap": "ARCHITECT: Tool registry has overlapping tools. Consolidate or deprecate.",
            "design_review": "ARCHITECT: Conduct periodic design review. Focus: {focus}",
            "security_alert": "SECURITY: Investigate security alert: {alert}",
            "secret_exposed": "SECURITY: Potential secret exposure detected. Rotate credentials.",
            "dependency_vuln": "SECURITY: Vulnerable dependency found: {package}",
        }
        
        template = templates.get(signal, f"{role.upper()}: Handle signal '{signal}'")
        try:
            return template.format(**context) if context else template
        except KeyError:
            return f"{role.upper()}: Handle signal '{signal}'. Context: {json.dumps(context)}"


# Singleton
_dispatcher: Optional[RoleDispatcher] = None


def get_role_dispatcher() -> RoleDispatcher:
    """Get or create the singleton RoleDispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = RoleDispatcher()
    return _dispatcher


def dispatch_system_signal(signal: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Convenience function to dispatch a signal without importing the class."""
    return get_role_dispatcher().dispatch_signal(signal, context)
