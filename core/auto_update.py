"""
Auto-update with blue/green deployment model.

This integrates into the mutation lifecycle:
1. After a mutation is promoted to main → auto_update triggers
2. Blue/green: the "green" version is validated before switching
3. If validation fails → rollback to "blue" (previous commit)
4. If validation passes → daemon restarts on green

The council is AWARE of updates because they flow through the
evolution pipeline (propose → vote → promote → update → restart).

Also supports periodic pull for external changes (e.g., human pushes).
"""

from __future__ import annotations

import asyncio
import os
import sys
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPDATE_LOG_FILE = PROJECT_ROOT / "evolution" / "update_log.json"
RESTART_MARKER = PROJECT_ROOT / "evolution" / "restart_marker.json"
LOCK_FILE = Path("/tmp/autonomousagent_update.lock")
BLUE_GREEN_STATE_FILE = PROJECT_ROOT / "evolution" / "blue_green_state.json"


# ─── Git Operations ────────────────────────────────────────────────────────────

def _run_git(cmd: list) -> Tuple[bool, str, str]:
    """Run a git command in project root."""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Git command timed out"
    except Exception as e:
        return False, "", str(e)


def get_current_commit() -> str:
    success, stdout, _ = _run_git(["rev-parse", "--short", "HEAD"])
    return stdout if success else "unknown"


def get_current_commit_full() -> str:
    success, stdout, _ = _run_git(["rev-parse", "HEAD"])
    return stdout if success else "unknown"


# ─── Blue/Green State ──────────────────────────────────────────────────────────

