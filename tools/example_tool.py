from langchain_core.tools import tool


@tool
def example_tool(input_text: str) -> str:
    """Example tool that processes input text and returns a transformed result.
    
    This is a minimal example tool demonstrating the pattern for creating
    tools that can be registered with the MCP server.
    
    Args:
        input_text: The text to process
        
    Returns:
        Processed text with transformation applied
    """
    if not input_text:
        return "Error: Empty input provided"
    
    processed = input_text.strip().upper()
    return f"Processed: {processed}"


@tool
def add_numbers(a: int, b: int) -> str:
    """Example tool that adds two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        String representation of the sum
    """
    result = a + b
    return f"Sum: {result}"
