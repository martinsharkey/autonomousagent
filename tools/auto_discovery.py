"""Auto-discovery and registration of tools created by the council daemon.

Scans tools/ directory for @tool-decorated functions, validates them with
the code_validator security gate, and registers safe ones into MCP_REGISTRY.

This closes the loop: council creates tools → auto_discovery loads them →
planning.py can execute them → the council can USE what it creates.

Quality gates:
- Security validation (no subprocess, eval, pickle, etc.)
- Deduplication check (skip tools whose name/purpose overlaps existing ones)
- Import validation (file must parse without syntax errors)
- Size limit (50KB max to prevent loading generated junk)

The repo_janitor should periodically call audit_tool_quality() to identify
tools that are never invoked and can be pruned.
"""

import ast
import importlib
import importlib.util
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# These are the "core" tools that are manually registered in mcp_registry.py
# and should NOT be auto-discovered (to avoid double-registration)
CORE_TOOLS = {
    "mcp_registry.py",
    "mcp_server.py",
    "code_validator.py",
    "auto_discovery.py",
    "__init__.py",
}

# Files that are known to be utility/support modules (not tool providers)
SKIP_FILES = CORE_TOOLS | {
    "example.py",
    "example_tool.py",
}

# Maximum file size to scan (prevent loading massive generated files)
MAX_TOOL_FILE_SIZE = 50_000  # 50KB

_discovery_log: List[Dict] = []
_last_scan_time: float = 0.0
_scan_interval: float = 300.0  # Re-scan every 5 minutes


def _has_tool_decorator(filepath: Path) -> bool:
    """Quick AST check: does this file have any @tool decorated functions?"""
    try:
        source = filepath.read_text(encoding="utf-8")
        if len(source) > MAX_TOOL_FILE_SIZE:
            return False
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "tool":
                        return True
                    if isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                        return True
        return False
    except (SyntaxError, UnicodeDecodeError, OSError):
        return False


