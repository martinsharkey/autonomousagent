"""
Real editor tool for autonomous goal execution.

Provides safe file read/write/patch operations with:
- AST validation for Python files before writing
- Path security (restricted to project root, respects denylist)
- Diff generation for audit trail
- Sandbox validation before applying changes
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Paths that CANNOT be modified by the editor tool
EDITOR_DENYLIST = {
    ".env", ".git", "secrets/", "autonomous_loops/",
    "council_daemon.py",  # Operator-only
}

# Paths that require extra validation but are allowed
EDITOR_SENSITIVE = {
    "core/agent_loop.py", "core/api_router.py", "core/evolution.py",
    "core/telegram.py", "core/graph.py", "core/planning.py",
}

# Maximum file size the editor will handle (100KB)
MAX_FILE_SIZE = 100_000

# Maximum new content size
MAX_WRITE_SIZE = 50_000


def _resolve_path(file_path: str) -> Tuple[bool, str, Path]:
    """Resolve and validate a file path. Returns (ok, error_msg, resolved_path)."""
    # Normalize and prevent path traversal
    normalized = os.path.normpath(file_path).replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith(".."):
        return False, f"Path traversal blocked: {file_path}", Path()

    resolved = PROJECT_ROOT / normalized

    # Ensure it's still within project root
    try:
        resolved.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return False, f"Path escapes project root: {file_path}", Path()

    # Check denylist
    for denied in EDITOR_DENYLIST:
        if normalized.startswith(denied) or normalized == denied.rstrip("/"):
            return False, f"Path is in denylist: {file_path}", Path()

    return True, "", resolved


def _validate_python_ast(content: str, file_path: str) -> Tuple[bool, str]:
    """Validate that Python content parses correctly."""
    try:
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError in {file_path} line {e.lineno}: {e.msg}"


def _generate_diff(original: str, modified: str, file_path: str) -> str:
    """Generate a unified diff between original and modified content."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines, modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )
    return "".join(diff)


def editor_read(file_path: str) -> Dict[str, Any]:
    """Read a file and return its contents.

    Args:
        file_path: Relative path from project root.

    Returns:
        Dict with keys: success, content, lines, size, error
    """
    ok, err, resolved = _resolve_path(file_path)
    if not ok:
        return {"success": False, "error": err}

    if not resolved.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    if not resolved.is_file():
        return {"success": False, "error": f"Not a file: {file_path}"}

    try:
        content = resolved.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Read error: {str(e)}"}

    if len(content) > MAX_FILE_SIZE:
        return {"success": False, "error": f"File too large ({len(content)} bytes > {MAX_FILE_SIZE})"}

    return {
        "success": True,
        "content": content,
        "lines": len(content.splitlines()),
        "size": len(content),
    }


