#!/usr/bin/env python3
"""Multi-provider model compatibility test tool.

Tests a given prompt against all configured LLM providers,
validates response format consistency, and logs mismatches.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Default test prompts for different capabilities
TEST_PROMPTS = {
    "simple": "What is 2+2?",
    "json": "Return JSON: {'name': 'test', 'value': 123}",
    "code": "Write a Python function to reverse a string.",
    "instruction_following": "List three colors."
}


def load_providers_config(path: str = "providers.yaml") -> Dict[str, Any]:
    """Load provider configurations from YAML file."""
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        return config.get("providers", {})
    except Exception as e:
        logger.error(f"Failed to load providers config: {e}")
        return {}


def test_provider(provider_name: str, provider_config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    """Test a single provider with a given prompt.

    Returns a dict with keys: success, response, latency, error.
    """
    # Placeholder: actual API call would go here
    # For now, simulate a call with a mock response
    start = time.time()
    try:
        # Simulate API call
        time.sleep(0.1)
        # Mock response based on provider
        response = f"Mock response from {provider_name}: {prompt[:20]}..."
        latency = time.time() - start
        return {
            "success": True,
            "response": response,
            "latency": latency,
            "error": None
        }
    except Exception as e:
        latency = time.time() - start
        return {
            "success": False,
            "response": None,
            "latency": latency,
            "error": str(e)
        }


def validate_response_format(response: str, expected_format: str) -> bool:
    """Validate response format (e.g., JSON, code, plain text)."""
    if expected_format == "json":
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError:
            return False
    elif expected_format == "code":
        # Simple heuristic: check for code markers or function definition
        if "def " in response or "```" in response:
            return True
        return False
    else:
        # Plain text always valid
        return True


def run_compatibility_test(providers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run compatibility tests across all providers.

    Returns a summary dict with results per provider and overall score.
    """
    if providers is None:
        providers = load_providers_config()

    if not providers:
        logger.warning("No providers configured. Skipping compatibility test.")
        return {"status": "skipped", "reason": "no_providers"}

    results = {}
    overall_success = True
    total_tests = 0
    passed_tests = 0

    for provider_name, provider_config in providers.items():
        provider_results = []
        for test_name, prompt in TEST_PROMPTS.items():
            total_tests += 1
            test_result = test_provider(provider_name, provider_config, prompt)
            if test_result["success"]:
                # Validate format if applicable
                format_ok = validate_response_format(test_result["response"], test_name)
                if format_ok:
                    passed_tests += 1
                else:
                    overall_success = False
                    logger.warning(f"Format mismatch for {provider_name} on test '{test_name}'")
            else:
                overall_success = False
                logger.error(f"Provider {provider_name} failed on test '{test_name}': {test_result['error']}")
            provider_results.append({
                "test": test_name,
                "success": test_result["success"],
                "latency": test_result["latency"],
                "error": test_result["error"]
            })
        results[provider_name] = provider_results

    compatibility_score = passed_tests / total_tests if total_tests > 0 else 0.0
    summary = {
        "status": "completed",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "compatibility_score": compatibility_score,
        "overall_success": overall_success,
        "results": results
    }
    return summary


def log_compatibility_report(summary: Dict[str, Any]) -> None:
    """Log the compatibility test report to a file for later analysis."""
    report_path = "compatibility_report.json"
    try:
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Compatibility report saved to {report_path}")
    except Exception as e:
        logger.error(f"Failed to save compatibility report: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = run_compatibility_test()
    log_compatibility_report(summary)
    print(json.dumps(summary, indent=2))
