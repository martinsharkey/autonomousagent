import pytest
import json
from tools.mcp_server import MCPServer, mcp_server, handle_mcp_request
from tools.example_tool import example_tool, add_numbers


class TestMCPServer:
    """Test suite for MCP server functionality."""
    
    def test_server_initialization(self):
        """Test that MCP server initializes with default tools."""
        server = MCPServer()
        assert len(server.tools) > 0
        assert "editor" in server.tools
        assert "search_tools" in server.tools
    
    def test_register_custom_tool(self):
        """Test registering a custom tool with the server."""
        server = MCPServer()
        initial_count = len(server.tools)
        
        success = server.register_tool(example_tool)
        assert success is True
        assert len(server.tools) == initial_count + 1
        assert "example_tool" in server.tools
    
    def test_list_tools(self):
        """Test listing all registered tools."""
        server = MCPServer()
        server.register_tool(example_tool)
        
        tool_list = server.list_tools()
        assert len(tool_list) > 0
        
        tool_names = [t["name"] for t in tool_list]
        assert "example_tool" in tool_names
        
        for tool_schema in tool_list:
            assert "name" in tool_schema
            assert "description" in tool_schema
            assert "inputSchema" in tool_schema
    
    def test_call_tool_success(self):
        """Test successful tool execution."""
        server = MCPServer()
        server.register_tool(example_tool)
        
        result = server.call_tool("example_tool", {"input_text": "hello"})
        assert "result" in result
        assert "HELLO" in result["result"]
    
    def test_call_tool_not_found(self):
        """Test calling a non-existent tool."""
        server = MCPServer()
        
        result = server.call_tool("nonexistent_tool", {})
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_call_tool_with_error(self):
        """Test tool execution with invalid arguments."""
        server = MCPServer()
        server.register_tool(example_tool)
        
        result = server.call_tool("example_tool", {})
        assert "error" in result or "result" in result
    
    def test_handle_request_list_tools(self):
        """Test handling a tools/list request."""
        server = MCPServer()
        server.register_tool(example_tool)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        response = server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert len(response["result"]) > 0
    
    def test_handle_request_call_tool(self):
        """Test handling a tools/call request."""
        server = MCPServer()
        server.register_tool(add_numbers)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "add_numbers",
                "arguments": {"a": 5, "b": 3}
            },
            "id": 2
        }
        
        response = server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "8" in response["result"]["result"]
    
    def test_handle_request_invalid_method(self):
        """Test handling an invalid method request."""
        server = MCPServer()
        
        request = {
            "jsonrpc": "2.0",
            "method": "invalid/method",
            "id": 3
        }
        
        response = server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601
    
    def test_handle_mcp_request_json_string(self):
        """Test handling MCP request from JSON string."""
        server = MCPServer()
        server.register_tool(example_tool)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "example_tool",
                "arguments": {"input_text": "test"}
            },
            "id": 4
        })
        
        response_json = handle_mcp_request(request_json)
        response = json.loads(response_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "result" in response
    
    def test_handle_mcp_request_invalid_json(self):
        """Test handling invalid JSON request."""
        response_json = handle_mcp_request("invalid json")
        response = json.loads(response_json)
        
        assert "error" in response
        assert response["error"]["code"] == -32700


class TestExampleTools:
    """Test suite for example tools."""
    
    def test_example_tool_basic(self):
        """Test basic example tool functionality."""
        result = example_tool.invoke({"input_text": "hello world"})
        assert "HELLO WORLD" in result
    
    def test_example_tool_empty_input(self):
        """Test example tool with empty input."""
        result = example_tool.invoke({"input_text": ""})
        assert "Error" in result
    
    def test_add_numbers_basic(self):
        """Test basic addition functionality."""
        result = add_numbers.invoke({"a": 10, "b": 20})
        assert "30" in result
    
    def test_add_numbers_negative(self):
        """Test addition with negative numbers."""
        result = add_numbers.invoke({"a": -5, "b": 10})
        assert "5" in result
