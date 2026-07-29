"""Mutation safety gates to prevent destructive auto-apply."""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

APPROVAL_REQUIRED = {
    "core/agent_loop.py",
    "core/api_router.py",
    "core/evolution.py",
    "core/telegram.py",
    "council_daemon.py",
    "core/state.py",
    "core/graph.py",
    "core/rollback.py",
    "core/snapshots.py",
    "core/checkpointer.py",
    "core/planning.py",
    "core/curiosity.py",
    "core/communication.py",
}

ALLOWLIST_NON_CRITICAL = [
    "tools/",
    "governance/",
    "microbots/",
    "tests/",
    "agents/",
    "core/",
    "providers.yaml",
    "README.md",
    "MISSION_PURPOSE.md",
    "MUTATIONS_ROADMAP.md",
    "TODO.md",
    "session_log.md",
]

DENYLIST_CRITICAL = [
    ".env",
    ".git",
    "secrets/",
    "autonomous_loops/",
]

MAX_REDUCTION_RATIO = 0.5


def _file_lines(path: str) -> int:
    try:
        return len(Path(path).read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


def _is_path_allowed(path: str) -> bool:
    if any(path.startswith(d) or path == d for d in DENYLIST_CRITICAL):
        return False
    return any(path == a or path.startswith(a) for a in ALLOWLIST_NON_CRITICAL)


def _is_approval_required(path: str) -> bool:
    return path in APPROVAL_REQUIRED


def _check_path_policy(changes: Dict[str, Any]) -> Tuple[bool, str, bool]:
    file_changes = changes.get("file_changes") or []
    if not isinstance(file_changes, list):
        return True, "", False

    approval_required = False
    for fc in file_changes:
        if not isinstance(fc, dict):
            continue
        path = fc.get("path", "")
        kind = fc.get("kind", "modify")
        if kind in ("modify", "replace", "delete"):
            if not _is_path_allowed(path):
                return False, f"Path {path} is not in the safe allowlist", False
            if _is_approval_required(path):
                approval_required = True
    return True, "", approval_required


def _check_file_size(changes: Dict[str, Any]) -> Tuple[bool, str]:
    file_changes = changes.get("file_changes") or []
    if not isinstance(file_changes, list):
        return True, ""

    for fc in file_changes:
        if not isinstance(fc, dict):
            continue
        path = fc.get("path", "")
        kind = fc.get("kind", "modify")
        content = fc.get("content", "")
        if not path.endswith(".py") or not content or kind == "delete":
            continue

        old_lines = _file_lines(path)
        if old_lines == 0:
            continue

        new_lines = len(content.splitlines())
        if old_lines > 0:
            reduction = (old_lines - new_lines) / old_lines
            if reduction > MAX_REDUCTION_RATIO:
                return (
                    False,
                    f"File {path} would shrink {reduction:.1%} ({old_lines} -> {new_lines} lines)",
                )
    return True, ""


def _check_syntax(changes: Dict[str, Any]) -> Tuple[bool, str]:
    file_changes = changes.get("file_changes") or []
    if not isinstance(file_changes, list):
        return True, ""

    for fc in file_changes:
        if not isinstance(fc, dict):
            continue
        path = fc.get("path", "")
        kind = fc.get("kind", "modify")
        content = fc.get("content", "")
        if not path.endswith(".py") or not content or kind == "delete":
            continue

        try:
            ast.parse(content)
        except SyntaxError as e:
            return False, f"Syntax error in {path}: {e}"
    return True, ""


def _check_imports(changes: Dict[str, Any]) -> Tuple[bool, str]:
    file_changes = changes.get("file_changes") or []
    if not isinstance(file_changes, list):
        return True, ""

    for fc in file_changes:
        if not isinstance(fc, dict):
            continue
        path = fc.get("path", "")
        kind = fc.get("kind", "modify")
        content = fc.get("content", "")
        if not path.endswith(".py") or not content or kind == "delete":
            continue

        module_name = Path(path).stem
        if not module_name:
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / Path(path).name
            tmp_path.write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"import importlib.util; spec = importlib.util.spec_from_file_location('{module_name}', r'{tmp_path}'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if not stderr:
                    stderr = result.stdout.strip()
                return False, f"Import error in {path}: {stderr}"

    return True, ""


def check_mutation_safety(mutation: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (is_safe, reason)."""
    changes = mutation.get("proposed_changes") or {}

    if not isinstance(changes, dict):
        return True, ""

    is_safe, reason, approval_required = _check_path_policy(changes)
    if not is_safe:
        return False, reason

    is_safe, reason = _check_file_size(changes)
    if not is_safe:
        return False, reason

    is_safe, reason = _check_syntax(changes)
    if not is_safe:
        return False, reason

    is_safe, reason = _check_imports(changes)
    if not is_safe:
        return False, reason

    if approval_required:
        return True, "Mutation passes safety checks but requires human approval for critical file"

    return True, "Mutation passes safety checks"
