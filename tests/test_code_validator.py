import pytest
from tools.code_validator import validate_tool_code, ToolCodeValidator, SecurityViolation


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

    def test_blocks_sys_import(self):
        code = "import sys\nsys.exit(0)"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_socket_import(self):
        code = "import socket\ns = socket.socket()"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_eval_function(self):
        code = "result = eval('1+1')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe
        assert any("eval" in str(v) for v in violations)

    def test_blocks_exec_function(self):
        code = "exec('print(1)')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_dunder_subclasses(self):
        code = "().__class__.__base__.__subclasses__()"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe
        assert any("__subclasses__" in str(v) for v in violations)

    def test_blocks_dunder_bases(self):
        code = "obj.__bases__"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_os_system_pattern(self):
        code = "import something\nos.system('rm -rf /')"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_blocks_subprocess_run_pattern(self):
        code = "subprocess.run(['rm', '-rf', '/'])"
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

    def test_allows_math_operations(self):
        code = "result = 1 + 2 * 3"
        is_safe, violations = validate_tool_code(code)
        assert is_safe

    def test_allows_string_operations(self):
        code = "text = 'hello'.upper()"
        is_safe, violations = validate_tool_code(code)
        assert is_safe

    def test_allows_list_operations(self):
        code = "items = [1, 2, 3]\nresult = sum(items)"
        is_safe, violations = validate_tool_code(code)
        assert is_safe

    def test_allows_dict_operations(self):
        code = "data = {'key': 'value'}\nprint(data['key'])"
        is_safe, violations = validate_tool_code(code)
        assert is_safe

    def test_catches_syntax_error(self):
        code = "def broken(\n"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe
        assert any("Syntax error" in str(v) for v in violations)

    def test_multiple_violations(self):
        code = """
import os
import subprocess
eval('code')
"""
        is_safe, violations = validate_tool_code(code)
        assert not is_safe
        assert len(violations) >= 3

    def test_from_import_blocked(self):
        code = "from os import system"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_nested_import_blocked(self):
        code = "from os.path import join"
        is_safe, violations = validate_tool_code(code)
        assert not is_safe

    def test_allows_standard_library_safe_modules(self):
        code = """
import json
import math
import datetime
data = json.dumps({'key': 'value'})
result = math.sqrt(16)
"""
        is_safe, violations = validate_tool_code(code)
        assert is_safe


class TestToolCodeValidatorClass:
    def test_validator_initialization(self):
        code = "print('test')"
        validator = ToolCodeValidator(code)
        assert validator.code == code
        assert validator.violations == []

    def test_validator_validate_method(self):
        code = "import os"
        validator = ToolCodeValidator(code)
        is_safe, violations = validator.validate()
        assert not is_safe
        assert len(violations) > 0

    def test_security_violation_has_line_number(self):
        code = "x = 1\nimport os\ny = 2"
        validator = ToolCodeValidator(code)
        is_safe, violations = validator.validate()
        assert not is_safe
        assert violations[0].line == 2
