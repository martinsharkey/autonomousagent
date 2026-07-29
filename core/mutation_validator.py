"""Validate mutations before they reach council vote."""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Tuple

from core.mutation_deduplicator import get_deduplicator
from core.mutation_proposer import (
    FILE_MUTATION_ALLOWLIST,
    FILE_MUTATION_DENYLIST,
    VALID_PARAMS,
)


CRITICAL_FILES = {
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


class MutationValidator:
    """Validate proposed mutations before council voting."""

    async def validate_proposal(self, proposal: Dict[str, Any]) -> Tuple[bool, str]:
        """Return (is_valid, reason)."""
        changes = proposal.get("proposed_changes") or {}
        if not isinstance(changes, dict):
            return False, "proposed_changes is not a dict"

        agent_name = proposal.get("agent_name")
        if not agent_name:
            return False, "No agent_name in proposal"

        file_changes = changes.get("file_changes")
        if file_changes:
            if not isinstance(file_changes, list):
                return False, "file_changes must be a list"
            for fc in file_changes:
                if not isinstance(fc, dict):
                    continue
                path = fc.get("path", "")
                kind = fc.get("kind", "create")
                if kind in ("modify", "replace", "delete") and path in CRITICAL_FILES:
                    return (
                        False,
                        f"Critical file {path} requires human approval",
                    )
                    return False, "Each file_change must be a dict"
                is_valid, reason = await self._validate_file_change(fc)
                if not is_valid:
                    return False, reason
        else:
            valid_params = VALID_PARAMS.get(agent_name, [])
            for param_name in changes.keys():
                if param_name not in valid_params:
                    return (
                        False,
                        f"Invalid param '{param_name}' for {agent_name}. "
                        f"Valid: {valid_params}",
                    )

        mission_pillar = proposal.get("mission_pillar")
        if mission_pillar is None or mission_pillar < 1 or mission_pillar > 5:
            return False, "No valid mission pillar (1-5 required)"

        return True, "Valid"

    async def _validate_file_change(self, file_change: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a single file change."""
        path = file_change.get("path", "")
        content = file_change.get("content", "")
        kind = file_change.get("kind", "create")

        for denied in FILE_MUTATION_DENYLIST:
            if denied in path:
                return False, f"Denied path: {path}"

        allowed = False
        for allow in FILE_MUTATION_ALLOWLIST:
            if allow in path or path.startswith(allow):
                allowed = True
                break

        if not allowed:
            return False, f"Path not in allowlist: {path}"

        if path.endswith(".py") and content:
            try:
                ast.parse(content)
            except SyntaxError as e:
                return False, f"Syntax error in {path}: {e}"

        return True, "Valid"