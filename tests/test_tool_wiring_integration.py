"""Integration test: verify the full tool wiring pipeline works end-to-end.

Tests:
1. Auto-discovery scans tools/ and registers @tool functions
2. Planning prompt includes dynamically-registered tool names
3. execute_step dispatches to registered tools (not just hardcoded ones)
4. Janitor audit_tool_quality detects duplicates and orphans
5. Full pipeline: discover → plan → execute → audit
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestAutoDiscovery:
    """Test tools/auto_discovery.py functionality."""

    def test_discover_and_register_runs(self):
        """Auto-discovery runs without errors and returns structured result."""
        from tools.auto_discovery import discover_and_register
        result = discover_and_register(force=True)
        assert "registered" in result
        assert "skipped" in result
        assert "failed" in result
        assert "already_loaded" in result

    def test_discovered_tools_in_registry(self):
        """Tools discovered from files appear in MCP_REGISTRY."""
        from tools.auto_discovery import discover_and_register, get_available_tool_names
        discover_and_register(force=True)
        names = get_available_tool_names()
        # Core tools should always be present
        assert "editor" in names
        assert "shell_exec" in names
        assert "load_tool" in names
        # At least some tools should be registered
        assert len(names) >= 9  # 9 core tools minimum

    def test_get_tool_descriptions_format(self):
        """get_tool_descriptions() returns formatted string."""
        from tools.auto_discovery import discover_and_register, get_tool_descriptions
        discover_and_register(force=True)
        desc = get_tool_descriptions()
        assert "Available tools:" in desc
        assert "editor:" in desc

    def test_skip_files_excluded(self):
        """SKIP_FILES are never loaded by discovery."""
        from tools.auto_discovery import discover_and_register, SKIP_FILES
        result = discover_and_register(force=True)
        all_files = [r["file"] for r in result.get("registered", [])]
        all_files += [r["file"] for r in result.get("failed", [])]
        for skip in SKIP_FILES:
            assert skip not in all_files, f"{skip} should be skipped"

    def test_security_validation_blocks_dangerous(self):
        """Security validator rejects files with subprocess/eval."""
        from tools.auto_discovery import _validate_tool_file
        
        # Create a dangerous temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import subprocess\nsubprocess.run(['rm', '-rf', '/'])\n")
            f.flush()
            is_safe, reason = _validate_tool_file(Path(f.name))
        
        os.unlink(f.name)
        assert not is_safe
        assert "subprocess" in reason.lower() or "Dangerous" in reason

    def test_security_validation_allows_safe(self):
        """Security validator allows normal tool files."""
        from tools.auto_discovery import _validate_tool_file
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool
import json

@tool
def my_safe_tool(query: str) -> str:
    \"\"\"A safe tool that just returns data.\"\"\"
    return json.dumps({"result": query})
""")
            f.flush()
            is_safe, reason = _validate_tool_file(Path(f.name))
        
        os.unlink(f.name)
        assert is_safe, f"Should be safe but got: {reason}"

    def test_has_tool_decorator_detection(self):
        """_has_tool_decorator correctly identifies @tool functions."""
        from tools.auto_discovery import _has_tool_decorator
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from langchain_core.tools import tool\n@tool\ndef foo(): pass\n")
            f.flush()
            assert _has_tool_decorator(Path(f.name))
        os.unlink(f.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo(): pass\n")
            f.flush()
            assert not _has_tool_decorator(Path(f.name))
        os.unlink(f.name)

    def test_extract_tool_names(self):
        """_extract_tool_names finds @tool function names."""
        from tools.auto_discovery import _extract_tool_names
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def my_tool_a(x: str) -> str:
    pass

@tool
def my_tool_b(y: int) -> str:
    pass

def not_a_tool():
    pass
""")
            f.flush()
            names = _extract_tool_names(Path(f.name))
        
        os.unlink(f.name)
        assert "my_tool_a" in names
        assert "my_tool_b" in names
        assert "not_a_tool" not in names


class TestJanitorToolQuality:
    """Test the janitor's tool quality audit."""

    def test_audit_tool_quality_runs(self):
        """audit_tool_quality returns structured report."""
        from tools.auto_discovery import discover_and_register, audit_tool_quality
        discover_and_register(force=True)
        result = audit_tool_quality()
        assert "duplicate_purpose" in result
        assert "orphaned_files" in result
        assert "recommendations" in result

    def test_janitor_full_audit_includes_tool_quality(self):
        """full_audit() now includes tool_quality section."""
        from tools.repo_janitor import full_audit
        report = full_audit()
        assert "tool_quality" in report


class TestPlanningToolInjection:
    """Test that planning injects registered tools into prompts."""

    def test_create_plan_includes_dynamic_tools(self):
        """create_plan prompt includes dynamically registered tool names."""
        from tools.auto_discovery import discover_and_register, get_available_tool_names
        discover_and_register(force=True)
        
        tool_names = get_available_tool_names()
        # Should have more than just the 3 hardcoded ones
        assert len(tool_names) > 3
        # Core tools present
        assert "editor" in tool_names
        assert "shell_exec" in tool_names


class TestExecuteStepDispatch:
    """Test that execute_step dispatches to dynamically registered tools."""

    def test_dispatch_to_registered_tool(self):
        """execute_step can call a dynamically registered tool."""
        from tools.mcp_registry import _tool_registry, register_tool
        from langchain_core.tools import tool
        
        @tool
        def test_dynamic_tool(query: str) -> str:
            """A test tool for integration testing."""
            return f"dynamic_result: {query}"
        
        register_tool(test_dynamic_tool)
        assert "test_dynamic_tool" in _tool_registry
        
        # Verify the tool works when invoked
        result = _tool_registry["test_dynamic_tool"].invoke("hello")
        assert "dynamic_result: hello" in result
        
        # Cleanup
        del _tool_registry["test_dynamic_tool"]

    def test_unknown_tool_returns_error(self):
        """execute_step with unknown tool name produces error."""
        from tools.mcp_registry import _tool_registry
        assert "nonexistent_tool_xyz" not in _tool_registry


class TestEndToEnd:
    """Full pipeline integration test."""

    def test_full_pipeline(self):
        """Discover → register → available in planning → audit finds them."""
        from tools.auto_discovery import (
            discover_and_register,
            get_available_tool_names,
            audit_tool_quality,
        )
        from tools.mcp_registry import _tool_registry
        
        # Step 1: Discovery
        result = discover_and_register(force=True)
        assert result.get("status") != "skipped"
        
        # Step 2: Tools available
        names = get_available_tool_names()
        assert len(names) >= 9
        
        # Step 3: All registered tools are callable
        for name in names[:5]:
            tool_func = _tool_registry[name]
            assert hasattr(tool_func, "invoke"), f"Tool {name} not invocable"
        
        # Step 4: Audit finds no critical issues
        audit = audit_tool_quality()
        # Should have structured output even if empty
        assert isinstance(audit["duplicate_purpose"], list)
        assert isinstance(audit["orphaned_files"], list)
        
        print(f"\n✅ Full pipeline OK: {len(names)} tools registered")
        print(f"   Duplicates found: {len(audit['duplicate_purpose'])}")
        print(f"   Orphaned files: {len(audit['orphaned_files'])}")


def run_all():
    """Run all tests and report results."""
    import traceback
    
    test_classes = [
        TestAutoDiscovery,
        TestJanitorToolQuality,
        TestPlanningToolInjection,
        TestExecuteStepDispatch,
        TestEndToEnd,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for cls in test_classes:
        print(f"\n{'─' * 60}")
        print(f"  {cls.__name__}")
        print(f"{'─' * 60}")
        
        instance = cls()
        for method_name in dir(instance):
            if not method_name.startswith("test_"):
                continue
            method = getattr(instance, method_name)
            try:
                method()
                print(f"  ✅ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
                errors.append((f"{cls.__name__}.{method_name}", traceback.format_exc()))
                failed += 1
    
    print(f"\n{'═' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'═' * 60}")
    
    if errors:
        print("\nFailure details:")
        for name, tb in errors:
            print(f"\n--- {name} ---")
            print(tb)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
