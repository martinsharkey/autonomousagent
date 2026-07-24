from langchain_core.tools import tool
from typing import Dict, List
import importlib.util
import sys
import os

_tool_registry: Dict[str, callable] = {}

@tool
def editor(filepath: str, code: str) -> str:
    """Creates and modifies tool code files locally."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, "w") as f:
        f.write(code)
    return f"Saved code to {filepath}"

@tool
def load_tool(filepath: str) -> str:
    """Dynamically loads a newly written Python tool at runtime."""
    if not os.path.exists(filepath):
        return f"Error: File {filepath} not found"

    module_name = os.path.basename(filepath).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if callable(attr) and hasattr(attr, "name"):
            _tool_registry[attr.name] = attr
            return f"Tool {attr.name} registered and ready for execution."

    return f"Tool {filepath} loaded but no @tool decorated functions found."

@tool
def shell_exec(command: str) -> str:
    """Executes shell commands for compiling/testing code inside an isolated environment."""
    from core.sandbox import execute_in_sandbox
    return execute_in_sandbox(command)

@tool
def search_tools(query: str) -> str:
    """Layer 1: Search available tools by name or description."""
    from core.tool_discovery import search_available_tools
    return search_available_tools(query)

@tool
def inspect_tool(tool_name: str) -> str:
    """Layer 2: Get full JSON schema for a specific tool."""
    from core.tool_discovery import get_tool_schema
    return get_tool_schema(tool_name)

@tool
def execute_tool(tool_name: str, **kwargs) -> str:
    """Layer 3: Execute a tool with provided arguments."""
    if tool_name not in _tool_registry:
        return f"Error: Tool {tool_name} not found in registry"
    tool_func = _tool_registry[tool_name]
    try:
        result = tool_func.invoke(kwargs)
        return str(result)
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

def register_tool(tool_func: callable):
    """Register a tool function in the registry."""
    if hasattr(tool_func, "name"):
        _tool_registry[tool_func.name] = tool_func
        return True
    return False

def get_registered_tools() -> List[str]:
    """Get list of all registered tool names."""
    return list(_tool_registry.keys())

register_tool(editor)
register_tool(load_tool)
register_tool(shell_exec)
register_tool(search_tools)
register_tool(inspect_tool)
register_tool(execute_tool)