def _validate_tool_file(filepath: Path) -> Tuple[bool, str]:
    """Run security validation on a tool file before loading.
    
    Uses a RELAXED validator compared to code_validator — council-created
    tools may need json, pathlib, datetime imports which are safe.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, f"Cannot read file: {e}"

    if len(source) > MAX_TOOL_FILE_SIZE:
        return False, f"File too large ({len(source)} bytes)"

    # Parse AST to check for dangerous patterns
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Blocked: subprocess, os.system, eval, exec, __import__
    DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "execfile"}
    DANGEROUS_IMPORTS = {"ctypes", "pickle", "marshal", "shelve"}
    
    for node in ast.walk(tree):
        # Check for dangerous function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                return False, f"Dangerous call: {node.func.id}()"
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "exec", "execvp"):
                    return False, f"Dangerous call: .{node.func.attr}()"
                if node.func.attr in ("run", "call", "Popen", "check_output"):
                    # Check if it's subprocess.*
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                        return False, f"Dangerous call: subprocess.{node.func.attr}()"

        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in DANGEROUS_IMPORTS:
                    return False, f"Dangerous import: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in DANGEROUS_IMPORTS:
                return False, f"Dangerous import: from {node.module}"

    return True, "OK"


def _extract_tool_names(filepath: Path) -> List[str]:
    """Extract names of @tool-decorated functions from a file via AST."""
    names = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "tool":
                        names.append(node.name)
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                        names.append(node.name)
    except (SyntaxError, OSError):
        pass
    return names


def discover_and_register(force: bool = False) -> Dict[str, any]:
    """Scan tools/ directory and register any valid @tool-decorated functions.
    
    Args:
        force: If True, bypass the scan interval cooldown.
        
    Returns:
        Dict with registered, skipped, failed counts and details.
    """
    global _last_scan_time
    
    now = time.time()
    if not force and (now - _last_scan_time) < _scan_interval:
        return {"status": "skipped", "reason": "scan_interval_not_elapsed"}
    
    _last_scan_time = now
    
    from tools.mcp_registry import _tool_registry, _approved_tools
    
    tools_dir = Path(__file__).parent
    results = {
        "registered": [],
        "skipped": [],
        "failed": [],
        "already_loaded": [],
    }
    
    for filepath in sorted(tools_dir.glob("*.py")):
        if filepath.name in SKIP_FILES:
            continue
            
        # Skip if no @tool decorator
        if not _has_tool_decorator(filepath):
            results["skipped"].append({"file": filepath.name, "reason": "no_tool_decorator"})
            continue
        
        # Check which tool names are in this file
        tool_names = _extract_tool_names(filepath)
        if not tool_names:
            results["skipped"].append({"file": filepath.name, "reason": "no_tool_functions"})
            continue
            
        # Skip if ALL tools from this file are already registered
        all_registered = all(name in _tool_registry for name in tool_names)
        if all_registered:
            results["already_loaded"].append({"file": filepath.name, "tools": tool_names})
            continue
        
        # Validate security
        is_safe, reason = _validate_tool_file(filepath)
        if not is_safe:
            results["failed"].append({"file": filepath.name, "reason": reason})
            _log_event("validation_failed", filepath.name, reason)
            continue
        
        # Load the module
        module_name = f"tools.{filepath.stem}"
        try:
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                spec = importlib.util.spec_from_file_location(module_name, str(filepath))
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            
            # Register any @tool-decorated functions
            newly_registered = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, "name") and hasattr(attr, "invoke"):
                    # It's a langchain tool
                    if attr.name not in _tool_registry:
                        _tool_registry[attr.name] = attr
                        _approved_tools[attr.name] = str(filepath)
                        newly_registered.append(attr.name)
            
            if newly_registered:
                results["registered"].append({
                    "file": filepath.name,
                    "tools": newly_registered,
                })
                _log_event("registered", filepath.name, ", ".join(newly_registered))
            else:
                results["skipped"].append({"file": filepath.name, "reason": "no_new_tools"})
                
        except Exception as e:
            results["failed"].append({"file": filepath.name, "reason": str(e)})
            _log_event("load_failed", filepath.name, str(e))
            # Clean up failed module
            if module_name in sys.modules:
                del sys.modules[module_name]
    
    return results


def get_available_tool_names() -> List[str]:
    """Get all currently registered tool names (for LLM prompting)."""
    from tools.mcp_registry import _tool_registry
    return sorted(_tool_registry.keys())


def get_tool_descriptions() -> str:
    """Get formatted tool descriptions for injection into agent prompts."""
    from tools.mcp_registry import _tool_registry
    
    lines = []
    for name, tool_func in sorted(_tool_registry.items()):
        doc = ""
        if hasattr(tool_func, "description"):
            doc = tool_func.description
        elif hasattr(tool_func, "__doc__") and tool_func.__doc__:
            doc = tool_func.__doc__.strip().split("\n")[0]
        lines.append(f"  - {name}: {doc}")
    
    return "Available tools:\n" + "\n".join(lines)


def _log_event(event_type: str, filename: str, detail: str):
    """Log discovery events for debugging."""
    _discovery_log.append({
        "time": time.time(),
        "event": event_type,
        "file": filename,
        "detail": detail,
    })
    # Keep log bounded
    if len(_discovery_log) > 200:
        _discovery_log[:] = _discovery_log[-100:]


def get_discovery_log() -> List[Dict]:
    """Get recent discovery events."""
    return _discovery_log[-50:]


def audit_tool_quality() -> Dict[str, any]:
    """Audit tools for duplicates, unused tools, and quality issues.
    
    Called by repo_janitor to identify dead-weight tools that were
    created but never invoked or are redundant with existing tools.
    """
    from tools.mcp_registry import _tool_registry, _approved_tools
    
    issues = {
        "duplicate_purpose": [],
        "orphaned_files": [],
        "recommendations": [],
    }
    
    # Check for name-similarity duplicates
    tool_names = list(_tool_registry.keys())
    seen_stems = {}
    for name in tool_names:
        stem = name.replace("_", "").lower()
        if stem in seen_stems:
            issues["duplicate_purpose"].append({
                "tool_a": seen_stems[stem],
                "tool_b": name,
                "reason": "similar_name_stem",
            })
        else:
            seen_stems[stem] = name
    
    # Check for tools with very similar descriptions
    descriptions = {}
    for name, tool_func in _tool_registry.items():
        desc = ""
        if hasattr(tool_func, "description"):
            desc = tool_func.description[:80].lower()
        elif hasattr(tool_func, "__doc__") and tool_func.__doc__:
            desc = tool_func.__doc__[:80].lower()
        if desc:
            words = set(desc.split())
            for other_name, other_words in descriptions.items():
                if other_name == name:
                    continue
                overlap = words & other_words
                if len(overlap) > 5 and len(overlap) / max(len(words), len(other_words)) > 0.6:
                    issues["duplicate_purpose"].append({
                        "tool_a": other_name,
                        "tool_b": name,
                        "reason": "description_overlap",
                    })
            descriptions[name] = words
    
    # Check for orphaned files (have @tool but failed to load)
    tools_dir = Path(__file__).parent
    for filepath in tools_dir.glob("*.py"):
        if filepath.name in SKIP_FILES:
            continue
        if _has_tool_decorator(filepath):
            tool_names_in_file = _extract_tool_names(filepath)
            registered_from_file = [n for n in tool_names_in_file if n in _tool_registry]
            if not registered_from_file and tool_names_in_file:
                issues["orphaned_files"].append({
                    "file": filepath.name,
                    "tools": tool_names_in_file,
                })
    
    if issues["duplicate_purpose"]:
        issues["recommendations"].append(
            f"Consider consolidating {len(issues['duplicate_purpose'])} duplicate tool pairs"
        )
    if issues["orphaned_files"]:
        issues["recommendations"].append(
            f"{len(issues['orphaned_files'])} tool files failed to register — check imports"
        )
    
    return issues