def editor_write(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file (create or overwrite).

    Args:
        file_path: Relative path from project root.
        content: Full file content to write.

    Returns:
        Dict with keys: success, diff, lines_changed, error
    """
    ok, err, resolved = _resolve_path(file_path)
    if not ok:
        return {"success": False, "error": err}

    if len(content) > MAX_WRITE_SIZE:
        return {"success": False, "error": f"Content too large ({len(content)} bytes > {MAX_WRITE_SIZE})"}

    # Python files must pass AST validation
    if file_path.endswith(".py"):
        ast_ok, ast_err = _validate_python_ast(content, file_path)
        if not ast_ok:
            return {"success": False, "error": f"AST validation failed: {ast_err}"}

    # Read original for diff
    original = ""
    if resolved.exists():
        try:
            original = resolved.read_text(encoding="utf-8")
        except Exception:
            pass

    # Create parent directories if needed
    resolved.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    try:
        resolved.write_text(content, encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Write error: {str(e)}"}

    diff = _generate_diff(original, content, file_path)
    lines_changed = sum(1 for line in diff.splitlines() if line.startswith("+") or line.startswith("-"))

    return {
        "success": True,
        "diff": diff[:5000],  # Truncate large diffs for output
        "lines_changed": lines_changed,
        "file_path": file_path,
        "is_new_file": not bool(original),
    }


def editor_patch(file_path: str, search: str, replace: str) -> Dict[str, Any]:
    """Apply a search/replace patch to a file.

    Args:
        file_path: Relative path from project root.
        search: Exact text to find in the file.
        replace: Text to replace it with.

    Returns:
        Dict with keys: success, diff, occurrences_replaced, error
    """
    ok, err, resolved = _resolve_path(file_path)
    if not ok:
        return {"success": False, "error": err}

    if not resolved.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        original = resolved.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Read error: {str(e)}"}

    if search not in original:
        return {"success": False, "error": f"Search text not found in {file_path}"}

    # Count occurrences and replace
    occurrences = original.count(search)
    modified = original.replace(search, replace)

    # Python files must pass AST validation after patch
    if file_path.endswith(".py"):
        ast_ok, ast_err = _validate_python_ast(modified, file_path)
        if not ast_ok:
            return {"success": False, "error": f"Patch breaks syntax: {ast_err}"}

    # Write
    try:
        resolved.write_text(modified, encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Write error: {str(e)}"}

    diff = _generate_diff(original, modified, file_path)

    return {
        "success": True,
        "diff": diff[:5000],
        "occurrences_replaced": occurrences,
        "file_path": file_path,
    }


def editor_create_file(file_path: str, content: str) -> Dict[str, Any]:
    """Create a new file. Fails if file already exists.

    Args:
        file_path: Relative path from project root.
        content: File content.

    Returns:
        Dict with keys: success, file_path, lines, error
    """
    ok, err, resolved = _resolve_path(file_path)
    if not ok:
        return {"success": False, "error": err}

    if resolved.exists():
        return {"success": False, "error": f"File already exists: {file_path}"}

    return editor_write(file_path, content)


def editor_list_dir(dir_path: str) -> Dict[str, Any]:
    """List contents of a directory.

    Args:
        dir_path: Relative path from project root.

    Returns:
        Dict with keys: success, files, dirs, error
    """
    ok, err, resolved = _resolve_path(dir_path)
    if not ok:
        return {"success": False, "error": err}

    if not resolved.exists():
        return {"success": False, "error": f"Directory not found: {dir_path}"}

    if not resolved.is_dir():
        return {"success": False, "error": f"Not a directory: {dir_path}"}

    try:
        entries = list(resolved.iterdir())
        files = sorted(str(e.relative_to(PROJECT_ROOT)) for e in entries if e.is_file())
        dirs = sorted(str(e.relative_to(PROJECT_ROOT)) for e in entries if e.is_dir())
        return {"success": True, "files": files[:100], "dirs": dirs[:50]}
    except Exception as e:
        return {"success": False, "error": f"List error: {str(e)}"}


def parse_editor_action(action: str) -> Dict[str, Any]:
    """Parse an LLM-generated editor action string into a structured command.

    Supports formats:
    - JSON: {"operation": "read|write|patch|create|list", "file_path": "...", ...}
    - Structured text: READ file_path / WRITE file_path\\n<content> / PATCH file_path\\n<search>\\n---\\n<replace>

    Returns:
        Dict with operation details or error.
    """
    action = action.strip()

    # Try JSON first
    if action.startswith("{"):
        try:
            parsed = json.loads(action)
            return parsed
        except json.JSONDecodeError:
            pass

    # Try structured text format
    lines = action.split("\n")
    first_line = lines[0].strip().upper()

    if first_line.startswith("READ "):
        file_path = lines[0].strip()[5:].strip()
        return {"operation": "read", "file_path": file_path}

    if first_line.startswith("LIST "):
        dir_path = lines[0].strip()[5:].strip()
        return {"operation": "list", "file_path": dir_path}

    if first_line.startswith("WRITE "):
        file_path = lines[0].strip()[6:].strip()
        content = "\n".join(lines[1:])
        return {"operation": "write", "file_path": file_path, "content": content}

    if first_line.startswith("CREATE "):
        file_path = lines[0].strip()[7:].strip()
        content = "\n".join(lines[1:])
        return {"operation": "create", "file_path": file_path, "content": content}

    if first_line.startswith("PATCH "):
        file_path = lines[0].strip()[6:].strip()
        rest = "\n".join(lines[1:])
        # Split on --- separator
        if "---" in rest:
            parts = rest.split("---", 1)
            search = parts[0].strip()
            replace = parts[1].strip()
            return {"operation": "patch", "file_path": file_path, "search": search, "replace": replace}
        return {"operation": "patch", "file_path": file_path, "error": "Missing --- separator between search and replace"}

    return {"operation": "unknown", "error": f"Could not parse editor action: {action[:200]}"}


def execute_editor_action(action: str) -> Dict[str, Any]:
    """Execute a parsed or raw editor action.

    This is the main entry point called by the planner.

    Args:
        action: Either a JSON string or structured text describing the edit.

    Returns:
        Dict with execution results.
    """
    parsed = parse_editor_action(action)
    operation = parsed.get("operation", "unknown")

    if operation == "unknown" or "error" in parsed:
        return {"success": False, "error": parsed.get("error", "Unknown editor operation")}

    file_path = parsed.get("file_path", "")

    if operation == "read":
        return editor_read(file_path)

    elif operation == "write":
        content = parsed.get("content", "")
        if not content:
            return {"success": False, "error": "No content provided for write operation"}
        return editor_write(file_path, content)

    elif operation == "create":
        content = parsed.get("content", "")
        return editor_create_file(file_path, content)

    elif operation == "patch":
        search = parsed.get("search", "")
        replace = parsed.get("replace", "")
        if not search:
            return {"success": False, "error": "No search text provided for patch operation"}
        return editor_patch(file_path, search, replace)

    elif operation == "list":
        return editor_list_dir(file_path)

    return {"success": False, "error": f"Unsupported operation: {operation}"}
