from langchain_core.tools import tool
from typing import Dict, List, Optional, Tuple
import importlib.util
import sys
import os
import json
import ast

from tools.code_validator import validate_tool_code

_tool_registry: Dict[str, callable] = {}
MCP_REGISTRY: Dict[str, callable] = _tool_registry
_pending_tools: Dict[str, dict] = {}
_approved_tools: Dict[str, str] = {}

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
def load_tool(filepath: str, auto_approve: bool = False) -> str:
    """Dynamically loads a newly written Python tool at runtime with security validation."""
    if not os.path.exists(filepath):
        return f"Error: File {filepath} not found"

    with open(filepath, 'r') as f:
        code = f.read()

    is_safe, violations = validate_tool_code(code)
    if not is_safe:
        violation_msgs = [f"  - {v}" for v in violations]
        return f"Security validation failed for {filepath}:\n" + "\n".join(violation_msgs)

    tool_id = os.path.basename(filepath).replace(".py", "")
    
    if not auto_approve:
        _pending_tools[tool_id] = {
            'filepath': filepath,
            'code': code,
            'schema': _extract_schema_without_execution(code)
        }
        return f"Tool '{tool_id}' passed security validation and is pending approval. Use approve_tool('{tool_id}') to activate."
    
    return _load_and_register_tool(filepath, tool_id)

def _extract_schema_without_execution(code: str) -> dict:
    """Extract tool schema from code without executing it."""
    try:
        tree = ast.parse(code)
        tools = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                        tool_info = {
                            'name': node.name,
                            'docstring': ast.get_docstring(node) or "",
                            'parameters': []
                        }
                        
                        for arg in node.args.args:
                            if arg.arg != 'self':
                                tool_info['parameters'].append({
                                    'name': arg.arg,
                                    'annotation': ast.unparse(arg.annotation) if arg.annotation else 'Any'
                                })
                        
                        tools.append(tool_info)
        
        return {'tools': tools}
    except Exception as e:
        return {'error': str(e)}

def _load_and_register_tool(filepath: str, tool_id: str) -> str:
    """Load and register a tool after approval."""
    try:
        module_name = tool_id
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        registered = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "name"):
                _tool_registry[attr.name] = attr
                _approved_tools[attr.name] = filepath
                registered.append(attr.name)
        
        if registered:
            return f"Tool(s) {', '.join(registered)} registered and ready for execution."
        return f"Tool {filepath} loaded but no @tool decorated functions found."
    except Exception as e:
        return f"Error loading tool: {str(e)}"

@tool
def approve_tool(tool_id: str) -> str:
    """Approve and activate a pending tool."""
    if tool_id not in _pending_tools:
        return f"Error: No pending tool with id '{tool_id}'"
    
    tool_info = _pending_tools[tool_id]
    result = _load_and_register_tool(tool_info['filepath'], tool_id)
    del _pending_tools[tool_id]
    return result

@tool
def list_pending_tools() -> str:
    """List all tools pending approval."""
    if not _pending_tools:
        return "No tools pending approval."
    
    result = "Tools pending approval:\n"
    for tool_id, info in _pending_tools.items():
        result += f"\n{tool_id}:\n"
        result += f"  File: {info['filepath']}\n"
        if 'schema' in info:
            result += f"  Schema: {json.dumps(info['schema'], indent=2)}\n"
    return result

@tool
def list_approved_tools() -> str:
    """List all approved and active tools."""
    if not _approved_tools:
        return "No tools currently approved."
    
    result = "Approved tools:\n"
    for tool_name, filepath in _approved_tools.items():
        result += f"  - {tool_name}: {filepath}\n"
    return result

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
register_tool(approve_tool)
register_tool(list_pending_tools)
register_tool(list_approved_tools)
register_tool(shell_exec)
register_tool(search_tools)
register_tool(inspect_tool)
register_tool(execute_tool)
