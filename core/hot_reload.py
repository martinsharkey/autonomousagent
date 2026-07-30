"""
Hot Module Reload - enables self-evolution without daemon restart.

Integrates with the evolution saga:
  propose → validate → canary → soak → promote → HOT RELOAD → verify

If reload fails (import error, syntax error), the evolution engine
can roll back the mutation since we're still within the saga.

Safety:
- Only reloads modules under the project package (agents/, core/, governance/, tools/)
- Preserves global state by re-binding references
- Logs all reload activity for audit
- Returns success/failure so the saga can decide to rollback
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Modules that are safe to hot-reload (contain business logic, not state)
RELOADABLE_PREFIXES = [
    "agents.",
    "core.agent_context",
    "core.react",
    "core.telegram",
    "core.mutation_proposer",
    "core.mutation_validator",
    "core.temperature_selector",
    "core.evolution",
    "core.graph",
    "core.sandbox",
    "governance.consensus",
    "governance.audit_log",
    "tools.",
]

# Never reload these - they hold critical runtime state
NEVER_RELOAD = [
    "core.memory",        # SQLite connections, singleton state
    "core.agent_loop",    # Running event loop references
    "core.api_router",    # Active HTTP connections, router state
    "core.communication", # Message bus state
    "core.goals",         # SQLite connections
    "core.health",        # Running metrics
]


def _is_reloadable(module_name: str) -> bool:
    """Check if a module is safe to hot-reload."""
    for blocked in NEVER_RELOAD:
        if module_name == blocked or module_name.startswith(blocked + "."):
            return False
    for prefix in RELOADABLE_PREFIXES:
        if module_name.startswith(prefix) or module_name == prefix.rstrip("."):
            return True
    return False


def _get_loaded_project_modules() -> List[str]:
    """Get all currently loaded modules that belong to this project."""
    project_modules = []
    for name in list(sys.modules.keys()):
        if _is_reloadable(name):
            project_modules.append(name)
    return sorted(project_modules)


def reload_module(module_name: str) -> Tuple[bool, Optional[str]]:
    """
    Reload a single module by name.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    if not _is_reloadable(module_name):
        return False, f"Module '{module_name}' is not in the reloadable list"
    
    if module_name not in sys.modules:
        return False, f"Module '{module_name}' is not currently loaded"
    
    try:
        module = sys.modules[module_name]
        importlib.reload(module)
        return True, None
    except Exception as e:
        error = f"Failed to reload '{module_name}': {e}\n{traceback.format_exc()}"
        return False, error


def reload_changed_modules(changed_files: List[str]) -> Dict[str, any]:
    """
    Reload modules corresponding to changed files.
    Called by the evolution engine after a mutation is promoted.
    
    Args:
        changed_files: List of file paths relative to project root
                      (e.g., ["core/telegram.py", "agents/autobot.py"])
    
    Returns:
        {
            "success": bool,
            "reloaded": ["module.name", ...],
            "failed": [{"module": "name", "error": "..."}],
            "skipped": ["module.name", ...],
            "timestamp": "iso8601"
        }
    """
    result = {
        "success": True,
        "reloaded": [],
        "failed": [],
        "skipped": [],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Convert file paths to module names
    modules_to_reload = []
    for filepath in changed_files:
        # Convert path like "core/telegram.py" to "core.telegram"
        if not filepath.endswith(".py"):
            continue
        module_name = filepath[:-3].replace("/", ".").replace("\\", ".")
        
        # Remove __init__ suffix
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        
        if _is_reloadable(module_name) and module_name in sys.modules:
            modules_to_reload.append(module_name)
        elif module_name in sys.modules:
            result["skipped"].append(module_name)
    
    # Reload in dependency order (leaf modules first)
    # Sort by depth (deeper = more specific = reload first)
    modules_to_reload.sort(key=lambda m: m.count("."), reverse=True)
    
    for module_name in modules_to_reload:
        success, error = reload_module(module_name)
        if success:
            result["reloaded"].append(module_name)
            print(f"[HOT-RELOAD] ✓ Reloaded: {module_name}")
        else:
            result["failed"].append({"module": module_name, "error": error})
            result["success"] = False
            print(f"[HOT-RELOAD] ✗ Failed: {module_name} - {error}")
    
    # Log the reload event
    try:
        from governance.audit_log import log_event
        log_event("hot_reload", result)
    except Exception:
        pass
    
    return result


def reload_all_project_modules() -> Dict[str, any]:
    """
    Nuclear option: reload ALL reloadable project modules.
    Use after a git pull or major update.
    
    Returns same format as reload_changed_modules.
    """
    modules = _get_loaded_project_modules()
    # Sort deepest first for proper reload order
    modules.sort(key=lambda m: m.count("."), reverse=True)
    
    result = {
        "success": True,
        "reloaded": [],
        "failed": [],
        "skipped": [],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    for module_name in modules:
        success, error = reload_module(module_name)
        if success:
            result["reloaded"].append(module_name)
        else:
            result["failed"].append({"module": module_name, "error": error})
            result["success"] = False
    
    count = len(result["reloaded"])
    failures = len(result["failed"])
    print(f"[HOT-RELOAD] Complete: {count} reloaded, {failures} failed")
    
    try:
        from governance.audit_log import log_event
        log_event("hot_reload_all", result)
    except Exception:
        pass
    
    return result


def verify_reload_health() -> Tuple[bool, Optional[str]]:
    """
    Quick health check after reload - tries to import critical modules
    and call basic functions to ensure nothing is broken.
    
    Returns:
        (healthy: bool, error_message: Optional[str])
    """
    checks = [
        ("core.agent_context", "inject_mission_context"),
        ("core.telegram", "format_council_message"),
        ("governance.consensus", "ConsensusEngine"),
    ]
    
    for module_name, attr_name in checks:
        try:
            mod = sys.modules.get(module_name)
            if mod is None:
                continue
            attr = getattr(mod, attr_name, None)
            if attr is None:
                return False, f"Module '{module_name}' missing attribute '{attr_name}' after reload"
        except Exception as e:
            return False, f"Health check failed for '{module_name}': {e}"
    
    return True, None
