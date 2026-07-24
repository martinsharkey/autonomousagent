from typing import Dict, Any
import subprocess
import tempfile
import os

def execute_code_mode(script_content: str, language: str = "python") -> str:
    """Execute a script in code mode - agent writes script, sandbox executes, returns only final output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as tmp:
        tmp.write(script_content)
        tmp_path = tmp.name

    try:
        if language == "python":
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
        elif language == "javascript":
            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            return f"Unsupported language: {language}"

        if result.returncode != 0:
            return f"Script execution failed:\n{result.stderr}"

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return "Script execution timed out (30s limit)"
    except Exception as e:
        return f"Execution error: {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def generate_code_mode_prompt(task_description: str) -> str:
    """Generate prompt for code mode - instructs agent to write a single script."""
    return f"""
You are in CODE MODE. Instead of making multiple tool calls, write a single Python or JavaScript script that accomplishes the task.

Task: {task_description}

Requirements:
1. Write a complete, executable script
2. The script should use the available tools (editor, load_tool, shell_exec, search_tools, inspect_tool, execute_tool)
3. Include print statements or console.log to output results
4. The script will be executed in a sandbox and only the final output will be returned

Write your script below:
"""
