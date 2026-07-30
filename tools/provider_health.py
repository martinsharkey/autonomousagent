import asyncio
import logging
import time
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# In-memory store for provider health status
_provider_health: Dict[str, dict] = {}

async def check_provider_health(provider_name: str, endpoint: str, api_key: str, timeout: int = 5) -> dict:
    """Check a single provider's health by sending a lightweight request."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",  # lightweight model for health check
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1
    }
    start = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=payload, timeout=timeout) as resp:
                latency = time.time() - start
                if resp.status == 200:
                    return {"healthy": True, "latency": latency, "status": resp.status}
                else:
                    return {"healthy": False, "latency": latency, "status": resp.status, "error": f"HTTP {resp.status}"}
    except asyncio.TimeoutError:
        return {"healthy": False, "latency": timeout, "status": 0, "error": "timeout"}
    except Exception as e:
        return {"healthy": False, "latency": time.time() - start, "status": 0, "error": str(e)}

async def run_provider_health_checks(providers_config: List[dict]) -> Dict[str, dict]:
    """Run health checks for all configured providers concurrently."""
    tasks = []
    for provider in providers_config:
        name = provider.get("name")
        endpoint = provider.get("endpoint")
        api_key = provider.get("api_key")
        if name and endpoint and api_key:
            tasks.append(check_provider_health(name, endpoint, api_key))
        else:
            logger.warning(f"Incomplete provider config: {name}")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    health_map = {}
    for idx, result in enumerate(results):
        provider_name = providers_config[idx]["name"]
        if isinstance(result, Exception):
            health_map[provider_name] = {"healthy": False, "error": str(result)}
        else:
            health_map[provider_name] = result
    _provider_health.update(health_map)
    return health_map

def get_healthy_providers() -> List[str]:
    """Return list of provider names that are currently healthy."""
    return [name for name, status in _provider_health.items() if status.get("healthy")]

def get_provider_priority() -> List[str]:
    """Return providers sorted by health and latency (healthy first, then by latency ascending)."""
    healthy = [(name, status["latency"]) for name, status in _provider_health.items() if status.get("healthy")]
    unhealthy = [name for name, status in _provider_health.items() if not status.get("healthy")]
    healthy.sort(key=lambda x: x[1])  # sort by latency
    return [name for name, _ in healthy] + unhealthy
