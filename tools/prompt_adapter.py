#!/usr/bin/env python3
"""Prompt adapter for multi-provider compatibility.

Rewrites prompts to match provider-specific formatting and tool-calling conventions.
"""

import json
import re
from typing import Dict, Any, Optional

# Provider-specific prompt templates and tool-call formats
PROVIDER_PROFILES = {
    "openai": {
        "tool_call_format": "json",
        "system_prefix": "You are a helpful assistant.",
        "tool_instruction": "Use the provided tools to accomplish the task.",
        "max_tokens_default": 4096,
    },
    "anthropic": {
        "tool_call_format": "xml",
        "system_prefix": "You are Claude, a helpful assistant.",
        "tool_instruction": "Use the available tools when necessary.",
        "max_tokens_default": 4096,
    },
    "google": {
        "tool_call_format": "json",
        "system_prefix": "You are a helpful assistant.",
        "tool_instruction": "Use tools to complete the task.",
        "max_tokens_default": 8192,
    },
    "cohere": {
        "tool_call_format": "json",
        "system_prefix": "You are a helpful assistant.",
        "tool_instruction": "Use tools when needed.",
        "max_tokens_default": 4096,
    },
    "mistral": {
        "tool_call_format": "json",
        "system_prefix": "You are a helpful assistant.",
        "tool_instruction": "Use tools if available.",
        "max_tokens_default": 4096,
    },
}


def adapt_prompt(prompt: str, provider: str, tools: Optional[list] = None) -> Dict[str, Any]:
    """Adapt a prompt for a given provider.

    Args:
        prompt: The original prompt text.
        provider: Provider name (e.g., 'openai', 'anthropic').
        tools: Optional list of tool definitions.

    Returns:
        A dictionary with adapted prompt and metadata.
    """
    profile = PROVIDER_PROFILES.get(provider.lower(), PROVIDER_PROFILES["openai"])

    # Add provider-specific system prefix if not already present
    adapted_prompt = prompt
    if not adapted_prompt.startswith(profile["system_prefix"]):
        adapted_prompt = f"{profile['system_prefix']}\n\n{adapted_prompt}"

    # Add tool instruction if tools are provided and not already mentioned
    if tools and "tool" not in adapted_prompt.lower():
        adapted_prompt += f"\n\n{profile['tool_instruction']}"

    # Convert tool definitions to provider-specific format if needed
    adapted_tools = tools
    if tools and profile["tool_call_format"] == "xml":
        adapted_tools = _convert_tools_to_xml(tools)

    return {
        "prompt": adapted_prompt,
        "provider": provider,
        "tool_format": profile["tool_call_format"],
        "tools": adapted_tools,
        "max_tokens": profile["max_tokens_default"],
    }


def _convert_tools_to_xml(tools: list) -> str:
    """Convert tool definitions to XML format for Anthropic-style providers."""
    xml_parts = ["<tools>"]
    for tool in tools:
        name = tool.get("name", "unknown")
        description = tool.get("description", "")
        parameters = tool.get("parameters", {})
        xml_parts.append(f"  <tool name=\"{name}\">")
        xml_parts.append(f"    <description>{description}</description>")
        if parameters:
            xml_parts.append("    <parameters>")
            for prop, details in parameters.get("properties", {}).items():
                xml_parts.append(f"      <param name=\"{prop}\" type=\"{details.get('type', 'string')}\">")
                xml_parts.append(f"        {details.get('description', '')}")
                xml_parts.append("      </param>")
            xml_parts.append("    </parameters>")
        xml_parts.append("  </tool>")
    xml_parts.append("</tools>")
    return "\n".join(xml_parts)


def validate_adaptation(original: str, adapted: Dict[str, Any]) -> bool:
    """Basic validation that adaptation didn't break the prompt."""
    if not adapted.get("prompt"):
        return False
    if len(adapted["prompt"]) < len(original):
        return False
    return True


if __name__ == "__main__":
    # Simple self-test
    test_prompt = "What is the weather in Tokyo?"
    result = adapt_prompt(test_prompt, "anthropic", tools=[{"name": "get_weather", "description": "Get weather", "parameters": {"properties": {"location": {"type": "string"}}}}])
    print(json.dumps(result, indent=2))
    assert validate_adaptation(test_prompt, result)
    print("Self-test passed.")
