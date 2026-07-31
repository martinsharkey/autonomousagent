#!/usr/bin/env python3
"""Provider compatibility tester: validates prompt/response formats and tool-calling behavior across LLM providers."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

# Assume a provider interface similar to core/api_router.py
# This tool is standalone and can be invoked by the agent.

logger = logging.getLogger(__name__)

# Test cases: each defines a prompt, expected response format, and optional tool call test
TEST_CASES = [
    {
        "name": "basic_completion",
        "prompt": "Reply with exactly: OK",
        "expected_substring": "OK",
        "tool_call": False,
    },
    {
        "name": "json_response",
        "prompt": "Return a JSON object with key 'status' set to 'success'.",
        "expected_json": {"status": "success"},
        "tool_call": False,
    },
    {
        "name": "tool_call_format",
        "prompt": "Use the available tool 'get_weather' to get weather for Paris. Return the tool call.",
        "expected_tool_call": {"name": "get_weather", "arguments": {"location": "Paris"}},
        "tool_call": True,
    },
]

async def test_provider(provider_name: str, client: Any) -> Dict[str, Any]:
    """Run all test cases against a provider and return results."""
    results = {"provider": provider_name, "tests": [], "overall_pass": True}
    for test in TEST_CASES:
        start = time.time()
        try:
            # This is a placeholder; actual implementation depends on provider interface
            # For example, call client.complete(prompt, tools=...) or similar
            response = await client.complete(
                prompt=test["prompt"],
                tools=[{"name": "get_weather", "description": "Get weather", "parameters": {"location": {"type": "string"}}}] if test["tool_call"] else None,
            )
            latency = time.time() - start
            passed = _evaluate_response(response, test)
            results["tests"].append({
                "name": test["name"],
                "passed": passed,
                "latency_ms": round(latency * 1000, 2),
                "response_preview": str(response)[:200],
            })
            if not passed:
                results["overall_pass"] = False
        except Exception as e:
            latency = time.time() - start
            results["tests"].append({
                "name": test["name"],
                "passed": False,
                "latency_ms": round(latency * 1000, 2),
                "error": str(e),
            })
            results["overall_pass"] = False
    return results

def _evaluate_response(response: Any, test: Dict[str, Any]) -> bool:
    """Check if response meets test expectations."""
    if test.get("expected_substring"):
        return test["expected_substring"] in str(response)
    if test.get("expected_json"):
        try:
            data = json.loads(response) if isinstance(response, str) else response
            return data == test["expected_json"]
        except Exception:
            return False
    if test.get("expected_tool_call"):
        # Check if response contains a tool call with matching name and args
        # This is a simplified check; actual parsing depends on provider format
        return _check_tool_call(response, test["expected_tool_call"])
    return False

def _check_tool_call(response: Any, expected: Dict[str, Any]) -> bool:
    """Heuristic check for tool call presence."""
    text = str(response).lower()
    return expected["name"].lower() in text and "paris" in text

async def run_compatibility_tests(providers: Dict[str, Any]) -> Dict[str, Any]:
    """Run tests for all configured providers."""
    report = {"timestamp": time.time(), "results": []}
    for name, client in providers.items():
        logger.info("Testing provider %s", name)
        result = await test_provider(name, client)
        report["results"].append(result)
    return report

def generate_report(report: Dict[str, Any]) -> str:
    """Format report as JSON string for easy consumption."""
    return json.dumps(report, indent=2)

if __name__ == "__main__":
    # Example usage: load providers from config and run
    # This is a stub; actual integration would import from core.api_router
    async def main():
        # Placeholder providers dict
        providers = {}
        report = await run_compatibility_tests(providers)
        print(generate_report(report))
    asyncio.run(main())
