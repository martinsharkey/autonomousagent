"""Smoke test: validate all core modules can be imported without crashing.

This is the MINIMUM bar for any code change — if a module can't import,
the daemon will crash. The council's post-goal test gate runs this first.

NOTE: Modules that depend on optional packages (telegram, etc.) are tested
with allowance for ModuleNotFoundError on those specific packages — the test
catches SYNTAX errors and broken internal imports, not missing pip packages.
"""
import importlib
import sys
import pytest


# Optional packages that may not be installed in every environment
OPTIONAL_PACKAGES = {"telegram", "huggingface_hub", "docker", "redis"}


def _try_import(module_path: str):
    """Import a module, allowing ModuleNotFoundError for optional deps only."""
    if module_path in sys.modules:
        del sys.modules[module_path]
    try:
        mod = importlib.import_module(module_path)
        return mod
    except ModuleNotFoundError as e:
        # Only allow failure if it's an optional package
        missing = str(e).replace("No module named ", "").strip("'\"")
        root_pkg = missing.split(".")[0]
        if root_pkg in OPTIONAL_PACKAGES:
            pytest.skip(f"Optional dependency not installed: {missing}")
        raise  # Re-raise if it's a real missing internal module


# Every module the daemon depends on at runtime
CORE_MODULES = [
    "core.state",
    "core.graph",
    "core.goals",
    "core.planning",
    "core.evolution",
    "core.curiosity",
    "core.governor",
    "core.agent_config",
    "core.agent_context",
    "core.checkpointer",
    "core.llm_router",
    "core.llm_provider",
    "core.editor_tool",
    "core.mutation_deduplicator",
    "core.mutation_safety_gate",
    "core.mutation_validator",
    "core.role_dispatcher",
    "core.sandbox",
    "core.health",
    "core.recovery",
    "core.quota_monitor",
    "core.feedback",
    "core.learning",
    "core.memory",
    "core.react",
    "core.hot_reload",
    "core.auto_update",
    "core.daemon_cluster",
    "core.consciousness_metric",
    "core.self_pentest",
    "core.github_sync",
    "core.secrets_vault",
    "core.deployer",
    "core.daily_report",
    "core.host_awareness",
]

TOOL_MODULES = [
    "tools.mcp_registry",
    "tools.auto_discovery",
    "tools.repo_janitor",
    "tools.code_validator",
]

GOVERNANCE_MODULES = [
    "governance.audit_log",
    "governance.consensus",
    "governance.decision_logger",
    "governance.zero_trust",
]

AGENT_MODULES = [
    "agents.alpha_evaluator",
    "agents.autobot",
    "agents.beta_worker",
]


@pytest.mark.parametrize("module_path", CORE_MODULES)
def test_core_import(module_path):
    """Each core module must import without error."""
    mod = _try_import(module_path)
    assert mod is not None


@pytest.mark.parametrize("module_path", TOOL_MODULES)
def test_tool_import(module_path):
    """Each tool module must import without error."""
    mod = _try_import(module_path)
    assert mod is not None


@pytest.mark.parametrize("module_path", GOVERNANCE_MODULES)
def test_governance_import(module_path):
    """Each governance module must import without error."""
    mod = _try_import(module_path)
    assert mod is not None


@pytest.mark.parametrize("module_path", AGENT_MODULES)
def test_agent_import(module_path):
    """Each agent module must import without error."""
    mod = _try_import(module_path)
    assert mod is not None


def test_council_daemon_importable():
    """The daemon entry point must be importable."""
    mod = _try_import("council_daemon")
    assert mod is None or hasattr(mod, "CouncilDaemon")


def test_agent_loop_importable():
    """The agent loop must be importable."""
    mod = _try_import("core.agent_loop")
    assert mod is None or hasattr(mod, "AutonomousAgentLoop")
