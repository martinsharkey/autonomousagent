import subprocess
import tempfile
import os
import uuid
import json
import shlex
from typing import Optional
from pathlib import Path

SANDBOX_TIMEOUT = 30
SANDBOX_MEMORY_LIMIT = "512m"
SANDBOX_CPU_LIMIT = "1.0"
SANDBOX_PIDS_LIMIT = "64"
SANDBOX_IMAGE = "python:3.11-slim"

_SANDBOX_MODE = os.getenv("SANDBOX_MODE", "production")

def _is_docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def execute_in_sandbox(command: str, timeout: int = SANDBOX_TIMEOUT, allow_unsafe: bool = False) -> str:
    if _is_docker_available():
        return _execute_in_docker_sandbox(command, timeout)
    elif allow_unsafe or _SANDBOX_MODE == "developer-unsafe":
        print("[WARNING] Using unsafe subprocess fallback - Docker not available")
        return _execute_in_subprocess_sandbox(command, timeout)
    else:
        return "ERROR: Docker required for sandbox execution. Set SANDBOX_MODE=developer-unsafe for local debugging only."

def _execute_in_docker_sandbox(command: str, timeout: int) -> str:
    container_name = f"sandbox-{uuid.uuid4().hex[:8]}"
    
    try:
        docker_cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--memory", SANDBOX_MEMORY_LIMIT,
            "--cpus", SANDBOX_CPU_LIMIT,
            "--pids-limit", SANDBOX_PIDS_LIMIT,
            "--network", "none",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--tmpfs", "/tmp:noexec,size=64m",
            SANDBOX_IMAGE,
            "sh", "-c", command
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            return f"Command failed with exit code {result.returncode}:\n{result.stderr}"
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Sandbox execution error: {str(e)}"

def _execute_in_subprocess_sandbox(command: str, timeout: int) -> str:
    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )
        
        if result.returncode != 0:
            return f"Command failed with exit code {result.returncode}:\n{result.stderr}"
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Sandbox execution error: {str(e)}"

def execute_python_in_sandbox(code: str, timeout: int = SANDBOX_TIMEOUT) -> str:
    if _is_docker_available():
        return _execute_python_in_docker(code, timeout)
    else:
        return _execute_python_in_subprocess(code, timeout)

def _execute_python_in_docker(code: str, timeout: int) -> str:
    container_name = f"sandbox-py-{uuid.uuid4().hex[:8]}"
    
    try:
        docker_cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--memory", SANDBOX_MEMORY_LIMIT,
            "--cpus", SANDBOX_CPU_LIMIT,
            "--pids-limit", SANDBOX_PIDS_LIMIT,
            "--network", "none",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--tmpfs", "/tmp:noexec,size=64m",
            "-i", SANDBOX_IMAGE,
            "python", "-c", code
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            return f"Python execution failed:\n{result.stderr}"
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)
        return f"Python execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Python sandbox error: {str(e)}"

def _execute_python_in_subprocess(code: str, timeout: int) -> str:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    
    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )
        
        if result.returncode != 0:
            return f"Python execution failed:\n{result.stderr}"
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        return f"Python execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Python sandbox error: {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

import ast

def validate_sandbox_security(code: str) -> bool:
    """Validate code using AST-based security checks."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    dangerous_imports = {
        'os', 'subprocess', 'sys', 'socket', 'shutil', 'ctypes',
        'pickle', 'marshal', 'builtins', 'importlib', '__builtin__'
    }
    dangerous_functions = {
        'eval', 'exec', '__import__', 'compile',
        'open', 'input', 'breakpoint', 'exit', 'quit'
    }
    dangerous_attributes = {
        '__subclasses__', '__class__', '__base__', '__mro__',
        '__globals__', '__code__', '__closure__', '__func__',
        '__self__', '__module__', '__dict__', '__bases__'
    }

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_imports:
                    print(f"[SECURITY] Blocked dangerous import: {alias.name}")
                    return False
                # Check submodules too
                top_level = alias.name.split('.')[0]
                if top_level in dangerous_imports:
                    print(f"[SECURITY] Blocked dangerous import: {alias.name}")
                    return False

        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            top_level = module.split('.')[0]
            if top_level in dangerous_imports:
                print(f"[SECURITY] Blocked dangerous import: {module}")
                return False

        # Check function calls
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in dangerous_functions:
                    print(f"[SECURITY] Blocked dangerous function: {func.id}")
                    return False
            elif isinstance(func, ast.Attribute):
                attr_name = func.attr
                if attr_name in dangerous_attributes:
                    print(f"[SECURITY] Blocked dangerous attribute: {attr_name}")
                    return False
                # Check for method calls like os.system, subprocess.run
                if isinstance(func.value, ast.Name):
                    if func.value.id in dangerous_imports and attr_name in ('system', 'run', 'call', 'popen', 'check_output', 'check_call'):
                        print(f"[SECURITY] Blocked dangerous call: {func.value.id}.{attr_name}")
                        return False

        # Check attribute access (e.g., getattr, setattr)
        if isinstance(node, ast.Attribute):
            if node.attr in dangerous_attributes:
                print(f"[SECURITY] Blocked dangerous attribute access: {node.attr}")
                return False

    return True
