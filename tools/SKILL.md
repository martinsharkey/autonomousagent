# Agent Skills - Tool Creation Guide

## Overview
This document provides portable markdown instructions for agents to autonomously create, test, and register new tools at runtime.

## Tool Creation Process

### Step 1: Design the Tool Schema
Before writing code, define the tool's purpose and interface:
- **Name**: Descriptive, lowercase with underscores (e.g., `fetch_webpage`)
- **Description**: Clear, concise explanation of what the tool does
- **Parameters**: Input parameters with types and descriptions
- **Returns**: Expected output format

### Step 2: Write the Tool Code
Create a Python file with the following structure:

```python
from langchain_core.tools import tool

@tool
def your_tool_name(param1: str, param2: int = 10) -> str:
    """Clear description of what this tool does."""
    # Implementation here
    result = f"Processed {param1} with {param2}"
    return result
```

### Step 3: Test the Tool
Before registering, test the tool locally:
```python
result = your_tool_name("test", 5)
print(result)  # Verify output
```

### Step 4: Register the Tool
Use the `load_tool` function to dynamically register:
```python
load_tool("path/to/your_tool.py")
```

## Tool Design Patterns

### Pattern 1: File Operations
```python
@tool
def read_file(filepath: str) -> str:
    """Read contents of a file."""
    with open(filepath, 'r') as f:
        return f.read()
```

### Pattern 2: API Calls
```python
@tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    import httpx
    response = httpx.get(url)
    return response.text
```

### Pattern 3: Data Processing
```python
@tool
def process_data(data: str, operation: str = "uppercase") -> str:
    """Process data with specified operation."""
    if operation == "uppercase":
        return data.upper()
    elif operation == "lowercase":
        return data.lower()
    return data
```

## Progressive Tool Discovery

### Layer 1: Catalog (Search)
Use `search_tools(query)` to find tools by name or description.
Returns: List of tool names and brief descriptions.

### Layer 2: Inspect (Schema)
Use `inspect_tool(tool_name)` to get full JSON schema.
Returns: Complete parameter definitions and usage examples.

### Layer 3: Execute
Use `execute_tool(tool_name, **kwargs)` to invoke the tool.
Returns: Tool execution result.

## Code Mode (Programmatic Calling)

Instead of sequential tool calls, write a single script:

```python
# Agent writes this script
from tools.mcp_registry import editor, load_tool, shell_exec

# Create a new tool
tool_code = '''
from langchain_core.tools import tool

@tool
def calculate_sum(a: int, b: int) -> str:
    """Calculate sum of two numbers."""
    return str(a + b)
'''

editor("tools/calculate_sum.py", tool_code)
load_tool("tools/calculate_sum.py")
result = execute_tool("calculate_sum", a=5, b=3)
print(f"Result: {result}")
```

The sandbox executes the script and returns only the final `print()` output to the LLM, saving thousands of tokens.

## Best Practices

1. **Keep Tools Focused**: Each tool should do one thing well
2. **Clear Descriptions**: Write descriptions that help agents understand when to use the tool
3. **Error Handling**: Include try-catch blocks for robustness
4. **Type Hints**: Use Python type hints for better schema generation
5. **Documentation**: Add docstrings explaining parameters and return values
6. **Testing**: Test tools before registering them
7. **Security**: Never execute untrusted code without sandboxing

## Example: Creating a Web Scraper Tool

```python
from langchain_core.tools import tool
import httpx

@tool
def scrape_webpage(url: str, selector: str = "body") -> str:
    """Scrape content from a webpage using CSS selector."""
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        # Simplified - in production use BeautifulSoup
        return response.text[:1000]  # Return first 1000 chars
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"
```

## Troubleshooting

### Tool Not Found
- Verify the tool was registered with `load_tool()`
- Check that the function has the `@tool` decorator
- Ensure the file path is correct

### Schema Generation Failed
- Add type hints to all parameters
- Ensure the function has a docstring
- Check that parameter types are JSON-serializable

### Execution Errors
- Test the tool function directly before registering
- Add error handling with try-catch blocks
- Verify all imports are available in the execution environment
