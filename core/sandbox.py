import subprocess
import tempfile
import os
from typing import Optional

SANDBOX_TIMEOUT = 30
SANDBOX_MEMORY_LIMIT = "512m"

def execute_in_sandbox(command: str, timeout: int = SANDBOX_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
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

def validate_sandbox_security(code: str) -> bool:
    dangerous_patterns = [
        "__subclasses__",
        "__class__",
        "__base__",
        "os.system",
        "subprocess.call",
        "eval(",
        "exec(",
        "__import__"
    ]
    
    for pattern in dangerous_patterns:
        if pattern in code:
            print(f"[SECURITY] Blocked dangerous pattern: {pattern}")
            return False
    
    return True
