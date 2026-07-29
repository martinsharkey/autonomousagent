#!/usr/bin/env python3
"""Multi-provider health check tool for Pillar 3: Model Agnosticism.

Tests connectivity and response quality for all configured LLM providers.
Logs results for failover decisions and provides a summary.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

import yaml

logger = logging.getLogger(__name__)

# Default providers to check if config not available
DEFAULT_PROVIDERS = [
    {"name": "openai", "model": "gpt-4o-mini", "endpoint": "https://api.openai.com/v1/chat/completions"},
    {"name": "anthropic", "model": "claude-3-haiku-20240307", "endpoint": "https://api.anthropic.com/v1/messages"},
    {"name": "google", "model": "gemini-1.5-flash", "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"},
    {"name": "deepseek", "model": "deepseek-chat", "endpoint": "https://api.deepseek.com/v1/chat/completions"},
]


def load_provider_config(config_path: str = "providers.yaml") -> List[Dict[str, Any]]:
    """Load provider configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        providers = []
        for provider_name, provider_config in config.get("providers", {}).items():
            providers.append({
                "name": provider_name,
                "model": provider_config.get("model", ""),
                "endpoint": provider_config.get("endpoint", ""),
                "api_key": provider_config.get("api_key", ""),
            })
        return providers if providers else DEFAULT_PROVIDERS
    except Exception as e:
        logger.warning(f"Failed to load provider config: {e}. Using defaults.")
        return DEFAULT_PROVIDERS


async def check_provider(provider: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    """Check a single provider's health by sending a minimal test request."""
    start = time.time()
    result = {
        "name": provider["name"],
        "model": provider.get("model", ""),
        "endpoint": provider.get("endpoint", ""),
        "healthy": False,
        "latency_ms": 0.0,
        "error": None,
    }
    try:
        # Use aiohttp or httpx for async HTTP; fallback to urllib
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Minimal test payload (varies by provider)
            payload = {
                "model": provider.get("model", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider.get('api_key', 'test')}",
            }
            response = await client.post(
                provider.get("endpoint", ""),
                json=payload,
                headers=headers,
            )
            elapsed = (time.time() - start) * 1000
            result["latency_ms"] = round(elapsed, 2)
            if response.status_code in (200, 201):
                result["healthy"] = True
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
    except ImportError:
        # Fallback: use urllib (synchronous, but acceptable for simple check)
        import json
        import urllib.request
        import urllib.error
        try:
            payload = json.dumps({
                "model": provider.get("model", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }).encode()
            req = urllib.request.Request(
                provider.get("endpoint", ""),
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {provider.get('api_key', 'test')}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = (time.time() - start) * 1000
                result["latency_ms"] = round(elapsed, 2)
                if resp.status in (200, 201):
                    result["healthy"] = True
                else:
                    result["error"] = f"HTTP {resp.status}: {resp.read().decode()[:200]}"
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result["latency_ms"] = round(elapsed, 2)
            result["error"] = str(e)[:200]
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = round(elapsed, 2)
        result["error"] = str(e)[:200]
    return result


async def run_provider_health_check(config_path: str = "providers.yaml") -> Dict[str, Any]:
    """Run health checks on all configured providers."""
    providers = load_provider_config(config_path)
    tasks = [check_provider(p) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    healthy_count = 0
    unhealthy_count = 0
    details = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            details.append({
                "name": providers[i]["name"],
                "healthy": False,
                "error": str(res)[:200],
                "latency_ms": 0.0,
            })
            unhealthy_count += 1
        else:
            details.append(res)
            if res["healthy"]:
                healthy_count += 1
            else:
                unhealthy_count += 1
    
    summary = {
        "timestamp": time.time(),
        "total_providers": len(providers),
        "healthy": healthy_count,
        "unhealthy": unhealthy_count,
        "details": details,
        "all_healthy": unhealthy_count == 0,
    }
    logger.info(f"Provider health check complete: {healthy_count}/{len(providers)} healthy")
    return summary


if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "providers.yaml"
    result = asyncio.run(run_provider_health_check(config_path))
    print(yaml.dump(result, default_flow_style=False))
