"""Mission Governor: checks whether proposed mutations advance mission pillars."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


PILLAR_TARGET_MAP: Dict[int, List[str]] = {
    1: [
        "core/evolution.py",
        "core/mutation_proposer.py",
        "core/mutation_validator.py",
        "core/mutation_deduplicator.py",
        "agents/",
        "core/governor.py",
        "core/learning.py",
        "core/feedback.py",
    ],
    2: [
        "core/api_router.py",
        "core/quota_monitor.py",
        "core/provider_router.py",
        "core/llm_cache.py",
        "core/semantic_cache.py",
        "providers.yaml",
        "core/llm_provider.py",
        "core/provider_benchmark.py",
    ],
     3: [
         "providers.yaml",
         "core/api_router.py",
         "core/provider_router.py",
         "core/ollama_client.py",
         "tools/",
         "tools/ollama_adapter.py",
         "core/provider_benchmark.py",
         "core/llm_provider.py",
     ],
    4: [
        "core/checkpointer.py",
        "core/goals.py",
        "core/state_manager.py",
        "core/state_recovery.py",
        "core/snapdeploy.py",
        "core/rollout.py",
        "core/data_logger.py",
        "core/version_store.py",
    ],
    5: [
        "core/telegram.py",
        "agents/",
        "core/operator_interface.py",
        "core/council_monitor.py",
        "core/communication.py",
        "core/mesh_communication.py",
        "core/node_monitor.py",
    ],
}

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


def _matches_pillar(path: str, pillar: int) -> bool:
    prefixes = PILLAR_TARGET_MAP.get(pillar, [])
    return any(path == p or path.startswith(p) for p in prefixes)


def _is_allowed_path(path: str) -> bool:
    if any(path.startswith(d) or path == d for d in DENYLIST_CRITICAL):
        return False
    return any(path == a or path.startswith(a) for a in ALLOWLIST_NON_CRITICAL)


def is_mission_aligned(mutation: Dict[str, Any]) -> bool:
    changes = mutation.get("proposed_changes") or {}
    if not isinstance(changes, dict):
        return False

    pillar = mutation.get("mission_pillar")
    file_changes = changes.get("file_changes") or []
    if isinstance(file_changes, list) and file_changes:
        paths = []
        for fc in file_changes:
            if isinstance(fc, dict):
                fc_path = fc.get("path")
                if fc_path is None:
                    continue
                if isinstance(fc_path, dict):
                    fc_path = fc_path.get("path", "")
                if not isinstance(fc_path, str):
                    continue
                paths.append(fc_path)
        if not paths:
            return False
        if pillar and any(_matches_pillar(p, pillar) for p in paths):
            return True
        for p in paths:
            if not _is_allowed_path(p):
                continue
            for pillar_num in PILLAR_TARGET_MAP:
                if _matches_pillar(p, pillar_num):
                    return True
        if pillar:
            desc = str(mutation.get("description", "")).lower()
            pillar_keywords = {
                1: ["self-evolve", "self-improve", "learn", "optimize", "feedback", "mutation", "evolution", "goal detection", "temperature", "prompt optimization", "error handling", "failure recovery"],
                2: ["cost", "cheap", "free", "failover", "groq", "cloud", "provider", "rate limit", "cooldown", "resource", "quota", "routing", "cache", "batch"],
                3: ["provider", "model", "agnostic", "fallback", "ollama", "cloud-first", "load balance", "multi-model", "router", "tool", "tools", "web scrape", "scraping", "research", "discovery", "add capability"],
                4: ["persist", "sqlite", "database", "checkpoint", "store", "recovery", "state", "goal", "memory", "durable", "integrity", "repair"],
                5: ["telegram", "human", "operator", "command", "status", "/who", "/goal", "interface", "steer", "approval", "notification", "natural language", "nlp", "companion"],
            }
            keywords = pillar_keywords.get(pillar, [])
            if any(kw in desc for kw in keywords):
                return True
        return False

    if pillar:
        return True
    return False


def requires_approval(mutation: Dict[str, Any]) -> bool:
    changes = mutation.get("proposed_changes") or {}
    file_changes = changes.get("file_changes") or []
    if isinstance(file_changes, list):
        for fc in file_changes:
            if isinstance(fc, dict) and fc.get("path") in APPROVAL_REQUIRED:
                return True
    return False


def get_mission_pillar(path: str) -> Optional[int]:
    for pillar_num, prefixes in PILLAR_TARGET_MAP.items():
        if any(path == p or path.startswith(p) for p in prefixes):
            return pillar_num
    return None


def get_pillar_name(pillar: int) -> str:
    names = {
        1: "Recursive Self-Evolution",
        2: "Autonomous Resource Optimization",
        3: "Model Agnosticism",
        4: "Durable Local State",
        5: "Companion Alignment",
    }
    return names.get(pillar, "Unknown")
