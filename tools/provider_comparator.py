#!/usr/bin/env python3
"""Multi-provider response comparison tool for Pillar 3."""
import asyncio
import json
import time
from typing import Dict, List, Optional
from core.api_router import router

async def compare_providers(prompt: str, providers: Optional[List[str]] = None) -> Dict:
    """Send prompt to all configured providers and return comparison."""
    if providers is None:
        providers = list(router.providers.keys())
    results = {}
    for provider in providers:
        start = time.time()
        try:
            response = await router.route(prompt, provider=provider)
            latency = time.time() - start
            results[provider] = {
                "response": response,
                "latency": round(latency, 3),
                "error": None
            }
        except Exception as e:
            latency = time.time() - start
            results[provider] = {
                "response": None,
                "latency": round(latency, 3),
                "error": str(e)
            }
    return results

async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: provider_comparator.py <prompt> [provider1 provider2 ...]")
        sys.exit(1)
    prompt = sys.argv[1]
    providers = sys.argv[2:] if len(sys.argv) > 2 else None
    results = await compare_providers(prompt, providers)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
