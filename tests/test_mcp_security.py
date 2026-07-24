import pytest
import tempfile
import os
from tools.mcp_registry import (
    load_tool,
    approve_tool,
    list_pending_tools,
    list_approved_tools,
    _pending_tools,
    _approved_tools,
    _tool_registry
)
from tools.code_validator import validate_tool_code


class TestCodeValidator:
    def test_blocks_os_import(self):
        code = "import os\nos.system('ls')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe
        assert any("os" in str(v) for v in violations)

    def test_blocks_subprocess_import(self):
        code = "import subprocess\nsubprocess.run(['ls'])"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_eval(self):
        code = "eval('1+1')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_exec(self):
        code = "exec('print(1)')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_dunder_methods(self):
        code = "().__class__.__base__.__subclasses__()"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_allows_safe_code(self):
        code = """
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    return a + b
"""
        is_safe, violations = validate_tool_code(code)
        assert is_safe
        assert len(violations) == 0


class TestToolRegistration:
    def setup_method(self):
        _pending_tools.clear()
        _approved_tools.clear()

    def test_load_tool_validates_security(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import os\nos.system('ls')")
            f.flush()
            
            result = load_tool.invoke({"filepath": f.name})
            assert "Security validation failed" in result
            
            os.unlink(f.name)

    def test_load_tool_creates_pending(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def test_func(x: int) -> int:
    return x * 2
""")
            f.flush()
            
            result = load_tool.invoke({"filepath": f.name})
            assert "pending approval" in result
            
            tool_id = os.path.basename(f.name).replace(".py", "")
            assert tool_id in _pending_tools
            
            os.unlink(f.name)

    def test_approve_tool_activates(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    return a * b
""")
            f.flush()
            
            load_tool.invoke({"filepath": f.name})
            tool_id = os.path.basename(f.name).replace(".py", "")
            
            result = approve_tool.invoke({"tool_id": tool_id})
            assert "registered" in result
            assert tool_id not in _pending_tools
            assert "multiply" in _approved_tools
            
            os.unlink(f.name)

    def test_list_pending_tools(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def pending_func(x: str) -> str:
    return x.upper()
""")
            f.flush()
            
            load_tool.invoke({"filepath": f.name})
            
            result = list_pending_tools.invoke({})
            assert "pending approval" in result
            
            os.unlink(f.name)

    def test_list_approved_tools(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def approved_func(x: int) -> int:
    return x + 1
""")
            f.flush()
            
            load_tool.invoke({"filepath": f.name})
            tool_id = os.path.basename(f.name).replace(".py", "")
            approve_tool.invoke({"tool_id": tool_id})
            
            result = list_approved_tools.invoke({})
            assert "approved_func" in result
            
            os.unlink(f.name)

    def test_auto_approve_bypasses_pending(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from langchain_core.tools import tool

@tool
def auto_func(x: int) -> int:
    return x * 3
""")
            f.flush()
            
            result = load_tool.invoke({"filepath": f.name, "auto_approve": True})
            assert "registered" in result
            assert "auto_func" in _approved_tools
            
            os.unlink(f.name)
