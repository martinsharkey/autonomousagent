import subprocess
import tempfile
import os
import uuid
import json
from typing import Optional
from pathlib import Path

SANDBOX_TIMEOUT = 30
SANDBOX_MEMORY_LIMIT = "512m"
SANDBOX_CPU_LIMIT = "1.0"
SANDBOX_PIDS_LIMIT = "64"
SANDBOX_IMAGE = "python:3.11-slim"

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

def execute_in_sandbox(command: str, timeout: int = SANDBOX_TIMEOUT) -> str:
    if _is_docker_available():
        return _execute_in_docker_sandbox(command, timeout)
    else:
        return _execute_in_subprocess_sandbox(command, timeout)

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
