from typing import List, Dict
import json
from tools.mcp_registry import _tool_registry

def search_available_tools(query: str) -> str:
    """Layer 1: Search tools by name or description, return names and brief descriptions only."""
    results = []
    query_lower = query.lower()

    for tool_name, tool_func in _tool_registry.items():
        if query_lower in tool_name.lower():
            description = tool_func.description if hasattr(tool_func, "description") else "No description"
            results.append({
                "name": tool_name,
                "description": description[:100]
            })

    if not results:
        return "No tools found matching your query."

    output = "Available tools:\n"
    for tool_info in results:
        output += f"- {tool_info['name']}: {tool_info['description']}\n"

    return output

def get_tool_schema(tool_name: str) -> str:
    """Layer 2: Get full JSON schema for a specific tool."""
    if tool_name not in _tool_registry:
        return f"Error: Tool {tool_name} not found"

    tool_func = _tool_registry[tool_name]

    schema = {
        "name": tool_name,
        "description": tool_func.description if hasattr(tool_func, "description") else "No description",
        "parameters": {}
    }

    if hasattr(tool_func, "args_schema"):
        schema["parameters"] = tool_func.args_schema.schema()

    return json.dumps(schema, indent=2)

def get_all_tool_names() -> List[str]:
    """Get list of all registered tool names."""
    return list(_tool_registry.keys())

def tool_exists(tool_name: str) -> bool:
    """Check if a tool exists in the registry."""
    return tool_name in _tool_registry
