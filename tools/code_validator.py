import ast
import re
from typing import List, Tuple

BLOCKED_IMPORTS = {
    'os', 'subprocess', 'sys', 'shutil', 'socket', 'http', 'urllib',
    'requests', 'ctypes', 'multiprocessing', 'threading', 'signal',
    'pickle', 'shelve', 'marshal', 'tempfile', 'pathlib'
}

BLOCKED_FUNCTIONS = {
    'eval', 'exec', 'compile', '__import__', 'execfile', 'input',
    'raw_input', 'breakpoint'
}

BLOCKED_ATTRIBUTES = {
    '__subclasses__', '__bases__', '__mro__', '__class__', '__globals__',
    '__code__', '__closure__', '__func__', '__self__', '__module__',
    '__dict__', '__wrapped__', '__qualname__'
}

DANGEROUS_PATTERNS = [
    r'os\.system',
    r'os\.popen',
    r'os\.exec',
    r'subprocess\.(run|call|Popen|check_output)',
    r'shutil\.(rmtree|copyfile|move)',
    r'socket\.(socket|create_connection)',
    r'urllib\.request\.urlopen',
    r'requests\.(get|post|put|delete)',
    r'ctypes\.CDLL',
    r'pickle\.loads?',
    r'marshal\.loads?',
    r'__import__\s*\(',
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
]


class SecurityViolation(Exception):
    def __init__(self, message: str, line: int = None):
        self.message = message
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


class ToolCodeValidator:
    def __init__(self, code: str):
        self.code = code
        self.violations: List[SecurityViolation] = []

    def validate(self) -> Tuple[bool, List[SecurityViolation]]:
        self.violations = []
        
        try:
            tree = ast.parse(self.code)
        except SyntaxError as e:
            self.violations.append(SecurityViolation(f"Syntax error: {e.msg}", e.lineno))
            return False, self.violations

        self._check_imports(tree)
        self._check_function_calls(tree)
        self._check_attribute_access(tree)
        self._check_dangerous_patterns()

        return len(self.violations) == 0, self.violations

    def _check_imports(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BLOCKED_IMPORTS:
                        self.violations.append(
                            SecurityViolation(f"Blocked import: {alias.name}", node.lineno)
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in BLOCKED_IMPORTS:
                    self.violations.append(
                        SecurityViolation(f"Blocked import from: {node.module}", node.lineno)
                    )

    def _check_function_calls(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in BLOCKED_FUNCTIONS:
                        self.violations.append(
                            SecurityViolation(f"Blocked function: {node.func.id}", node.lineno)
                        )

    def _check_attribute_access(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in BLOCKED_ATTRIBUTES:
                    self.violations.append(
                        SecurityViolation(f"Blocked attribute: {node.attr}", node.lineno)
                    )

    def _check_dangerous_patterns(self):
        lines = self.code.split('\n')
        for pattern in DANGEROUS_PATTERNS:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.violations.append(
                        SecurityViolation(f"Dangerous pattern: {pattern}", i)
                    )


def validate_tool_code(code: str) -> Tuple[bool, List[SecurityViolation]]:
    validator = ToolCodeValidator(code)
    return validator.validate()
