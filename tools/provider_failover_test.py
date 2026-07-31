#!/usr/bin/env python3
"""Tool to test provider failover by simulating outages and validating router behavior."""

import asyncio
import json
import sys
from typing import Any, Dict, List

# Mock imports for standalone testing; in production, these would be actual modules.
try:
    from core.api_router import APIRouter
except ImportError:
    APIRouter = None

try:
    from core.model_check import check_model
except ImportError:
    check_model = None

async def simulate_provider_failure(provider_name: str, duration: float = 0.1) -> None:
    """Simulate a provider outage by sleeping and raising an exception."""
    await asyncio.sleep(duration)
    raise ConnectionError(f"Simulated outage for {provider_name}")

async def test_failover(router: Any, providers: List[str], test_prompt: str = "Hello") -> Dict[str, Any]:
    """Run a failover test across providers, simulating failures for each."""
    results = {}
    for provider in providers:
        # Temporarily mark provider as down
        original_status = router.get_provider_status(provider) if hasattr(router, 'get_provider_status') else None
        if hasattr(router, 'set_provider_status'):
            router.set_provider_status(provider, False)
        try:
            # Attempt to get a response; should failover to another provider
            response = await router.complete(test_prompt, preferred_provider=provider)
            results[provider] = {
                "success": True,
                "used_provider": response.get("provider", "unknown"),
                "error": None
            }
        except Exception as e:
            results[provider] = {
                "success": False,
                "used_provider": None,
                "error": str(e)
            }
        finally:
            # Restore provider status
            if hasattr(router, 'set_provider_status') and original_status is not None:
                router.set_provider_status(provider, original_status)
    return results

async def main() -> None:
    """Main entry point for the failover test tool."""
    if APIRouter is None:
        print(json.dumps({"error": "APIRouter not available"}))
        return

    router = APIRouter()
    providers = router.get_available_providers() if hasattr(router, 'get_available_providers') else []
    if not providers:
        print(json.dumps({"error": "No providers configured"}))
        return

    results = await test_failover(router, providers)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
