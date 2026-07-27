import json
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from tools.mcp_registry import _tool_registry, register_tool


class MCPServer:
    """Model Context Protocol server implementation.
    
    This server provides a JSON-RPC 2.0 interface for tool discovery and execution,
    following the MCP specification for agent-tool communication.
    """
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools from mcp_registry."""
        from tools.mcp_registry import (
            editor, load_tool, shell_exec,
            search_tools, inspect_tool, execute_tool
        )
        from tools.tool_catalogue_mcp import (
            search_tools_catalogue,
            get_tool_details,
            list_tool_categories,
            discover_tools_by_use_case,
        )

        default_tools = [
            editor, load_tool, shell_exec,
            search_tools, inspect_tool, execute_tool,
            search_tools_catalogue,
            get_tool_details,
            list_tool_categories,
            discover_tools_by_use_case,
        ]
        for tool_func in default_tools:
            self.register_tool(tool_func)
    
    def register_tool(self, tool_func: Any) -> bool:
        """Register a tool with the MCP server.
        
        Args:
            tool_func: A LangChain tool decorated with @tool
            
        Returns:
            True if registration successful, False otherwise
        """
        if hasattr(tool_func, "name"):
            self.tools[tool_func.name] = tool_func
            register_tool(tool_func)
            return True
        return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their schemas.
        
        Returns:
            List of tool schemas in MCP format
        """
        tool_list = []
        for name, tool_func in self.tools.items():
            schema = {
                "name": name,
                "description": tool_func.description if hasattr(tool_func, "description") else "",
                "inputSchema": self._get_tool_schema(tool_func)
            }
            tool_list.append(schema)
        return tool_list
    
    def _get_tool_schema(self, tool_func: Any) -> Dict[str, Any]:
        """Extract JSON schema from a LangChain tool.
        
        Args:
            tool_func: LangChain tool object
            
        Returns:
            JSON schema dictionary
        """
        if hasattr(tool_func, "args_schema"):
            return tool_func.args_schema.schema()
        return {"type": "object", "properties": {}}
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with provided arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Dictionary with 'result' or 'error' key
        """
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            tool_func = self.tools[tool_name]
            result = tool_func.invoke(arguments)
            return {"result": str(result)}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC 2.0 request.
        
        Args:
            request: JSON-RPC 2.0 request dictionary
            
        Returns:
            JSON-RPC 2.0 response dictionary
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "tools/list":
            result = self.list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = self.call_tool(tool_name, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": request_id
            }
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }


# Global MCP server instance
mcp_server = MCPServer()


def initialize_mcp_server():
    """Initialize and return the MCP server instance."""
    return mcp_server


def handle_mcp_request(request_json: str) -> str:
    """Handle an MCP request from a JSON string.
    
    Args:
        request_json: JSON string containing the request
        
    Returns:
        JSON string containing the response
    """
    try:
        request = json.loads(request_json)
        response = mcp_server.handle_request(request)
        return json.dumps(response)
    except json.JSONDecodeError:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None
        }
        return json.dumps(error_response)
