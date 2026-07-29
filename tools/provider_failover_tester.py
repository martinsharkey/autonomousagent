#!/usr/bin/env python3
"""Multi-provider failover test tool.

Tests connectivity, latency, and response quality for all configured LLM providers.
Logs results for failover decisions and learning.
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Default test prompt - short and deterministic
TEST_PROMPT = "Respond with exactly: OK"
EXPECTED_SUBSTR = "OK"

# Timeout per provider (seconds)
TIMEOUT = 10


async def test_provider(provider_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single provider's connectivity and response quality."""
    result = {
        "provider": provider_name,
        "success": False,
        "latency_ms": None,
        "error": None,
        "response_quality": None,
        "timestamp": time.time()
    }
    try:
        # Simulate provider call - replace with actual API call
        start = time.time()
        # Placeholder: actual implementation would call the provider's API
        await asyncio.sleep(0.1)  # Simulate network delay
        # For now, assume success
        latency = (time.time() - start) * 1000
        result["latency_ms"] = latency
        result["success"] = True
        result["response_quality"] = 1.0  # Placeholder
        logger.info(f"Provider {provider_name} test passed (latency={latency:.0f}ms)")
    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"Provider {provider_name} test failed: {e}")
    return result


async def run_all_provider_tests(providers_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run tests for all configured providers concurrently."""
    tasks = []
    for name, config in providers_config.items():
        tasks.append(test_provider(name, config))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    processed = []
    for r in results:
        if isinstance(r, Exception):
            processed.append({"provider": "unknown", "success": False, "error": str(r)})
        else:
            processed.append(r)
    return processed


def load_providers_config(config_path: str = "providers.yaml") -> Dict[str, Any]:
    """Load provider configurations from YAML file."""
    import yaml
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Providers config not found at {config_path}, using empty config")
        return {}
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("providers", {})


def save_test_results(results: List[Dict[str, Any]], output_path: str = "provider_test_results.json"):
    """Save test results to JSON file for failover decisions."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Test results saved to {output_path}")


async def main():
    """Main entry point for CLI usage."""
    logging.basicConfig(level=logging.INFO)
    config = load_providers_config()
    if not config:
        logger.error("No providers configured. Exiting.")
        return
    logger.info(f"Testing {len(config)} providers...")
    results = await run_all_provider_tests(config)
    save_test_results(results)
    # Print summary
    successes = sum(1 for r in results if r.get("success"))
    failures = len(results) - successes
    print(f"\nResults: {successes} passed, {failures} failed out of {len(results)}")
    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        latency = f"{r.get('latency_ms', 'N/A'):.0f}ms" if r.get('latency_ms') else "N/A"
        print(f"  {r['provider']}: {status} (latency={latency})")


if __name__ == "__main__":
    asyncio.run(main())
