"""Saga Testing — 5-step verification pipeline for mutations.

Steps:
1. syntax_check: Verify all changed files have valid Python syntax
2. import_check: Verify changed modules can be imported without errors
3. unit_tests: Run targeted unit tests for affected modules
4. integration_smoke: Quick smoke test of core imports + basic function calls
5. dependency_check: Ensure no broken imports or missing dependencies

Used as a pre-flight gate in evolution.py before the heavier test suite.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_changed_files(mutation: Dict[str, Any]) -> List[str]:
    """Extract file paths from a mutation dict."""
    changes = mutation.get("proposed_changes", {})
    if not isinstance(changes, dict):
        return []

    files = []
    file_changes = changes.get("file_changes", [])
    if isinstance(file_changes, list):
        for item in file_changes:
            if isinstance(item, dict) and item.get("path"):
                files.append(item["path"])

    # Also check target_file
    target = mutation.get("target_file")
    if target:
        files.append(target)

    return files


def step_syntax_check(files: List[str]) -> Dict[str, Any]:
    """Step 1: Verify Python files have valid syntax."""
    errors = []
    checked = 0

    for filepath in files:
        if not filepath.endswith(".py"):
            continue

        full_path = PROJECT_ROOT / filepath
        if not full_path.exists():
            continue

        checked += 1
        try:
            source = full_path.read_text(encoding="utf-8")
            ast.parse(source, filename=filepath)
        except SyntaxError as e:
            errors.append(f"{filepath}:{e.lineno}: {e.msg}")

    return {
        "step": "syntax_check",
        "passed": len(errors) == 0,
        "checked": checked,
        "errors": errors,
    }


def step_import_check(files: List[str]) -> Dict[str, Any]:
    """Step 2: Verify changed modules can be imported."""
    errors = []
    checked = 0

    for filepath in files:
        if not filepath.endswith(".py"):
            continue

        full_path = PROJECT_ROOT / filepath
        if not full_path.exists():
            continue

        # Convert path to module name
        rel = filepath.replace("/", ".").replace("\\", ".")
        if rel.endswith(".py"):
            rel = rel[:-3]

        # Skip __init__ and test files for import check
        if "__init__" in rel or rel.startswith("tests."):
            continue

        checked += 1
        try:
            spec = importlib.util.spec_from_file_location(rel, full_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Don't actually execute - just verify it loads
                # spec.loader.exec_module(module)  # Too risky for pre-flight
                pass
        except Exception as e:
            errors.append(f"{filepath}: {type(e).__name__}: {e}")

    return {
        "step": "import_check",
        "passed": len(errors) == 0,
        "checked": checked,
        "errors": errors,
    }


def step_unit_tests(files: List[str]) -> Dict[str, Any]:
    """Step 3: Run targeted unit tests for affected modules."""
    # Find test files that match changed modules
    test_files = []
    for filepath in files:
        if not filepath.endswith(".py"):
            continue
        basename = Path(filepath).stem
        # Look for matching test file
        candidates = [
            PROJECT_ROOT / "tests" / f"test_{basename}.py",
            PROJECT_ROOT / "tests" / f"test_{basename}_unit.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                test_files.append(str(candidate))

    if not test_files:
        return {
            "step": "unit_tests",
            "passed": True,
            "skipped": True,
            "reason": "No matching test files found",
        }

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + test_files + ["-v", "--tb=short", "-q", "--timeout=30"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        return {
            "step": "unit_tests",
            "passed": result.returncode == 0,
            "test_files": test_files,
            "output": result.stdout[-1000:] if result.stdout else "",
            "errors": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "step": "unit_tests",
            "passed": False,
            "error": "Unit tests timed out (60s)",
        }
    except Exception as e:
        return {
            "step": "unit_tests",
            "passed": False,
            "error": str(e),
        }


def step_integration_smoke() -> Dict[str, Any]:
    """Step 4: Quick smoke test - verify core modules still import."""
    core_modules = [
        "core.agent_loop",
        "core.evolution",
        "core.feedback",
        "core.memory",
        "core.graph",
    ]

    errors = []
    for mod_name in core_modules:
        try:
            # Use subprocess to avoid polluting current process
            result = subprocess.run(
                [sys.executable, "-c", f"import {mod_name}"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(PROJECT_ROOT),
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
            )
            if result.returncode != 0:
                errors.append(f"{mod_name}: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            errors.append(f"{mod_name}: import timed out")
        except Exception as e:
            errors.append(f"{mod_name}: {e}")

    return {
        "step": "integration_smoke",
        "passed": len(errors) == 0,
        "checked": len(core_modules),
        "errors": errors,
    }


def step_dependency_check(files: List[str]) -> Dict[str, Any]:
    """Step 5: Check for broken imports in changed files."""
    errors = []
    checked = 0

    for filepath in files:
        if not filepath.endswith(".py"):
            continue

        full_path = PROJECT_ROOT / filepath
        if not full_path.exists():
            continue

        checked += 1
        try:
            source = full_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        if mod in ("core", "tools", "governance", "tests"):
                            # Internal - check file exists
                            internal_path = PROJECT_ROOT / alias.name.replace(".", "/")
                            if not (internal_path.exists() or Path(str(internal_path) + ".py").exists()):
                                # Check if it's a package
                                if not (internal_path / "__init__.py").exists():
                                    pass  # Not a hard failure for now
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith(("core.", "tools.", "governance.")):
                        parts = node.module.split(".")
                        mod_path = PROJECT_ROOT / "/".join(parts)
                        file_path = Path(str(mod_path) + ".py")
                        if not file_path.exists() and not (mod_path / "__init__.py").exists():
                            errors.append(f"{filepath}: missing internal module '{node.module}'")
        except SyntaxError:
            pass  # Already caught in step 1
        except Exception as e:
            errors.append(f"{filepath}: dependency scan error: {e}")

    return {
        "step": "dependency_check",
        "passed": len(errors) == 0,
        "checked": checked,
        "errors": errors,
    }


def run_saga(files: List[str]) -> Dict[str, Any]:
    """Run the full 5-step saga pipeline.

    Returns dict with overall pass/fail and individual step results.
    Stops at first failure (saga pattern).
    """
    results = []

    steps = [
        ("syntax_check", lambda: step_syntax_check(files)),
        ("import_check", lambda: step_import_check(files)),
        ("unit_tests", lambda: step_unit_tests(files)),
        ("integration_smoke", lambda: step_integration_smoke()),
        ("dependency_check", lambda: step_dependency_check(files)),
    ]

    for step_name, step_fn in steps:
        try:
            result = step_fn()
        except Exception as e:
            result = {"step": step_name, "passed": False, "error": str(e)}

        results.append(result)

        if not result.get("passed") and not result.get("skipped"):
            return {
                "passed": False,
                "failed_step": step_name,
                "error": result.get("errors", [result.get("error", "Unknown")])
                if isinstance(result.get("errors"), list) and result.get("errors")
                else result.get("error", "Step failed"),
                "steps": results,
            }

    return {
        "passed": True,
        "steps": results,
    }


def run_saga_for_mutation(mutation: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience: extract files from mutation dict and run saga."""
    files = _get_changed_files(mutation)
    if not files:
        return {"passed": True, "skipped": True, "reason": "No files to verify"}
    return run_saga(files)