class BlueGreenState:
    """Track which deployment slot is active and what's pending."""

    def __init__(self):
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if BLUE_GREEN_STATE_FILE.exists():
                return json.loads(BLUE_GREEN_STATE_FILE.read_text())
        except Exception:
            pass
        return {
            "active_slot": "blue",
            "blue_commit": get_current_commit_full(),
            "green_commit": None,
            "last_switch": None,
            "history": [],
        }

    def _save(self):
        try:
            BLUE_GREEN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            BLUE_GREEN_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    @property
    def active_commit(self) -> str:
        slot = self.state["active_slot"]
        return self.state.get(f"{slot}_commit", "unknown")

    def prepare_green(self, new_commit: str):
        """Stage green slot with a new commit (pre-validation)."""
        self.state["green_commit"] = new_commit
        self._save()

    def switch_to_green(self):
        """Promote green to active after validation passes."""
        self.state["active_slot"] = "green"
        self.state["last_switch"] = datetime.utcnow().isoformat()
        self.state["history"].append({
            "action": "switch_to_green",
            "commit": self.state["green_commit"],
            "timestamp": self.state["last_switch"],
        })
        # Keep history manageable
        self.state["history"] = self.state["history"][-20:]
        self._save()

    def rollback_to_blue(self, reason: str):
        """Rollback to blue if green fails validation."""
        self.state["active_slot"] = "blue"
        self.state["green_commit"] = None
        self.state["history"].append({
            "action": "rollback_to_blue",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.state["history"] = self.state["history"][-20:]
        self._save()

    def finalize_green(self):
        """After green is stable, it becomes the new blue baseline."""
        self.state["blue_commit"] = self.state["green_commit"]
        self.state["green_commit"] = None
        self.state["active_slot"] = "blue"
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return self.state.copy()


# ─── Validation ────────────────────────────────────────────────────────────────

def validate_green_deployment(changed_files: list) -> Tuple[bool, str]:
    """
    Validate the green deployment before switching.
    
    Checks:
    1. Python syntax of all changed .py files
    2. Core imports work
    3. Health check passes
    """
    import ast

    # Check syntax of changed files
    for filepath in changed_files:
        if filepath.endswith(".py"):
            full_path = PROJECT_ROOT / filepath
            if full_path.exists():
                try:
                    ast.parse(full_path.read_text())
                except SyntaxError as e:
                    return False, f"Syntax error in {filepath}: {e}"

    # Check core imports
    try:
        import importlib
        for module_name in ["core.evolution", "core.agent_loop", "core.telegram"]:
            try:
                mod = importlib.import_module(module_name)
                importlib.reload(mod)
            except Exception as e:
                return False, f"Import failed for {module_name}: {e}"
    except Exception as e:
        return False, f"Import validation failed: {e}"

    # Check health
    try:
        from core.hot_reload import verify_reload_health
        healthy, err = verify_reload_health()
        if not healthy:
            return False, f"Health check failed: {err}"
    except Exception as e:
        return False, f"Health check error: {e}"

    return True, "All checks passed"


# ─── Core Update Flow (integrated with mutation lifecycle) ─────────────────────

def check_for_updates() -> Dict[str, Any]:
    """Check if origin/main has new commits."""
    local_commit = get_current_commit_full()

    success, _, err = _run_git(["fetch", "origin", "main"])
    if not success:
        return {"has_updates": False, "error": f"Fetch failed: {err}"}

    success, stdout, _ = _run_git(["rev-list", "--count", "HEAD..origin/main"])
    commits_behind = int(stdout) if success and stdout.isdigit() else 0

    success, remote_commit, _ = _run_git(["rev-parse", "origin/main"])

    return {
        "has_updates": commits_behind > 0,
        "local_commit": local_commit,
        "remote_commit": remote_commit if success else "unknown",
        "commits_behind": commits_behind,
    }


def pull_and_validate() -> Dict[str, Any]:
    """
    Blue/Green pull: fetch changes into green slot, validate, then switch.
    
    This is the core function called after a mutation is promoted OR
    when checking for external updates.
    """
    bg = BlueGreenState()
    old_commit = get_current_commit_full()

    # Fetch and determine what changed
    _run_git(["stash"])
    success, _, err = _run_git(["pull", "origin", "main", "--ff-only"])
    if not success:
        # Force reset if ff-only fails
        success, _, err = _run_git(["reset", "--hard", "origin/main"])
        if not success:
            return {"success": False, "error": f"Pull failed: {err}", "action": "none"}

    new_commit = get_current_commit_full()
    if new_commit == old_commit:
        return {"success": True, "action": "no_change", "commit": new_commit[:8]}

    # Get changed files
    success, diff_output, _ = _run_git(["diff", "--name-only", old_commit, new_commit])
    changed_files = diff_output.split("\n") if success and diff_output else []

    # Stage as green
    bg.prepare_green(new_commit)
    print(f"[AUTO-UPDATE] Green staged: {old_commit[:8]} → {new_commit[:8]} ({len(changed_files)} files)")

    # Validate green
    valid, reason = validate_green_deployment(changed_files)

    if not valid:
        # Rollback to blue
        print(f"[AUTO-UPDATE] Green FAILED validation: {reason}")
        _run_git(["reset", "--hard", old_commit])
        bg.rollback_to_blue(reason)
        _log_update(old_commit, new_commit, changed_files, success=False, reason=reason)
        return {
            "success": False,
            "action": "rollback",
            "error": reason,
            "old_commit": old_commit[:8],
            "new_commit": new_commit[:8],
        }

    # Green passed — switch
    bg.switch_to_green()
    print(f"[AUTO-UPDATE] Green PASSED validation — switching active deployment")
    _log_update(old_commit, new_commit, changed_files, success=True)

    return {
        "success": True,
        "action": "updated",
        "old_commit": old_commit[:8],
        "new_commit": new_commit[:8],
        "files_changed": changed_files,
        "needs_restart": _needs_restart(changed_files),
    }


def _needs_restart(changed_files: list) -> bool:
    """Determine if changes require a full daemon restart vs hot-reload."""
    # These files can't be hot-reloaded safely
    restart_required_patterns = [
        "council_daemon.py",
        "core/graph.py",
        "core/state.py",
        "core/checkpointer.py",
        "requirements.txt",
        "Dockerfile",
    ]
    for f in changed_files:
        for pattern in restart_required_patterns:
            if f == pattern or f.endswith(pattern):
                return True
    return False


def restart_daemon() -> None:
    """Replace current process with fresh one (blue/green switch completion)."""
    print("[AUTO-UPDATE] Restarting daemon (blue/green switch)...")

    # Write restart marker for the new process
    try:
        RESTART_MARKER.parent.mkdir(parents=True, exist_ok=True)
        RESTART_MARKER.write_text(json.dumps({
            "restarted_at": datetime.utcnow().isoformat(),
            "reason": "blue_green_switch",
            "pid": os.getpid(),
            "commit": get_current_commit(),
        }))
    except Exception:
        pass

    python = sys.executable
    os.execv(python, [python] + sys.argv)


# ─── Integration Point: Called from evolution saga ─────────────────────────────

async def post_promote_update(mutation_id: str, changed_files: list) -> Dict[str, Any]:
    """
    Called after _promote_mutation() merges to main.
    
    This is the blue/green integration point in the mutation lifecycle:
    promote → pull (green) → validate → switch/rollback → hot-reload or restart
    
    The council already approved this via consensus, so this is the execution phase.
    """
    from core.hot_reload import reload_changed_modules, verify_reload_health

    result = pull_and_validate()

    if not result.get("success"):
        # Notify council of failed deployment
        await _notify_council(
            f"❌ Mutation {mutation_id[:12]} promoted but deployment FAILED: {result.get('error')}\n"
            f"Rolled back to previous version."
        )
        return result

    if result.get("action") == "no_change":
        return result

    # Determine: hot-reload or restart?
    if result.get("needs_restart"):
        await _notify_council(
            f"🔄 Mutation {mutation_id[:12]} requires daemon restart.\n"
            f"Commit: {result['old_commit']} → {result['new_commit']}\n"
            f"Restarting in 3 seconds..."
        )
        await asyncio.sleep(3)
        restart_daemon()
    else:
        # Hot-reload is sufficient
        reload_result = reload_changed_modules(changed_files)
        if reload_result["success"]:
            # Finalize green as new blue baseline
            bg = BlueGreenState()
            bg.finalize_green()
            await _notify_council(
                f"✅ Mutation {mutation_id[:12]} deployed (hot-reload).\n"
                f"Commit: {result['old_commit']} → {result['new_commit']}\n"
                f"Files: {', '.join(changed_files[:5])}"
            )
        else:
            # Hot-reload failed but validation passed — restart to be safe
            await _notify_council(
                f"⚠️ Mutation {mutation_id[:12]} hot-reload failed. Restarting daemon...\n"
                f"Reason: {reload_result.get('errors')}"
            )
            await asyncio.sleep(2)
            restart_daemon()

    return result


# ─── Periodic Check (for external pushes, not mutation-triggered) ──────────────

class AutoUpdateLoop:
    """
    Periodic check for external updates (human pushes, other tools).
    Runs as a background task in the daemon's event loop.
    
    This is SEPARATE from mutation-triggered updates (which go through
    post_promote_update). This catches changes pushed by humans or CI.
    """

    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self.enabled = os.environ.get("AUTO_UPDATE_ENABLED", "true").lower() == "true"
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background update loop."""
        if self.enabled:
            self._task = asyncio.create_task(self._loop())
            print(f"[AUTO-UPDATE] Background check enabled (every {self.interval}s)")

    async def _loop(self):
        """Main loop - check for updates periodically."""
        # Wait a bit after startup before first check
        await asyncio.sleep(30)

        while True:
            try:
                check = check_for_updates()
                if check.get("has_updates"):
                    commits = check["commits_behind"]
                    print(f"[AUTO-UPDATE] {commits} new commit(s) on origin/main")
                    result = pull_and_validate()

                    if result.get("success") and result.get("action") == "updated":
                        if result.get("needs_restart"):
                            await _notify_council(
                                f"🔄 External update detected ({commits} commits). "
                                f"Restart required. Restarting..."
                            )
                            await asyncio.sleep(3)
                            restart_daemon()
                        else:
                            # Hot-reload external changes
                            from core.hot_reload import reload_changed_modules
                            files = result.get("files_changed", [])
                            reload_changed_modules(files)
                            bg = BlueGreenState()
                            bg.finalize_green()
                            await _notify_council(
                                f"✅ External update applied (hot-reload). "
                                f"{result['old_commit']} → {result['new_commit']}"
                            )
            except Exception as e:
                print(f"[AUTO-UPDATE] Check failed: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        if self._task:
            self._task.cancel()


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _notify_council(message: str):
    """Send notification via Telegram."""
    try:
        from core.telegram import send_council_message
        await send_council_message("AUTO-UPDATE", message)
    except Exception:
        pass


def _log_update(old_commit: str, new_commit: str, files: list, success: bool, reason: str = ""):
    """Log update to evolution/update_log.json."""
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "old_commit": old_commit[:8],
            "new_commit": new_commit[:8],
            "files_changed": len(files),
            "success": success,
            "reason": reason,
        }
        log = []
        if UPDATE_LOG_FILE.exists():
            log = json.loads(UPDATE_LOG_FILE.read_text())
        log.append(log_entry)
        log = log[-50:]
        UPDATE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_LOG_FILE.write_text(json.dumps(log, indent=2))
    except Exception:
        pass


def get_version_info() -> Dict[str, Any]:
    """Get current deployment version info for /version command."""
    bg = BlueGreenState()
    return {
        "commit": get_current_commit(),
        "commit_full": get_current_commit_full(),
        "active_slot": bg.state.get("active_slot", "blue"),
        "last_switch": bg.state.get("last_switch"),
        "auto_update_enabled": os.environ.get("AUTO_UPDATE_ENABLED", "true").lower() == "true",
    }
