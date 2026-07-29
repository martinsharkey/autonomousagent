#!/usr/bin/env python3
"""Multi-provider model compatibility test tool.

Validates prompt/response format across providers and logs mismatches
for failover tuning. Supports Pillar 3 - Model Agnosticism.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Expected response schema keys per provider (example)
PROVIDER_SCHEMAS = {
    "openai": {"required": ["choices", "usage"], "optional": ["id", "object", "created"]},
    "anthropic": {"required": ["content", "model"], "optional": ["stop_reason", "usage"]},
    "google": {"required": ["candidates"], "optional": ["usageMetadata"]},
    "cohere": {"required": ["text", "generation_id"], "optional": ["finish_reason"]},
}

# Test prompts covering different use cases
TEST_PROMPTS = [
    "Hello, how are you?",
    "Explain quantum computing in one sentence.",
    "What is 2+2?",
    "Write a short poem about AI.",
]


def validate_response_format(provider: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that a response matches the expected schema for the provider."""
    schema = PROVIDER_SCHEMAS.get(provider, {})
    required = schema.get("required", [])
    missing = [key for key in required if key not in response]
    extra = [key for key in response if key not in required and key not in schema.get("optional", [])]
    return {
        "provider": provider,
        "valid": len(missing) == 0,
        "missing_keys": missing,
        "unexpected_keys": extra,
        "response_keys": list(response.keys()),
    }


def run_compatibility_test(provider: str, prompt: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single compatibility test for a provider-prompt pair."""
    start = time.time()
    validation = validate_response_format(provider, response)
    elapsed = time.time() - start
    return {
        "provider": provider,
        "prompt": prompt[:50],
        "valid": validation["valid"],
        "validation_details": validation,
        "response_time": elapsed,
        "timestamp": time.time(),
    }


def run_all_tests(provider_responses: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Run compatibility tests for multiple providers and prompts.

    Args:
        provider_responses: Dict mapping provider name to list of response dicts.
            Each response dict should have 'prompt' and 'response' keys.

    Returns:
        List of test result dicts.
    """
    results = []
    for provider, responses in provider_responses.items():
        for item in responses:
            prompt = item.get("prompt", "")
            response = item.get("response", {})
            result = run_compatibility_test(provider, prompt, response)
            results.append(result)
            if not result["valid"]:
                logger.warning(
                    f"Compatibility mismatch for {provider}: missing {result['validation_details']['missing_keys']}"
                )
    return results


def log_mismatches(results: List[Dict[str, Any]], log_file: str = "compatibility_mismatches.log"):
    """Log mismatches to a file for analysis and failover tuning."""
    mismatches = [r for r in results if not r["valid"]]
    if mismatches:
        with open(log_file, "a") as f:
            for m in mismatches:
                f.write(json.dumps(m) + "\n")
        logger.info(f"Logged {len(mismatches)} mismatches to {log_file}")
    else:
        logger.info("No mismatches found.")


if __name__ == "__main__":
    # Example usage
    sample_responses = {
        "openai": [
            {
                "prompt": "Hello",
                "response": {
                    "choices": [{"text": "Hi there!"}],
                    "usage": {"total_tokens": 5},
                },
            }
        ],
        "anthropic": [
            {
                "prompt": "Hello",
                "response": {
                    "content": [{"text": "Hello!"}],
                    "model": "claude-3",
                },
            }
        ],
    }
    results = run_all_tests(sample_responses)
    log_mismatches(results)
    print(json.dumps(results, indent=2))
